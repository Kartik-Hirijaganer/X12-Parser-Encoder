import { useEffect, useRef, useState } from 'react'

import type { ChangeEvent, ReactNode } from 'react'

import type { SubmitterConfig } from '../types/settings'
import { useApi } from '../hooks/useApi'
import { useSettings } from '../hooks/useSettings'
import { fetchProfileDefaults, fetchProfiles } from '../services/api'
import {
  formatIsaControlNumber,
  MAX_ISA_CONTROL_NUMBER,
  nextIsaControlNumber,
  SERVICE_TYPE_OPTIONS,
} from '../utils/constants'
import { cn } from '../utils/cn'
import { readTextFromFile } from '../utils/fileDetection'
import { isValidNpi } from '../utils/npiValidator'
import { downloadTextFile } from '../utils/downloads'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FileUpload } from '../components/ui/FileUpload'
import { CheckIcon, CloseIcon } from '../components/ui/Icons'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { toast } from '../components/ui/Toast'
import { UnsavedChangesBar } from '../components/ui/UnsavedChangesBar'

type SettingsBanner = {
  message: string
  variant: 'error' | 'warning'
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function SettingsPage() {
  const { parseSettingsJson, replaceSettings, settings } = useSettings()
  const [draft, setDraft] = useState(settings)
  const [icnInput, setIcnInput] = useState(formatIcnInput(settings.lastIsaControlNumber))
  const [banner, setBanner] = useState<SettingsBanner | null>(null)
  const [saveAttempted, setSaveAttempted] = useState(false)
  const profilesRequest = useApi(fetchProfiles, [])
  const preserveDraftOnNextSettingsSyncRef = useRef(false)

  useEffect(() => {
    if (preserveDraftOnNextSettingsSyncRef.current) {
      preserveDraftOnNextSettingsSyncRef.current = false
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDraft((current) => ({
        ...current,
        lastIsaControlNumber: settings.lastIsaControlNumber,
      }))
    } else {
      setDraft(settings)
    }
    setIcnInput(formatIcnInput(settings.lastIsaControlNumber))
  }, [settings])

  async function applyProfileDefaults(profileName: string) {
    try {
      const defaults = await fetchProfileDefaults(profileName)
      setDraft((current) => {
        const next = {
          ...current,
          payerProfile: profileName,
          payerName: defaults.payerName,
          payerId: defaults.payerId,
          interchangeReceiverId: defaults.interchangeReceiverId,
          receiverIdQualifier: defaults.receiverIdQualifier,
          defaultServiceTypeCode: defaults.defaultServiceTypeCode,
          maxBatchSize: defaults.maxBatchSize,
        }
        return next
      })
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

  function persist(candidate: SubmitterConfig) {
    const validationErrors = validateSettingsDraft(candidate)
    if (Object.keys(validationErrors).length > 0) {
      setSaveAttempted(true)
      setBanner({
        message: 'Fix the highlighted settings fields before saving.',
        variant: 'error',
      })
      return false
    }

    replaceSettings(candidate)
    setBanner(null)
    setSaveAttempted(false)
    toast.success('Settings saved')
    return true
  }

  async function importJson(file: File) {
    try {
      const text = await readTextFromFile(file)
      const parsed = parseSettingsJson(text)
      setDraft(parsed)
      setIcnInput(formatIcnInput(parsed.lastIsaControlNumber))
      toast.success('Settings imported to draft')
      setBanner(null)
    } catch (caughtError) {
      setBanner({
        message: caughtError instanceof Error ? caughtError.message : 'The JSON file could not be imported.',
        variant: 'error',
      })
    }
  }

  function handleIcnChange(event: ChangeEvent<HTMLInputElement>) {
    const digits = event.currentTarget.value.replace(/\D/g, '').slice(0, 9)
    setIcnInput(digits)
    updateField('lastIsaControlNumber', parseIcnDraftValue(digits))
  }

  function handleIcnBlur() {
    if (icnInput.length > 0) {
      setIcnInput(icnInput.padStart(9, '0'))
    }
  }

  function clearIcnDraft() {
    setIcnInput('')
    updateField('lastIsaControlNumber', null)
  }

  function saveIcn() {
    const lastIsaControlNumber = draft.lastIsaControlNumber
    preserveDraftOnNextSettingsSyncRef.current = true
    replaceSettings({
      ...settings,
      lastIsaControlNumber,
    })
    setDraft((current) => ({
      ...current,
      lastIsaControlNumber,
    }))
    setIcnInput(formatIcnInput(lastIsaControlNumber))
    setBanner(null)
    toast.success(lastIsaControlNumber === null ? 'ICN cleared' : 'ICN saved')
  }

  function discardChanges() {
    setDraft(settings)
    setIcnInput(formatIcnInput(settings.lastIsaControlNumber))
    setBanner(null)
    setSaveAttempted(false)
  }

  const validationErrors = validateSettingsDraft(draft)
  const visibleError = (field: keyof SubmitterConfig) =>
    shouldShowFieldError(field, draft, saveAttempted) ? validationErrors[field] : undefined
  const profiles = profilesRequest.data?.profiles ?? [{ name: 'dc_medicaid', displayName: 'DC Medicaid', description: 'DC Medicaid eligibility profile.' }]
  const hasUnsavedChanges = serializeSettings(draft) !== serializeSettings(settings)
  const nextDraftIcn = nextIsaControlNumber(draft.lastIsaControlNumber)
  const icnIsExhausted = draft.lastIsaControlNumber === MAX_ISA_CONTROL_NUMBER

  return (
    <AppShell
      subtitle="Provider, payer, envelope, and ICN defaults live here. Save changes explicitly before generating 270 files."
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
        <Button disabled={!hasUnsavedChanges} onClick={() => persist(draft)} variant="primary">
          Save Changes
        </Button>
      </div>

      <div className="mx-auto grid max-w-[var(--layout-settings-max)] gap-6 md:grid-cols-2">
        <SettingsGroup
          description="Set the last ISA13 that was submitted so the next generated 270 uses a unique control number."
          id="icn"
          title="Interchange Control Number"
        >
          {draft.lastIsaControlNumber === null ? (
            <Banner title="ICN is required before generation." variant="warning">
              Set the last submitted ICN before generating a 270 file for DC Medicaid.
            </Banner>
          ) : null}
          {icnIsExhausted ? (
            <Banner title="ICN range exhausted." variant="warning">
              ISA13 999999999 cannot wrap to 000000001. Contact Gainwell or confirm a new
              trading-partner control-number policy before generating more files.
            </Banner>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <ReadOnlyField
              label="Last submitted ICN"
              value={draft.lastIsaControlNumber === null ? '— not set —' : formatIsaControlNumber(draft.lastIsaControlNumber)}
            />
            <ReadOnlyField
              label="Next ICN to be used"
              value={nextDraftIcn === null ? '— not set —' : formatIsaControlNumber(nextDraftIcn)}
            />
          </div>
          <TextField
            helperText="Digits only. Empty or 000000000 clears the saved ICN."
            label="Set your last submitted ICN"
            name="lastIsaControlNumber"
            onBlur={handleIcnBlur}
            onChange={handleIcnChange}
            value={icnInput}
          />
          <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
            <p>Find the last ICN in:</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>Gainwell submission portal.</li>
              <li>Most recent generated/downloaded 270 filename.</li>
              <li>999 acknowledgments.</li>
              <li>Settings JSON exported from the browser that last generated files.</li>
            </ul>
            <p>
              This app is stateless. If multiple people generate files under the same trading
              partner ID, coordinate who generates next or export/import Settings JSON after each
              accepted batch.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={saveIcn} variant="primary">
              Save ICN
            </Button>
            <Button onClick={clearIcnDraft} variant="secondary">
              Clear
            </Button>
          </div>
        </SettingsGroup>

        <SettingsGroup description="These values identify the provider in the 270 transaction." title="Submitter / Provider Identity">
          <TextField
            errorText={visibleError('organizationName')}
            label="Organization Name"
            name="organizationName"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.organizationName, visibleError('organizationName'))}
            value={draft.organizationName}
          />
          <TextField
            errorText={visibleError('providerNpi')}
            helperText={
              visibleError('providerNpi') === undefined && draft.providerNpi.length > 0
                ? 'Valid NPI.'
                : 'Enter the 10-digit provider NPI.'
            }
            label="Provider NPI"
            name="providerNpi"
            onChange={(event) =>
              updateField('providerNpi', event.currentTarget.value.replace(/\D/g, '').slice(0, 10))
            }
            required
            valid={fieldValidity(draft.providerNpi, visibleError('providerNpi'))}
            value={draft.providerNpi}
          />
          <SelectField
            label="Provider Entity Type"
            name="providerEntityType"
            onChange={(event) => updateField('providerEntityType', event.currentTarget.value as '1' | '2')}
            options={[
              { label: 'Individual (1)', value: '1' },
              { label: 'Organization (2)', value: '2' },
            ]}
            required
            value={draft.providerEntityType}
          />
          <TextField
            errorText={visibleError('tradingPartnerId')}
            helperText="Trading partner ID assigned by Gainwell."
            label="Trading Partner ID"
            name="tradingPartnerId"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.tradingPartnerId, visibleError('tradingPartnerId'))}
            value={draft.tradingPartnerId}
          />
          <TextField
            label="Taxonomy Code"
            name="providerTaxonomyCode"
            onChange={handleTextChange(updateField)}
            value={draft.providerTaxonomyCode}
          />
          <TextField
            label="Contact Name"
            name="contactName"
            onChange={handleTextChange(updateField)}
            value={draft.contactName}
          />
          <TextField
            label="Contact Phone"
            name="contactPhone"
            onChange={handleTextChange(updateField)}
            value={draft.contactPhone}
          />
          <TextField
            errorText={visibleError('contactEmail')}
            helperText={
              visibleError('contactEmail') === undefined && draft.contactEmail.length > 0
                ? 'Looks like a valid email.'
                : 'Optional contact email.'
            }
            label="Contact Email"
            name="contactEmail"
            onChange={handleTextChange(updateField)}
            valid={fieldValidity(draft.contactEmail, visibleError('contactEmail'), { optional: true })}
            value={draft.contactEmail}
          />
        </SettingsGroup>

        <SettingsGroup description="Selecting a payer profile auto-fills the receiver defaults below." title="Payer / Receiver">
          <SelectField
            label="Payer Profile"
            name="payerProfile"
            onChange={(event) => void applyProfileDefaults(event.currentTarget.value)}
            options={profiles.map((profile) => ({
              label: profile.displayName,
              value: profile.name,
            }))}
            required
            value={draft.payerProfile}
          />
          <TextField
            errorText={visibleError('payerName')}
            label="Payer Name"
            name="payerName"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.payerName, visibleError('payerName'))}
            value={draft.payerName}
          />
          <TextField
            errorText={visibleError('payerId')}
            label="Payer ID"
            name="payerId"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.payerId, visibleError('payerId'))}
            value={draft.payerId}
          />
          <TextField
            errorText={visibleError('interchangeReceiverId')}
            label="Receiver ID (ISA08)"
            name="interchangeReceiverId"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.interchangeReceiverId, visibleError('interchangeReceiverId'))}
            value={draft.interchangeReceiverId}
          />
          <SelectField
            label="Receiver Qualifier"
            name="receiverIdQualifier"
            onChange={(event) => updateField('receiverIdQualifier', event.currentTarget.value)}
            options={[
              { label: 'ZZ', value: 'ZZ' },
              { label: '30', value: '30' },
            ]}
            required
            value={draft.receiverIdQualifier}
          />
        </SettingsGroup>

        <SettingsGroup description="Envelope values apply to every generated interchange." title="Envelope Defaults">
          <SelectField
            label="Sender ID Qualifier"
            name="senderIdQualifier"
            onChange={(event) => updateField('senderIdQualifier', event.currentTarget.value)}
            options={[
              { label: 'ZZ', value: 'ZZ' },
              { label: '30', value: '30' },
            ]}
            required
            value={draft.senderIdQualifier}
          />
          <SelectField
            label="Usage Indicator"
            name="usageIndicator"
            onChange={(event) => updateField('usageIndicator', event.currentTarget.value as 'T' | 'P')}
            options={[
              { label: 'Test (T)', value: 'T' },
              { label: 'Production (P)', value: 'P' },
            ]}
            required
            value={draft.usageIndicator}
          />
          <SelectField
            label="Ack Requested"
            name="acknowledgmentRequested"
            onChange={(event) =>
              updateField('acknowledgmentRequested', event.currentTarget.value as '0' | '1')
            }
            options={[
              { label: 'No (0)', value: '0' },
              { label: 'Yes (1)', value: '1' },
            ]}
            required
            value={draft.acknowledgmentRequested}
          />
          <ReadOnlyField label="X12 Version" value="005010X279A1" />
        </SettingsGroup>

        <SettingsGroup description="These defaults are applied automatically during row normalization and generation." title="Transaction Defaults">
          <SelectField
            label="Service Type Code"
            name="defaultServiceTypeCode"
            onChange={(event) => updateField('defaultServiceTypeCode', event.currentTarget.value)}
            options={SERVICE_TYPE_OPTIONS.map((option) => ({
              label: option.label,
              value: option.value,
            }))}
            required
            value={draft.defaultServiceTypeCode}
          />
          <TextField
            errorText={visibleError('defaultServiceDate')}
            helperText="Used when a spreadsheet row leaves service_date blank."
            label="Default Service Date"
            name="defaultServiceDate"
            onChange={handleTextChange(updateField)}
            required
            valid={fieldValidity(draft.defaultServiceDate, visibleError('defaultServiceDate'))}
            value={draft.defaultServiceDate}
          />
          <TextField
            errorText={visibleError('maxBatchSize')}
            label="Max Batch Size"
            name="maxBatchSize"
            onChange={(event) =>
              updateField('maxBatchSize', Number(event.currentTarget.value.replace(/\D/g, '') || '0'))
            }
            required
            valid={fieldValidity(String(draft.maxBatchSize), visibleError('maxBatchSize'))}
            value={String(draft.maxBatchSize)}
          />
        </SettingsGroup>
      </div>

      {hasUnsavedChanges ? (
        <UnsavedChangesBar onDiscard={discardChanges} onSave={() => persist(draft)} />
      ) : null}
    </AppShell>
  )
}

