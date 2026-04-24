import type { ReactNode } from 'react'

import { Card } from '../ui/Card'
import { FileUpload } from '../ui/FileUpload'

export function ActionCard({
  accept,
  description,
  disabled = false,
  helper,
  icon,
  onFileSelect,
  title,
}: {
  accept?: string
  description: string
  disabled?: boolean
  helper?: ReactNode
  icon: ReactNode
  onFileSelect: (file: File) => void
  title: string
}) {
  return (
    <Card className="flex h-full flex-col gap-5" variant="action">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-action-50)] text-[var(--color-action-500)]">
        {icon}
      </div>
      <div>
        <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-secondary)]">{description}</p>
      </div>
      <div className="mt-auto flex flex-col gap-3">
        <FileUpload
          accept={accept}
          buttonLabel="Select File"
          disabled={disabled}
          onFileSelect={onFileSelect}
          variant="button"
        />
        {helper}
      </div>
    </Card>
  )
}
