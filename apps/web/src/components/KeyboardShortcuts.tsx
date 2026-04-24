import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'
import { Modal } from './ui/Modal'

interface ShortcutEntry {
  keys: readonly string[]
  label: string
  description: string
}

const SHORTCUTS: readonly { section: string; entries: readonly ShortcutEntry[] }[] = [
  {
    section: 'General',
    entries: [
      { keys: ['?'], label: '?', description: 'Open this keyboard shortcuts dialog' },
      { keys: ['Esc'], label: 'Esc', description: 'Close any open modal or drawer' },
    ],
  },
  {
    section: 'Navigation',
    entries: [
      { keys: ['g', 'h'], label: 'g then h', description: 'Go to Home' },
      { keys: ['g', 'd'], label: 'g then d', description: 'Go to Dashboard' },
      { keys: ['g', 't'], label: 'g then t', description: 'Go to Templates' },
      { keys: ['g', 's'], label: 'g then s', description: 'Go to Settings' },
    ],
  },
]

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  useKeyboardShortcut([
    {
      keys: '?',
      handler: (event) => {
        event.preventDefault()
        setOpen((current) => !current)
      },
    },
    {
      keys: ['g', 'h'],
      handler: (event) => {
        event.preventDefault()
        navigate('/')
      },
    },
    {
      keys: ['g', 'd'],
      handler: (event) => {
        event.preventDefault()
        navigate('/dashboard')
      },
    },
    {
      keys: ['g', 't'],
      handler: (event) => {
        event.preventDefault()
        navigate('/templates')
      },
    },
    {
      keys: ['g', 's'],
      handler: (event) => {
        event.preventDefault()
        navigate('/settings')
      },
    },
  ])

  return (
    <Modal
      description="Press a key combination to navigate quickly. Sequences must be pressed within one second."
      onOpenChange={setOpen}
      open={open}
      title="Keyboard shortcuts"
    >
      <div className="space-y-6">
        {SHORTCUTS.map((group) => (
          <section className="space-y-2" key={group.section}>
            <h3 className="text-caption font-semibold uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">
              {group.section}
            </h3>
            <ul className="divide-y divide-[var(--color-border-subtle)]">
              {group.entries.map((entry) => (
                <li className="flex items-center justify-between gap-4 py-2" key={entry.label}>
                  <span className="text-sm text-[var(--color-text-primary)]">{entry.description}</span>
                  <kbd className="rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-surface-subtle)] px-2 py-1 font-mono text-caption text-[var(--color-text-primary)]">
                    {entry.label}
                  </kbd>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Modal>
  )
}