function SettingsGroup({
  children,
  description,
  id,
  title,
}: {
  children: ReactNode
  description: string
  id?: string
  title: string
}) {
  return (
    <div id={id}>
      <Card className="space-y-5">
        <div className="space-y-2 border-b border-[var(--color-border-subtle)] pb-4">
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">{title}</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{description}</p>
        </div>
        <div className="grid gap-4">{children}</div>
      </Card>
    </div>
  )
}

function TextField({
  errorText,
  helperText,
  label,
  name,
  onBlur,
  onChange,
  required = false,
  valid,
  value,
}: {
  errorText?: string
  helperText?: string
  label: string
  name: string
  onBlur?: () => void
  onChange: (event: ChangeEvent<HTMLInputElement>) => void
  required?: boolean
  valid?: boolean | null
  value: string
}) {
  const helperId = errorText || helperText ? `${name}-helper` : undefined
  return (
    <label className="grid gap-2 text-sm font-medium text-[var(--color-text-primary)]">
      <LabelText label={label} required={required} />
      <div className="relative">
        <Input
          aria-describedby={helperId}
          aria-invalid={errorText ? true : undefined}
          className={cn(
            'pr-10 font-normal',
            errorText && 'border-[var(--color-inactive-500)] focus:border-[var(--color-inactive-500)]',
          )}
          name={name}
          onBlur={onBlur}
          onChange={onChange}
          value={value}
        />
        {valid === true ? (
          <span
            aria-label={`${label} is valid`}
            className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[var(--color-active-500)]"
            role="status"
          >
            <CheckIcon className="h-5 w-5" />
          </span>
        ) : valid === false ? (
          <span
            aria-label={`${label} has an error`}
            className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[var(--color-inactive-500)]"
            role="status"
          >
            <CloseIcon className="h-5 w-5" />
          </span>
        ) : null}
      </div>
      {errorText || helperText ? (
        <span
          className={cn(
            'text-caption font-normal',
            errorText ? 'text-[var(--color-inactive-500)]' : 'text-[var(--color-text-secondary)]',
          )}
          id={helperId}
        >
          {errorText ?? helperText}
        </span>
      ) : null}
    </label>
  )
}

