import type { SubmitterConfig } from '../types/settings'

export const SETTINGS_STORAGE_KEY = 'x12.submitter-config'

export const DEFAULT_SUBMITTER_CONFIG: SubmitterConfig = {
  organizationName: '',
  providerNpi: '',
  providerEntityType: '2',
  tradingPartnerId: '',
  providerTaxonomyCode: '',
  contactName: '',
  contactPhone: '',
  contactEmail: '',
  payerName: 'DC MEDICAID',
  payerId: 'DCMEDICAID',
  interchangeReceiverId: 'DCMEDICAID',
  receiverIdQualifier: 'ZZ',
  senderIdQualifier: 'ZZ',
  usageIndicator: 'T',
  acknowledgmentRequested: '0',
  defaultServiceTypeCode: '30',
  defaultServiceDate: '',
  maxBatchSize: 5000,
}
