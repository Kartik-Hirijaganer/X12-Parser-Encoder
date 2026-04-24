import { useState } from 'react'

import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog'
import { Drawer } from '../components/ui/Drawer'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBoundary } from '../components/ui/ErrorBoundary'
import { DocumentIcon, SearchIcon, WarningIcon } from '../components/ui/Icons'
import { Modal } from '../components/ui/Modal'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Skeleton } from '../components/ui/Skeleton'
import { toast } from '../components/ui/Toast'
import { Tooltip } from '../components/ui/Tooltip'

function ExplosiveChild({ boom }: { boom: boolean }) {
  if (boom) {
    throw new Error('Intentional gallery error')
  }
  return <p className="text-sm text-[var(--color-text-secondary)]">Child renders normally.</p>
}

export function UiGalleryPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [progress, setProgress] = useState(40)
  const [boom, setBoom] = useState(false)

  return (
    <AppShell subtitle="Dev-only gallery for every shared primitive." title="UI Gallery">
      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Toast</h2>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => toast.success('Saved')} variant="primary">
            Success
          </Button>
          <Button onClick={() => toast.info('Heads up')} variant="secondary">
            Info
          </Button>
          <Button onClick={() => toast.warning('Check this')} variant="secondary">
            Warning
          </Button>
          <Button onClick={() => toast.error('Something failed')} variant="secondary">
            Error
          </Button>
        </div>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Modal</h2>
        <Button onClick={() => setModalOpen(true)} variant="primary">
          Open modal
        </Button>
        <Modal
          description="Modal primitive with focus trap and ESC handling."
          footer={
            <Button onClick={() => setModalOpen(false)} variant="primary">
              Got it
            </Button>
          }
          onOpenChange={setModalOpen}
          open={modalOpen}
          title="Modal example"
        >
          <p>Content composed from tokens. Close via ESC, overlay click, or the button.</p>
        </Modal>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Drawer</h2>
        <Button onClick={() => setDrawerOpen(true)} variant="primary">
          Open drawer
        </Button>
        <Drawer
          description="Slides in from the right."
          onOpenChange={setDrawerOpen}
          open={drawerOpen}
          title="Drawer example"
        >
          <p className="py-4">Put filter UI or a form here.</p>
        </Drawer>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Tooltip</h2>
        <Tooltip content="Copies X12 output to the system clipboard">
          <Button variant="secondary">Hover me</Button>
        </Tooltip>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Skeleton</h2>
        <Skeleton height="1rem" radius="md" width="60%" />
        <Skeleton height="1rem" radius="md" width="80%" />
        <Skeleton height="1rem" radius="md" width="40%" />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">ProgressBar</h2>
        <ProgressBar label="Upload" value={progress} variant="determinate" />
        <ProgressBar label="Processing" variant="indeterminate" />
        <div className="flex gap-2">
          <Button
            onClick={() => setProgress((current) => Math.max(0, current - 10))}
            variant="secondary"
          >
            -10%
          </Button>
          <Button
            onClick={() => setProgress((current) => Math.min(100, current + 10))}
            variant="secondary"
          >
            +10%
          </Button>
        </div>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">EmptyState</h2>
        <EmptyState
          action={<Button variant="primary">Upload file</Button>}
          description="Upload a spreadsheet to populate this dashboard."
          icon={<DocumentIcon className="h-10 w-10" />}
          title="No data yet"
        />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">ConfirmationDialog</h2>
        <Button onClick={() => setConfirmOpen(true)} variant="secondary">
          Delete something
        </Button>
        <ConfirmationDialog
          confirmLabel="Delete"
          description="This cannot be undone."
          destructive
          onConfirm={() => toast.success('Deleted')}
          onOpenChange={setConfirmOpen}
          open={confirmOpen}
          title="Delete this record?"
        />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">ErrorBoundary</h2>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setBoom(true)} variant="secondary">
            Throw error in child
          </Button>
          <Button onClick={() => setBoom(false)} variant="ghost">
            Reset
          </Button>
        </div>
        <ErrorBoundary>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border-default)] p-4">
            <ExplosiveChild boom={boom} />
          </div>
        </ErrorBoundary>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Icon reference</h2>
        <div className="flex gap-3 text-[var(--color-text-secondary)]">
          <SearchIcon className="h-6 w-6" />
          <WarningIcon className="h-6 w-6" />
          <DocumentIcon className="h-6 w-6" />
        </div>
      </Card>
    </AppShell>
  )
}
