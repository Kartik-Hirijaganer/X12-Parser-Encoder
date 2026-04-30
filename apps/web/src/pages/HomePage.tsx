import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

import { useFileDropAffordance } from '../hooks/useFileDropAffordance'
import { useReducedMotionPreference } from '../hooks/useReducedMotionPreference'
import { useSettings } from '../hooks/useSettings'
import { convertUpload, ApiError, ApiTimeoutError } from '../services/api'
import { buildX12PreviewSummary, detectWorkflowFromFile } from '../utils/fileDetection'
import { cn } from '../utils/cn'
import { MAX_ISA_CONTROL_NUMBER } from '../utils/constants'
import { ActionCard } from '../components/features/ActionCard'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FileUpload } from '../components/ui/FileUpload'
import { DocumentIcon, SearchIcon, ShieldIcon, WarningIcon } from '../components/ui/Icons'
import { Spinner } from '../components/ui/Spinner'

type HomeErrorState = {
  message: string
  suggestion?: string | null
}

export function HomePage() {
  const navigate = useNavigate()
  const { hasRequiredSettings, hasUsableIcn, settings } = useSettings()
  const [error, setError] = useState<HomeErrorState | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [timeoutFile, setTimeoutFile] = useState<File | null>(null)
  const isDraggingWindow = useFileDropAffordance()
  const prefersReducedMotion = useReducedMotionPreference()
  const shouldPulse = isDraggingWindow && !isProcessing && !prefersReducedMotion
  const pulseDurationSeconds = useMemo(() => readPulseDurationSeconds(), [])

  async function handleFile(file: File, preferredFlow?: 'generate' | 'validate' | 'parse') {
    setError(null)
    setTimeoutFile(null)
    setIsProcessing(true)

    try {
      const detection =
        preferredFlow === 'generate'
          ? { workflow: 'generate' as const, rawText: null }
          : await detectWorkflowFromFile(file)
      const workflow = preferredFlow === 'generate' ? 'generate' : detection.workflow

      if (workflow === 'generate') {
        if (!hasRequiredSettings) {
          setError({
            message: 'Configure your provider details in Settings before generating files.',
          })
          return
        }
        if (!hasUsableIcn) {
          setError({
            message:
              settings.lastIsaControlNumber === MAX_ISA_CONTROL_NUMBER
                ? 'The ICN range is exhausted at 999999999. Contact Gainwell or confirm a new trading-partner control-number policy before generating files.'
                : 'Set the last submitted ICN in Settings before generating files.',
          })
          return
        }

        const response = await convertUpload(file, settings)
        navigate('/preview', {
          state: {
            flow: 'generate',
            filename: file.name,
            fileSize: file.size,
            response,
          },
        })
        return
      }

      if (workflow === 'validate' || workflow === 'parse') {
        if (!detection.rawText) {
          throw new Error('The X12 file could not be read in the browser.')
        }
        navigate('/preview', {
          state: {
            flow: workflow,
            filename: file.name,
            fileSize: file.size,
            rawText: detection.rawText,
            preview: buildX12PreviewSummary(detection.rawText),
          },
        })
        return
      }

      setError({
        message: 'This file type is not supported. Use the canonical spreadsheet template or an X12/EDI file.',
      })
    } catch (caughtError) {
      if (caughtError instanceof ApiTimeoutError) {
        setTimeoutFile(file)
        return
      }

      const nextError =
        caughtError instanceof ApiError
          ? { message: caughtError.message, suggestion: caughtError.suggestion }
          : { message: caughtError instanceof Error ? caughtError.message : 'The upload failed.' }
      setError(nextError)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <AppShell
      subtitle="Drop a spreadsheet to generate a 270, upload a 270 to validate it, or upload a 271 to review eligibility results."
      title="What would you like to do?"
    >
      {error ? (
        <Banner variant="error">
          <p>{error.message}</p>
          {error.suggestion ? (
            <p className="mt-1 text-caption text-[inherit]">Suggested fix: {error.suggestion}</p>
          ) : null}
        </Banner>
      ) : null}

      {timeoutFile ? (
        <Banner
          actions={
            <>
              <Button onClick={() => void handleFile(timeoutFile)} size="sm" variant="primary">
                Retry
              </Button>
              <Button onClick={() => setTimeoutFile(null)} size="sm" variant="secondary">
                Cancel
              </Button>
            </>
          }
          title="Request timed out"
          variant="warning"
        >
          Processing is taking longer than expected. This may happen with very large files.
        </Banner>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-3">
        <ActionCard
          accept=".xlsx,.csv,.tsv,.txt"
          description="Upload the canonical Excel or CSV template to create an eligibility inquiry file."
          disabled={!hasRequiredSettings || !hasUsableIcn || isProcessing}
          helper={
            !hasRequiredSettings ? (
              <p className="flex items-center gap-2 text-caption text-[var(--color-warning-500)]">
                <WarningIcon className="h-4 w-4" />
                Configure your provider details in Settings first.
              </p>
            ) : !hasUsableIcn ? (
              <p className="flex items-center gap-2 text-caption text-[var(--color-warning-500)]">
                <WarningIcon className="h-4 w-4" />
                {settings.lastIsaControlNumber === MAX_ISA_CONTROL_NUMBER
                  ? 'ICN exhausted at 999999999.'
                  : 'Set the last submitted ICN in Settings first.'}
              </p>
            ) : null
          }
          icon={<DocumentIcon className="h-7 w-7" />}
          onFileSelect={(file) => void handleFile(file, 'generate')}
          title="Generate 270"
        />
        <ActionCard
          accept=".x12,.edi,.txt"
          description="Upload an X12 270 file to run the current validator and see actionable issues."
          disabled={isProcessing}
          icon={<ShieldIcon className="h-7 w-7" />}
          onFileSelect={(file) => void handleFile(file, 'validate')}
          title="Validate 270"
        />
        <ActionCard
          accept=".x12,.edi,.txt"
          description="Upload an X12 271 response to review eligibility status, plan details, and AAA rejects."
          disabled={isProcessing}
          icon={<SearchIcon className="h-7 w-7" />}
          onFileSelect={(file) => void handleFile(file, 'parse')}
          title="Parse 271"
        />
      </section>

      <motion.div
        animate={shouldPulse ? { scale: 1.01 } : { scale: 1 }}
        aria-live="polite"
        className={cn('rounded-[var(--radius-2xl)]', shouldPulse ? 'shadow-[var(--shadow-md)]' : '')}
        data-drop-pulsing={shouldPulse ? 'true' : 'false'}
        transition={
          prefersReducedMotion
            ? { duration: 0 }
            : {
                duration: pulseDurationSeconds,
                ease: 'easeInOut',
                repeat: shouldPulse ? Infinity : 0,
                repeatType: 'reverse',
              }
        }
      >
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                Or drag and drop any file here
              </h2>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                The workbench routes spreadsheets to Generate and detects 270 vs 271 from the X12 content.
              </p>
            </div>
            {isProcessing ? (
              <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                <Spinner />
                Processing upload...
              </div>
            ) : null}
          </div>
          <FileUpload disabled={isProcessing} onFileSelect={(file) => void handleFile(file)} />
        </Card>
      </motion.div>
    </AppShell>
  )
}

function readPulseDurationSeconds(): number {
  if (typeof window === 'undefined') {
    return 0.9
  }

  const duration = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--duration-slow')
    .trim()

  if (duration.endsWith('ms')) {
    const parsed = Number(duration.slice(0, -2))
    return Number.isFinite(parsed) ? (parsed * 3) / 1000 : 0.9
  }

  if (duration.endsWith('s')) {
    const parsed = Number(duration.slice(0, -1))
    return Number.isFinite(parsed) ? parsed * 3 : 0.9
  }

  return 0.9
}
