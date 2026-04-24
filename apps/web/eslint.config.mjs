import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import designSystem from './.eslint-plugin-design-system/index.mjs'

export default defineConfig([
  globalIgnores(['coverage', 'dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'design-system': designSystem,
    },
    rules: {
      'design-system/no-raw-color': 'error',
      'design-system/no-arbitrary-tw': 'error',
      'design-system/primitive-required': 'error',
      'design-system/no-inline-animation': 'error',
    },
  },
])
