import type {
  ConvertResponse,
  GenerateResponse,
  ParseResponse,
  ValidateResponse,
} from './api'

export type WorkflowKind = 'generate' | 'validate' | 'parse'
export type FileKind = 'excel' | 'csv' | 'x12' | 'unknown'
export type X12TransactionType = '270' | '271' | 'unknown'

export interface X12PreviewSummary {
  segmentCount: number
  transactionType: X12TransactionType
  senderId: string
  receiverId: string
  controlNumber: string
  subscriberNames: string[]
}

export interface GeneratePreviewState {
  flow: 'generate'
  filename: string
  fileSize?: number
  response: ConvertResponse
}

export interface X12PreviewState {
  flow: 'validate' | 'parse'
  filename: string
  fileSize?: number
  rawText: string
  preview: X12PreviewSummary
}

export type PreviewRouteState = GeneratePreviewState | X12PreviewState

export interface GenerateResultRouteState {
  filename: string
  response: GenerateResponse
}

export interface ValidationResultRouteState {
  filename: string
  response: ValidateResponse
}

export interface DashboardRouteState {
  filename: string
  response: ParseResponse
}
