import { useId, useRef, useState } from 'react'

import { cn } from '../../utils/cn'
import { Button } from './Button'
import { UploadIcon } from './Icons'

type FileUploadVariant = 'dropzone' | 'button'

export function FileUpload({
  accept,
  buttonLabel = 'Select File',
  description,
  disabled = false,
  onFileSelect,
  title,
  variant = 'dropzone',
}: {
  accept?: string
  buttonLabel?: string
  description?: string
  disabled?: boolean
  onFileSelect: (file: File) => void
  title?: string
  variant?: FileUploadVariant
}) {
  const [isDragging, setIsDragging] = useState(false)
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement | null>(null)

  function openPicker() {
    if (!disabled) {
      inputRef.current?.click()
    }
  }

  function handleFiles(files: FileList | File[] | null) {
    const file = Array.isArray(files) ? files[0] ?? null : files?.item(0) ?? null
    if (file) {
      onFileSelect(file)
    }
  }

  if (variant === 'button') {
    return (
      <>
        <input
          ref={inputRef}
          accept={accept}
          className="hidden"
          id={inputId}
          onChange={(event) => handleFiles(event.currentTarget.files)}
          type="file"
        />
        <Button disabled={disabled} onClick={openPicker} variant="secondary">
          {buttonLabel}
        </Button>
      </>
    )
  }

  return (
    <div className="w-full">
      <input
        ref={inputRef}
        accept={accept}
        className="hidden"
        id={inputId}
        onChange={(event) => handleFiles(event.currentTarget.files)}
        type="file"
      />
      <div
        className={cn(
          'flex w-full flex-col items-center justify-center gap-3 rounded-[var(--radius-xl)] border-2 border-dashed px-6 py-10 text-center transition-[background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)] focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[var(--color-focus-ring)]',
          disabled
            ? 'cursor-not-allowed border-[var(--color-border-default)] bg-[var(--color-surface-secondary)] text-[var(--color-text-disabled)]'
            : 'cursor-pointer border-[var(--color-border-default)] bg-[linear-gradient(to_bottom,var(--color-surface-tertiary),var(--color-surface-wash))] text-[var(--color-text-primary)] hover:border-[var(--color-action-500)] hover:bg-[var(--color-action-50)]',
          isDragging && !disabled
            ? 'border-[var(--color-action-500)] bg-[var(--color-action-50)]'
            : '',
        )}
        onClick={openPicker}
        onDragEnter={(event) => {
          event.preventDefault()
          if (!disabled) {
            setIsDragging(true)
          }
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setIsDragging(false)
        }}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) {
            setIsDragging(true)
          }
        }}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          if (!disabled) {
            handleFiles(event.dataTransfer.files)
          }
        }}
        onKeyDown={(event) => {
          if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
            event.preventDefault()
            openPicker()
          }
        }}
        role="button"
        tabIndex={disabled ? -1 : 0}
      >
        <span className="rounded-full bg-[var(--color-surface-primary)] p-4 text-[var(--color-text-secondary)] shadow-[var(--shadow-sm)]">
          <UploadIcon className="h-8 w-8" />
        </span>
        <span className="text-[16px] font-medium">{title ?? 'Drag & drop any file here'}</span>
        <span className="max-w-xl text-[14px] text-[var(--color-text-secondary)]">
          {description ?? 'or click to browse (.xlsx .csv .x12 .edi)'}
        </span>
        <Button disabled={disabled} onClick={openPicker} variant="primary">
          {buttonLabel}
        </Button>
      </div>
    </div>
  )
}