function SelectField({
  errorText,
  label,
  name,
  onBlur,
  onChange,
  options,
  required = false,
  value,
}: {
  errorText?: string
  label: string
  name: string
  onBlur?: () => void
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void
  options: Array<{ label: string; value: string }>
  required?: boolean
  value: string
}) {
  const helperId = errorText ? `${name}-helper` : undefined
  return (
    <label className="grid gap-2 text-sm font-medium text-[var(--color-text-primary)]">
      <LabelText label={label} required={required} />
      <Select
        aria-describedby={helperId}
        aria-invalid={errorText ? true : undefined}
        className={cn(
          'font-normal',
          errorText && 'border-[var(--color-inactive-500)] focus:border-[var(--color-inactive-500)]',
        )}
        name={name}
        onBlur={onBlur}
        onChange={onChange}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      {errorText ? (
        <span className="text-caption font-normal text-[var(--color-inactive-500)]" id={helperId}>
          {errorText}
        </span>
      ) : null}
    </label>
  )
}

function LabelText({ label, required }: { label: string; required: boolean }) {
  return (
    <span>
      {label}
      {required ? <span className="text-[var(--color-required-asterisk)]">*</span> : null}
    </span>
  )
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <label className="grid gap-2 text-sm font-medium text-[var(--color-text-primary)]">
      {label}
      <div className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-tertiary)] px-3 py-2 text-base font-normal text-[var(--color-text-secondary)]">
        {value}
      </div>
    </label>
  )
}

