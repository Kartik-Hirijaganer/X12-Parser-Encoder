import type {
  ConvertResponse,
  ExportWorkbookRequest,
  GenerateResponse,
  ParseResponse,
  ProfileDefaultsResponse,
  ProfilesResponse,
  ValidateResponse,
} from '../types/api'
import type { SubmitterConfig } from '../types/settings'
import { API_BASE_URL, REQUEST_TIMEOUT_MS } from '../utils/constants'

export class ApiError extends Error {
  status: number
  suggestion: string | null

  constructor(message: string, status: number, suggestion: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.suggestion = suggestion
  }
}

export class ApiTimeoutError extends Error {
  constructor(message = 'Processing is taking longer than expected.') {
    super(message)
    this.name = 'ApiTimeoutError'
  }
}

export async function convertUpload(
  file: File,
  settings: SubmitterConfig,
): Promise<ConvertResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('config', JSON.stringify(toApiSubmitterConfig(settings)))
  return requestJson<ConvertResponse>('/convert', {
    method: 'POST',
    body: formData,
  })
}

export async function generate270(
  settings: SubmitterConfig,
  patients: ConvertResponse['patients'],
): Promise<GenerateResponse> {
  return requestJson<GenerateResponse>('/generate', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      config: toApiSubmitterConfig(settings),
      patients,
      profile: settings.payerProfile,
    }),
  })
}

export async function validate270(file: File, profile = 'dc_medicaid'): Promise<ValidateResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('profile', profile)
  return requestJson<ValidateResponse>('/validate', {
    method: 'POST',
    body: formData,
  })
}

export async function parse271(file: File): Promise<ParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return requestJson<ParseResponse>('/parse', {
    method: 'POST',
    body: formData,
  })
}

export async function exportEligibilityWorkbook(payload: ExportWorkbookRequest): Promise<Blob> {
  return requestBlob('/export/xlsx', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(payload),
  })
}

export async function fetchProfiles(): Promise<ProfilesResponse> {
  return requestJson<ProfilesResponse>('/profiles')
}

export async function fetchProfileDefaults(name: string): Promise<ProfileDefaultsResponse> {
  return requestJson<ProfileDefaultsResponse>(`/profiles/${name}/defaults`)
}

export function templateUrl(name: string): string {
  return `${API_BASE_URL}/templates/${name}`
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init)
  return (await response.json()) as T
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await request(path, init)
  return response.blob()
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
    })

    if (!response.ok) {
      throw await buildApiError(response)
    }

    return response
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiTimeoutError()
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

async function buildApiError(response: Response): Promise<ApiError> {
  let message = 'The request could not be completed.'
  let suggestion: string | null = null

  try {
    const payload = (await response.json()) as {
      detail?: string | { message?: string; suggestion?: string } | Array<{ msg?: string }>
    }
    if (typeof payload.detail === 'string') {
      message = payload.detail
    } else if (Array.isArray(payload.detail)) {
      message = payload.detail[0]?.msg ?? message
    } else if (payload.detail?.message) {
      message = payload.detail.message
      suggestion = payload.detail.suggestion ?? null
    }
  } catch {
    message = response.statusText || message
  }

  return new ApiError(message, response.status, suggestion)
}

function toApiSubmitterConfig(settings: SubmitterConfig): Record<string, string | number> {
  return {
    organizationName: settings.organizationName,
    providerNpi: settings.providerNpi,
    providerEntityType: settings.providerEntityType,
    tradingPartnerId: settings.tradingPartnerId,
    providerTaxonomyCode: settings.providerTaxonomyCode,
    contactName: settings.contactName,
    contactPhone: settings.contactPhone,
    contactEmail: settings.contactEmail,
    payerName: settings.payerName,
    payerId: settings.payerId,
    interchangeReceiverId: settings.interchangeReceiverId,
    receiverIdQualifier: settings.receiverIdQualifier,
    senderIdQualifier: settings.senderIdQualifier,
    usageIndicator: settings.usageIndicator,
    acknowledgmentRequested: settings.acknowledgmentRequested,
    defaultServiceTypeCode: settings.defaultServiceTypeCode,
    defaultServiceDate: settings.defaultServiceDate,
    maxBatchSize: settings.maxBatchSize,
  }
}

function jsonHeaders(): HeadersInit {
  return { 'Content-Type': 'application/json' }
}
