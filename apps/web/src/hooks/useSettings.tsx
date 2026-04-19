/* eslint-disable react-refresh/only-export-components */

import type { ReactNode } from 'react'

import { createContext, useContext, useEffect, useMemo, useState } from 'react'

import type { SubmitterConfig } from '../types/settings'
import {
  DEFAULT_PROFILE_NAME,
  DEFAULT_SUBMITTER_CONFIG,
  MAX_ISA_CONTROL_NUMBER,
  MIN_ISA_CONTROL_NUMBER,
  REQUIRED_SETTINGS_FIELDS,
  SETTINGS_STORAGE_KEY,
} from '../utils/constants'

interface SettingsContextValue {
  settings: SubmitterConfig
  hasRequiredSettings: boolean
  replaceSettings: (nextSettings: SubmitterConfig) => void
  importSettings: (rawValue: string) => SubmitterConfig
  updateLastIcn: (isa13: string) => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SubmitterConfig>(() => readStoredSettings())

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  }, [settings])

  const value = useMemo<SettingsContextValue>(
    () => ({
      settings,
      hasRequiredSettings: REQUIRED_SETTINGS_FIELDS.every((field) => {
        const fieldValue = settings[field]
        if (typeof fieldValue === 'number') {
          return fieldValue > 0
        }
        return fieldValue.trim().length > 0
      }),
      replaceSettings: (nextSettings) => setSettings(sanitizeSettings(nextSettings)),
      importSettings: (rawValue) => {
        const parsed = JSON.parse(rawValue) as Record<string, unknown>
        const nextSettings = sanitizeSettings(parsed)
        setSettings(nextSettings)
        return nextSettings
      },
      updateLastIcn: (isa13: string) => {
        const parsed = parseInt(isa13, 10)
        if (
          !Number.isInteger(parsed) ||
          parsed < MIN_ISA_CONTROL_NUMBER ||
          parsed > MAX_ISA_CONTROL_NUMBER
        ) {
          return
        }
        setSettings((prev) => ({ ...prev, lastIsaControlNumber: parsed }))
      },
    }),
    [settings],
  )

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export function useSettings(): SettingsContextValue {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider.')
  }
  return context
}

function readStoredSettings(): SubmitterConfig {
  if (typeof window === 'undefined') {
    return DEFAULT_SUBMITTER_CONFIG
  }

  const rawValue = window.localStorage.getItem(SETTINGS_STORAGE_KEY)
  if (!rawValue) {
    return DEFAULT_SUBMITTER_CONFIG
  }

  try {
    const parsed = JSON.parse(rawValue) as Record<string, unknown>
    return sanitizeSettings(parsed)
  } catch {
    return DEFAULT_SUBMITTER_CONFIG
  }
}

function sanitizeSettings(rawValue: Record<string, unknown> | SubmitterConfig): SubmitterConfig {
  const value = 'organization_name' in rawValue ? normalizeSnakeCase(rawValue) : rawValue
  const merged = {
    ...DEFAULT_SUBMITTER_CONFIG,
    ...value,
  }

  return {
    organizationName: String(merged.organizationName ?? ''),
    providerNpi: String(merged.providerNpi ?? '').replace(/\D/g, '').slice(0, 10),
    providerEntityType: merged.providerEntityType === '1' ? '1' : '2',
    tradingPartnerId: String(merged.tradingPartnerId ?? ''),
    providerTaxonomyCode: String(merged.providerTaxonomyCode ?? ''),
    contactName: String(merged.contactName ?? ''),
    contactPhone: String(merged.contactPhone ?? ''),
    contactEmail: String(merged.contactEmail ?? ''),
    payerProfile: String(merged.payerProfile ?? DEFAULT_PROFILE_NAME),
    payerName: String(merged.payerName ?? ''),
    payerId: String(merged.payerId ?? ''),
    interchangeReceiverId: String(merged.interchangeReceiverId ?? ''),
    receiverIdQualifier: String(merged.receiverIdQualifier ?? 'ZZ'),
    senderIdQualifier: String(merged.senderIdQualifier ?? 'ZZ'),
    usageIndicator: merged.usageIndicator === 'P' ? 'P' : 'T',
    acknowledgmentRequested: merged.acknowledgmentRequested === '1' ? '1' : '0',
    defaultServiceTypeCode: String(merged.defaultServiceTypeCode ?? '30'),
    defaultServiceDate: String(merged.defaultServiceDate ?? ''),
    maxBatchSize: Number.isFinite(Number(merged.maxBatchSize))
      ? Math.max(1, Number(merged.maxBatchSize))
      : 5000,
    lastIsaControlNumber:
      Number.isInteger(merged.lastIsaControlNumber) &&
      (merged.lastIsaControlNumber as number) >= MIN_ISA_CONTROL_NUMBER &&
      (merged.lastIsaControlNumber as number) <= MAX_ISA_CONTROL_NUMBER
        ? (merged.lastIsaControlNumber as number)
        : null,
  }
}

function normalizeSnakeCase(rawValue: Record<string, unknown>): Record<string, unknown> {
  return {
    organizationName: rawValue.organization_name,
    providerNpi: rawValue.provider_npi,
    providerEntityType: rawValue.provider_entity_type,
    tradingPartnerId: rawValue.trading_partner_id,
    providerTaxonomyCode: rawValue.provider_taxonomy_code,
    contactName: rawValue.contact_name,
    contactPhone: rawValue.contact_phone,
    contactEmail: rawValue.contact_email,
    payerProfile: rawValue.payer_profile,
    payerName: rawValue.payer_name,
    payerId: rawValue.payer_id,
    interchangeReceiverId: rawValue.interchange_receiver_id,
    receiverIdQualifier: rawValue.receiver_id_qualifier,
    senderIdQualifier: rawValue.sender_id_qualifier,
    usageIndicator: rawValue.usage_indicator,
    acknowledgmentRequested: rawValue.acknowledgment_requested,
    defaultServiceTypeCode: rawValue.default_service_type_code,
    defaultServiceDate: rawValue.default_service_date,
    maxBatchSize: rawValue.max_batch_size,
  }
}
