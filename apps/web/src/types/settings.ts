export type ProviderEntityType = '1' | '2'
export type UsageIndicator = 'T' | 'P'
export type AcknowledgmentRequested = '0' | '1'

export interface SubmitterConfig {
  organizationName: string
  providerNpi: string
  providerEntityType: ProviderEntityType
  tradingPartnerId: string
  providerTaxonomyCode: string
  contactName: string
  contactPhone: string
  contactEmail: string
  payerProfile: string
  payerName: string
  payerId: string
  interchangeReceiverId: string
  receiverIdQualifier: string
  senderIdQualifier: string
  usageIndicator: UsageIndicator
  acknowledgmentRequested: AcknowledgmentRequested
  defaultServiceTypeCode: string
  defaultServiceDate: string
  maxBatchSize: number
  lastIsaControlNumber: number | null
}