function formatIcnInput(value: number | null): string {
  return value === null ? '' : formatIsaControlNumber(value)
}

function parseIcnDraftValue(value: string): number | null {
  if (value.length === 0 || /^0+$/.test(value)) {
    return null
  }

  return Number(value)
}

function serializeSettings(value: SubmitterConfig): string {
  return JSON.stringify(value)
}

type SettingsValidationErrors = Partial<Record<keyof SubmitterConfig, string>>

function validateSettingsDraft(value: SubmitterConfig): SettingsValidationErrors {
  const errors: SettingsValidationErrors = {}

  if (value.organizationName.trim().length === 0) {
    errors.organizationName = 'Organization name is required.'
  }

  if (value.providerNpi.trim().length === 0) {
    errors.providerNpi = 'Provider NPI is required.'
  } else if (!/^\d{10}$/.test(value.providerNpi)) {
    errors.providerNpi = 'Provider NPI must be 10 digits.'
  } else if (!isValidNpi(value.providerNpi)) {
    errors.providerNpi = 'Invalid NPI (Luhn check failed).'
  }

  if (value.tradingPartnerId.trim().length === 0) {
    errors.tradingPartnerId = 'Trading partner ID is required.'
  }

  if (value.contactEmail.trim().length > 0 && !EMAIL_PATTERN.test(value.contactEmail)) {
    errors.contactEmail = 'Enter a valid email address.'
  }

  if (value.payerName.trim().length === 0) {
    errors.payerName = 'Payer name is required.'
  }

  if (value.payerId.trim().length === 0) {
    errors.payerId = 'Payer ID is required.'
  }

  if (value.interchangeReceiverId.trim().length === 0) {
    errors.interchangeReceiverId = 'Receiver ID is required.'
  }

  if (!/^\d{8}$/.test(value.defaultServiceDate)) {
    errors.defaultServiceDate = 'Default service date must be YYYYMMDD.'
  }

  if (!Number.isInteger(value.maxBatchSize) || value.maxBatchSize <= 0) {
    errors.maxBatchSize = 'Max batch size must be greater than zero.'
  }

  return errors
}

function shouldShowFieldError(
  field: keyof SubmitterConfig,
  draft: SubmitterConfig,
  saveAttempted: boolean,
): boolean {
  if (saveAttempted) {
    return true
  }

  if (field === 'providerNpi') {
    return draft.providerNpi.length > 0
  }

  if (field === 'contactEmail') {
    return draft.contactEmail.length > 0
  }

  return false
}

function fieldValidity(
  value: string,
  errorText: string | undefined,
  options: { optional?: boolean } = {},
): boolean | null {
  if (errorText) {
    return false
  }

  if (options.optional && value.trim().length === 0) {
    return null
  }

  return value.trim().length > 0 ? true : null
}

function handleTextChange(
  updateField: <K extends keyof SubmitterConfig>(field: K, value: SubmitterConfig[K]) => void,
) {
  return (event: ChangeEvent<HTMLInputElement>) => {
    updateField(event.currentTarget.name as keyof SubmitterConfig, event.currentTarget.value)
  }
}
