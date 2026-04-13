import type { FileKind, WorkflowKind, X12PreviewSummary, X12TransactionType } from '../types/workflow'

const CANONICAL_HEADERS = new Set([
  'last_name',
  'first_name',
  'date_of_birth',
  'gender',
  'member_id',
  'ssn',
  'service_type_code',
  'service_date',
  'service_date_end',
])

export function detectFileKind(filename: string): FileKind {
  const normalized = filename.toLowerCase()
  if (normalized.endsWith('.xlsx')) {
    return 'excel'
  }
  if (
    normalized.endsWith('.csv') ||
    normalized.endsWith('.tsv') ||
    normalized.endsWith('.txt')
  ) {
    return 'csv'
  }
  if (normalized.endsWith('.x12') || normalized.endsWith('.edi')) {
    return 'x12'
  }
  return 'unknown'
}

export function detectWorkflowFromContent(filename: string, text: string): WorkflowKind | 'unknown' {
  if (looksLikeTemplateHeaders(text)) {
    return 'generate'
  }

  if (text.trimStart().startsWith('ISA')) {
    const transactionType = detectX12TransactionType(text)
    if (transactionType === '270') {
      return 'validate'
    }
    if (transactionType === '271') {
      return 'parse'
    }
    return 'validate'
  }

  const fileKind = detectFileKind(filename)
  if (fileKind === 'excel' || fileKind === 'csv') {
    return 'generate'
  }
  if (fileKind === 'x12') {
    return 'validate'
  }

  return 'unknown'
}

export function looksLikeTemplateHeaders(text: string): boolean {
  const firstLine = text.split(/\r?\n/, 1)[0]?.trim().toLowerCase()
  if (!firstLine) {
    return false
  }

  const delimiter = firstLine.includes('\t') ? '\t' : ','
  const headers = firstLine.split(delimiter).map((header) => header.trim())
  return headers.some((header) => CANONICAL_HEADERS.has(header))
}

export function detectX12TransactionType(text: string): X12TransactionType {
  const delimiters = detectX12Delimiters(text)
  if (!delimiters) {
    return 'unknown'
  }

  const stSegment = splitSegments(text, delimiters.segment).find((segment) =>
    segment.startsWith(`ST${delimiters.element}`),
  )
  if (!stSegment) {
    return 'unknown'
  }

  const elements = stSegment.split(delimiters.element)
  if (elements[1] === '270' || elements[1] === '271') {
    return elements[1]
  }
  return 'unknown'
}

export function buildX12PreviewSummary(text: string): X12PreviewSummary {
  const delimiters = detectX12Delimiters(text)
  if (!delimiters) {
    return {
      segmentCount: 0,
      transactionType: 'unknown',
      senderId: 'Unknown',
      receiverId: 'Unknown',
      controlNumber: 'Unknown',
      subscriberNames: [],
    }
  }

  const segments = splitSegments(text, delimiters.segment)
  const isaElements = text.slice(0, 105).split(delimiters.element)
  const subscriberNames = segments
    .filter((segment) => segment.startsWith(`NM1${delimiters.element}IL${delimiters.element}`))
    .slice(0, 3)
    .map((segment) => {
      const elements = segment.split(delimiters.element)
      return [elements[3], elements[4]].filter(Boolean).join(', ')
    })
    .filter(Boolean)

  return {
    segmentCount: segments.length,
    transactionType: detectX12TransactionType(text),
    senderId: isaElements[6]?.trim() || 'Unknown',
    receiverId: isaElements[8]?.trim() || 'Unknown',
    controlNumber: isaElements[13]?.trim() || 'Unknown',
    subscriberNames,
  }
}

export async function detectWorkflowFromFile(
  file: File,
): Promise<{ workflow: WorkflowKind | 'unknown'; rawText: string | null }> {
  const fileKind = detectFileKind(file.name)
  if (fileKind === 'excel') {
    return { workflow: 'generate', rawText: null }
  }

  const rawText = await readTextFromFile(file)
  return {
    workflow: detectWorkflowFromContent(file.name, rawText),
    rawText,
  }
}

export async function readTextFromFile(file: File): Promise<string> {
  if (typeof file.text === 'function') {
    return file.text()
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error ?? new Error('File could not be read.'))
    reader.readAsText(file)
  })
}

function detectX12Delimiters(text: string):
  | { element: string; segment: string }
  | null {
  if (!text.startsWith('ISA') || text.length < 106) {
    return null
  }

  return {
    element: text[3],
    segment: text[105],
  }
}

function splitSegments(text: string, segmentTerminator: string): string[] {
  return text
    .split(segmentTerminator)
    .map((segment) => segment.trim())
    .filter(Boolean)
}
