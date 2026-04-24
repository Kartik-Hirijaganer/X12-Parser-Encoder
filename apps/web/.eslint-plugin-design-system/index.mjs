const HEX_COLOR_PATTERN = /#[0-9a-fA-F]{3,8}\b/
const ARBITRARY_CLASS_PATTERN = /(?:^|:)([!-]?[a-z0-9/.-]+)-\[([^\]]+)\]/
const RAW_DIMENSION_PATTERN = /-?\d*\.?\d+(px|ms)\b/

const SAFE_COLOR_FIXES = new Map([
  ['#ffffff', 'var(--color-surface-primary)'],
  ['#fff', 'var(--color-surface-primary)'],
  ['#000000', 'var(--color-text-primary)'],
  ['#000', 'var(--color-text-primary)'],
])

const messageUrl = 'docs/design-spec.md'

function getFilename(context) {
  return context.filename ?? context.getFilename?.() ?? ''
}

function isTokensFile(context) {
  return getFilename(context).endsWith('tokens.css')
}

function isClassNameAttribute(node) {
  return node.type === 'JSXAttribute' && node.name?.name === 'className'
}

function isStyleAttribute(node) {
  return node.type === 'JSXAttribute' && node.name?.name === 'style'
}

function literalText(node) {
  if (!node) {
    return null
  }

  if (node.type === 'Literal' && typeof node.value === 'string') {
    return node.value
  }

  if (node.type === 'TemplateElement') {
    return node.value.raw
  }

  return null
}

function staticClassNodes(attribute) {
  const value = attribute.value

  if (!value) {
    return []
  }

  if (value.type === 'Literal' && typeof value.value === 'string') {
    return [{ node: value, text: value.value, fixable: true }]
  }

  if (value.type !== 'JSXExpressionContainer') {
    return []
  }

  const expression = value.expression

  if (expression.type === 'Literal' && typeof expression.value === 'string') {
    return [{ node: expression, text: expression.value, fixable: true }]
  }

  if (expression.type === 'TemplateLiteral') {
    return expression.quasis.map((quasi) => ({
      node: quasi,
      text: quasi.value.raw,
      fixable: false,
    }))
  }

  return []
}

function reportHex(context, node, text, fixable) {
  const match = HEX_COLOR_PATTERN.exec(text)

  if (!match) {
    return
  }

  const hex = match[0]
  const replacement = SAFE_COLOR_FIXES.get(hex.toLowerCase())

  context.report({
    node,
    message: `Use a design token from ${messageUrl} instead of raw color ${hex}.`,
    fix:
      fixable && replacement
        ? (fixer) => fixer.replaceText(node, context.sourceCode.getText(node).replace(hex, replacement))
        : null,
  })
}

function getStyleObject(attribute) {
  const value = attribute.value

  if (value?.type !== 'JSXExpressionContainer') {
    return null
  }

  return value.expression.type === 'ObjectExpression' ? value.expression : null
}

function propertyName(property) {
  if (property.key?.type === 'Identifier') {
    return property.key.name
  }

  if (property.key?.type === 'Literal') {
    return String(property.key.value)
  }

  return ''
}

function stylePropertyTextNodes(styleObject) {
  const nodes = []

  for (const property of styleObject.properties) {
    if (property.type !== 'Property') {
      continue
    }

    const text = literalText(property.value)
    if (text !== null) {
      nodes.push({ node: property.value, property: propertyName(property), text })
    }

    if (property.value.type === 'TemplateLiteral') {
      for (const quasi of property.value.quasis) {
        nodes.push({ node: quasi, property: propertyName(property), text: quasi.value.raw })
      }
    }
  }

  return nodes
}

function splitClassNames(text) {
  return text.split(/\s+/).filter(Boolean)
}

function parseArbitraryClass(className) {
  const match = ARBITRARY_CLASS_PATTERN.exec(className)

  if (!match) {
    return null
  }

  return {
    className,
    prefix: match[1],
    value: match[2],
  }
}

function isTokenReference(value) {
  return value.includes('var(--')
}

