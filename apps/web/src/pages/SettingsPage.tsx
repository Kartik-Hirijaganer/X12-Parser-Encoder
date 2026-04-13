import { useEffect, useState } from 'react'

import type { ChangeEvent } from 'react'

import type { SubmitterConfig } from '../types/settings'
import { useApi } from '../hooks/useApi'
import { useSettings } from '../hooks/useSettings'
import { fetchProfileDefaults, fetchProfiles } from '../services/api'
import { SERVICE_TYPE_OPTIONS } from '../utils/constants'
import { readTextFromFile } from '../utils/fileDetection'
import { isValidNpi } from '../utils/npiValidator'
import { downloadTextFile } from '../utils/downloads'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FileUpload } from '../components/ui/FileUpload'

type SettingsBanner = {
  message: string
  variant: 'error' | 'success' | 'warning'
}

export function SettingsPage() {
  const { importSettings, replaceSettings, settings } = useSettings()
  const [draft, setDraft] = useState(settings)
  const [banner, setBanner] = useState<SettingsBanner | null>(null)
  const profilesRequest = useApi(fetchProfiles, [])

  useEffect(() => {
    setDraft(settings)
  }, [settings])

  async function applyProfileDefaults(profileName: string) {
    try {
      const defaults = await fetchProfileDefaults(profileName)
      setDraft((current) => ({
        ...current,
        payerProfile: profileName,
        payerName: defaults.payer_name,
        payerId: defaults.payer_id,
        interchangeReceiverId: defaults.interchange_receiver_id,
        receiverIdQualifier: defaults.receiver_id_qualifier,
        defaultServiceTypeCode: defaults.default_service_type_code,
        maxBatchSize: defaults.max_batch_size,
      }))
    } catch (caughtError) {
      setBanner({
        message:
          caughtError instanceof Error
            ? caughtError.message
            : 'Payer profile defaults could not be loaded.',
        variant: 'error',
      })
    }
  }

  function updateField<K extends keyof SubmitterConfig>(field: K, value: SubmitterConfig[K]) {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function saveSettings() {
    if (!draft.organizationName || !draft.providerNpi || !draft.tradingPartnerId) {
      setBanner({
        message: 'Organization name, provider NPI, and trading partner ID are required before saving.',
        variant: 'warning',
      })
      return
    }

    if (!isValidNpi(draft.providerNpi)) {
      setBanner({
        message: 'Provider NPI must be a valid 10-digit NPI before saving.',
        variant: 'error',
      })
      return
    }

    replaceSettings(draft)
    setBanner({
      message: 'Settings saved to local storage.',
      variant: 'success',
    })
  }

  async function importJson(file: File) {
    try {
      const text = await readTextFromFile(file)
      const parsed = importSettings(text)
      setDraft(parsed)
      setBanner({
        message: 'Settings imported successfully.',
        variant: 'success',
      })
    } catch (caughtError) {
      setBanner({
        message: caughtError instanceof Error ? caughtError.message : 'The JSON file could not be imported.',
        variant: 'error',
      })
    }
  }

  const npiValid = draft.providerNpi.length === 0 ? null : isValidNpi(draft.providerNpi)
  const profiles = profilesRequest.data?.profiles ?? [{ name: 'dc_medicaid', display_name: 'DC Medicaid', description: 'DC Medicaid eligibility profile.' }]

  return (
    <AppShell
      subtitle="Provider, payer, and envelope defaults live here. These settings are persisted locally and used automatically in the Generate 270 workflow."
      title="Settings"
    >
      {banner ? (
        <Banner onDismiss={() => setBanner(null)} variant={banner.variant}>
          {banner.message}
        </Banner>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <FileUpload
          accept=".json,application/json"
          buttonLabel="Import JSON"
          onFileSelect={(file) => void importJson(file)}
          variant="button"
        />
        <Button
          onClick={() => downloadTextFile(JSON.stringify(draft, null, 2), 'x12-settings.json', 'application/json')}
          variant="secondary"
        >
          Export JSON
        </Button>
        <Button onClick={saveSettings} variant="primary">
          Save Changes
        </Button>
      </div>

      <div className="mx-auto grid max-w-[640px] gap-6">
        <SettingsGroup description="These values identify the provider in the 270 transaction." title="Submitter / Provider Identity">
          <TextField
            label="Organization Name*"
            name="organizationName"
            onChange={handleTextChange(updateField)}
            value={draft.organizationName}
          />
          <TextField
            helperText={
              npiValid === null
                ? 'Enter the 10-digit provider NPI.'
                : npiValid
                  ? 'Valid NPI.'
                  : 'Invalid NPI (Luhn check failed).'
            }
            label="Provider NPI*"
            name="providerNpi"
            onChange={(event) =>
              updateField('providerNpi', event.currentTarget.value.replace(/\D/g, '').slice(0, 10))
            }
            value={draft.providerNpi}
          />
          <SelectField
            label="Provider Entity Type*"
            name="providerEntityType"
            onChange={(event) => updateField('providerEntityType', event.currentTarget.value as '1' | '2')}
            options={[
              { label: 'Individual (1)', value: '1' },
              { label: 'Organization (2)', value: '2' },
            ]}
            value={draft.providerEntityType}
          />
          <TextField
            label="Trading Partner ID*"
            name="tradingPartnerId"
            onChange={handleTextChange(updateField)}
            value={draft.tradingPartnerId}
          />
          <TextField
            label="Taxonomy Code"
            name="providerTaxonomyCode"
            onChange={handleTextChange(updateField)}
            value={draft.providerTaxonomyCode}
          />
          <TextField label="Contact Name" name="contactName" onChange={handleTextChange(updateField)} value={draft.contactName} />
          <TextField
            label="Contact Phone"
            name="contactPhone"
            onChange={handleTextChange(updateField)}
            value={draft.contactPhone}
          />
          <TextField
            label="Contact Email"
            name="contactEmail"
            onChange={handleTextChange(updateField)}
            value={draft.contactEmail}
          />
        </SettingsGroup>

        <SettingsGroup description="Selecting a payer profile auto-fills the receiver defaults below." title="Payer / Receiver">
          <SelectField
            label="Payer Profile*"
            name="payerProfile"
            onChange={(event) => void applyProfileDefaults(event.currentTarget.value)}
            options={profiles.map((profile) => ({
              label: profile.display_name,
              value: profile.name,
            }))}
            value={draft.payerProfile}
          />
          <TextField label="Payer Name*" name="payerName" onChange={handleTextChange(updateField)} value={draft.payerName} />
          <TextField label="Payer ID*" name="payerId" onChange={handleTextChange(updateField)} value={draft.payerId} />
          <TextField
            label="Receiver ID (ISA08)*"
            name="interchangeReceiverId"
            onChange={handleTextChange(updateField)}
            value={draft.interchangeReceiverId}
          />
          <SelectField
            label="Receiver Qualifier*"
            name="receiverIdQualifier"
            onChange={(event) => updateField('receiverIdQualifier', event.currentTarget.value)}
            options={[
              { label: 'ZZ', value: 'ZZ' },
              { label: '30', value: '30' },
            ]}
            value={draft.receiverIdQualifier}
          />
        </SettingsGroup>

        <SettingsGroup description="Envelope values apply to every generated interchange." title="Envelope Defaults">
          <SelectField
            label="Sender ID Qualifier*"
            name="senderIdQualifier"
            onChange={(event) => updateField('senderIdQualifier', event.currentTarget.value)}
            options={[
              { label: 'ZZ', value: 'ZZ' },
              { label: '30', value: '30' },
            ]}
            value={draft.senderIdQualifier}
          />
          <SelectField
            label="Usage Indicator*"
            name="usageIndicator"
            onChange={(event) => updateField('usageIndicator', event.currentTarget.value as 'T' | 'P')}
            options={[
              { label: 'Test (T)', value: 'T' },
              { label: 'Production (P)', value: 'P' },
            ]}
            value={draft.usageIndicator}
          />
          <SelectField
            label="Ack Requested*"
            name="acknowledgmentRequested"
            onChange={(event) =>
              updateField('acknowledgmentRequested', event.currentTarget.value as '0' | '1')
            }
            options={[
              { label: 'No (0)', value: '0' },
              { label: 'Yes (1)', value: '1' },
            ]}
            value={draft.acknowledgmentRequested}
          />
          <ReadOnlyField label="X12 Version" value="005010X279A1" />
        </SettingsGroup>

        <SettingsGroup description="These defaults are applied automatically during row normalization and generation." title="Transaction Defaults">
          <SelectField
            label="Service Type Code*"
            name="defaultServiceTypeCode"
            onChange={(event) => updateField('defaultServiceTypeCode', event.currentTarget.value)}
            options={SERVICE_TYPE_OPTIONS.map((option) => ({
              label: option.label,
              value: option.value,
            }))}
            value={draft.defaultServiceTypeCode}
          />
          <TextField
            label="Default Service Date*"
            name="defaultServiceDate"
            onChange={handleTextChange(updateField)}
            value={draft.defaultServiceDate}
          />
          <TextField
            label="Max Batch Size*"
            name="maxBatchSize"
            onChange={(event) =>
              updateField('maxBatchSize', Number(event.currentTarget.value.replace(/\D/g, '') || '0'))
            }
            value={String(draft.maxBatchSize)}
          />
        </SettingsGroup>
      </div>
    </AppShell>
  )
}

function SettingsGroup({
  children,
  description,
  title,
}: {
  children: React.ReactNode
  description: string
  title: string
}) {
  return (
    <Card className="space-y-5">
      <div className="space-y-2 border-b border-[var(--color-border-subtle)] pb-4">
        <h2 className="text-[20px] font-semibold text-[var(--color-text-primary)]">{title}</h2>
        <p className="text-[14px] text-[var(--color-text-secondary)]">{description}</p>
      </div>
      <div className="grid gap-4">{children}</div>
    </Card>
  )
}

function TextField({
  helperText,
  label,
  name,
  onChange,
  value,
}: {
  helperText?: string
  label: string
  name: string
  onChange: (event: ChangeEvent<HTMLInputElement>) => void
  value: string
}) {
  return (
    <label className="grid gap-2 text-[14px] font-medium text-[var(--color-text-primary)]">
      {label}
      <input
        className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 text-[16px] font-normal text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[3px] focus:ring-[var(--color-focus-ring)]"
        name={name}
        onChange={onChange}
        value={value}
      />
      {helperText ? <span className="text-[13px] font-normal text-[var(--color-text-secondary)]">{helperText}</span> : null}
    </label>
  )
}

function SelectField({
  label,
  name,
  onChange,
  options,
  value,
}: {
  label: string
  name: string
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void
  options: Array<{ label: string; value: string }>
  value: string
}) {
  return (
    <label className="grid gap-2 text-[14px] font-medium text-[var(--color-text-primary)]">
      {label}
      <select
        className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 text-[16px] font-normal text-[var(--color-text-primary)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[3px] focus:ring-[var(--color-focus-ring)]"
        name={name}
        onChange={onChange}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <label className="grid gap-2 text-[14px] font-medium text-[var(--color-text-primary)]">
      {label}
      <div className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-tertiary)] px-3 py-2 text-[16px] font-normal text-[var(--color-text-secondary)]">
        {value}
      </div>
    </label>
  )
}

function handleTextChange(
  updateField: <K extends keyof SubmitterConfig>(field: K, value: SubmitterConfig[K]) => void,
) {
  return (event: ChangeEvent<HTMLInputElement>) => {
    updateField(event.currentTarget.name as keyof SubmitterConfig, event.currentTarget.value)
  }
}