function shouldRejectArbitrary(classInfo) {
  if (!classInfo || isTokenReference(classInfo.value)) {
    return false
  }

  return HEX_COLOR_PATTERN.test(classInfo.value) || RAW_DIMENSION_PATTERN.test(classInfo.value)
}

function pathIsFeatureOrPage(filename) {
  const normalized = filename.replaceAll('\\', '/')
  return (
    normalized.includes('/src/components/features/') ||
    normalized.includes('/src/pages/')
  )
}

function isRawFileInput(node) {
  if (node.name?.name !== 'input') {
    return false
  }

  return node.attributes.some((attribute) => {
    if (attribute.type !== 'JSXAttribute' || attribute.name?.name !== 'type') {
      return false
    }

    if (attribute.value?.type === 'Literal') {
      return attribute.value.value === 'file'
    }

    if (attribute.value?.type === 'JSXExpressionContainer') {
      const expression = attribute.value.expression
      return expression.type === 'Literal' && expression.value === 'file'
    }

    return false
  })
}

const noRawColor = {
  meta: {
    type: 'problem',
    docs: {
      description: 'disallow raw hex colors in JSX class names and style objects',
    },
    fixable: 'code',
    schema: [],
  },
  create(context) {
    if (isTokensFile(context)) {
      return {}
    }

    return {
      JSXAttribute(node) {
        if (isClassNameAttribute(node)) {
          for (const classNode of staticClassNodes(node)) {
            reportHex(context, classNode.node, classNode.text, classNode.fixable)
          }
          return
        }

        if (!isStyleAttribute(node)) {
          return
        }

        const styleObject = getStyleObject(node)
        if (!styleObject) {
          return
        }

        for (const styleNode of stylePropertyTextNodes(styleObject)) {
          reportHex(context, styleNode.node, styleNode.text, false)
        }
      },
    }
  },
}

const noArbitraryTw = {
  meta: {
    type: 'problem',
    docs: {
      description: 'disallow non-token Tailwind arbitrary values for design-system values',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (!isClassNameAttribute(node)) {
          return
        }

        for (const classNode of staticClassNodes(node)) {
          for (const className of splitClassNames(classNode.text)) {
            const classInfo = parseArbitraryClass(className)

            if (!shouldRejectArbitrary(classInfo)) {
              continue
            }

            context.report({
              node: classNode.node,
              message: `Use a token-backed arbitrary value from ${messageUrl} instead of "${classInfo.className}".`,
            })
          }
        }
      },
    }
  },
}

const primitiveRequired = {
  meta: {
    type: 'problem',
    docs: {
      description: 'require UI primitives for buttons, file inputs, and tables in pages and feature components',
    },
    schema: [],
  },
  create(context) {
    if (!pathIsFeatureOrPage(getFilename(context))) {
      return {}
    }

    return {
      JSXOpeningElement(node) {
        const tagName = node.name?.name

        if (tagName === 'button') {
          context.report({
            node,
            message: `Use the Button primitive. See ${messageUrl}.`,
          })
        }

        if (tagName === 'table') {
          context.report({
            node,
            message: `Use the Table primitive. See ${messageUrl}.`,
          })
        }

        if (isRawFileInput(node)) {
          context.report({
            node,
            message: `Use the FileUpload primitive. See ${messageUrl}.`,
          })
        }
      },
    }
  },
}

const noInlineAnimation = {
  meta: {
    type: 'problem',
    docs: {
      description: 'disallow inline transition and animation declarations',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (!isStyleAttribute(node)) {
          return
        }

        const styleObject = getStyleObject(node)
        if (!styleObject) {
          return
        }

        for (const property of styleObject.properties) {
          if (property.type !== 'Property') {
            continue
          }

          const name = propertyName(property)
          if (name === 'transition' || name === 'animation') {
            context.report({
              node: property.key,
              message: `Use motion tokens from ${messageUrl} instead of inline ${name}.`,
            })
          }
        }
      },
    }
  },
}

export default {
  rules: {
    'no-raw-color': noRawColor,
    'no-arbitrary-tw': noArbitraryTw,
    'primitive-required': primitiveRequired,
    'no-inline-animation': noInlineAnimation,
  },
}
