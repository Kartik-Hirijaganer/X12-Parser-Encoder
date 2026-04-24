import type { ReactNode } from 'react'

import { NavLink } from 'react-router-dom'

import { APP_VERSION } from '../../utils/constants'
import { Button } from '../ui/Button'
import { ConfigStatusBar } from '../features/ConfigStatusBar'

export function AppShell({
  children,
  subtitle,
  title,
}: {
  children: ReactNode
  subtitle?: string
  title: string
}) {
  return (
    <div className="min-h-screen bg-[var(--color-surface-wash)] text-[var(--color-text-primary)]">
      <header className="sticky top-0 z-20 border-b border-[var(--color-border-default)] bg-[var(--color-surface-primary)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[var(--layout-container-max)] items-center justify-between gap-4 px-6 py-4 lg:px-10">
          <div>
            <NavLink className="text-lg font-semibold text-[var(--color-text-primary)]" to="/">
              DC Medicaid Eligibility Tool
            </NavLink>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink
              className={({ isActive }) =>
                `rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'border-b-2 border-[var(--color-action-500)] text-[var(--color-action-500)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-action-50)] hover:text-[var(--color-text-primary)]'
                }`
              }
              to="/templates"
            >
              Templates
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                `rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'border-b-2 border-[var(--color-action-500)] text-[var(--color-action-500)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-action-50)] hover:text-[var(--color-text-primary)]'
                }`
              }
              to="/settings"
            >
              Settings
            </NavLink>
            <Button
              href="/api/v1/templates/template_spec.md"
              rel="noreferrer"
              target="_blank"
              variant="ghost"
            >
              ?
            </Button>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-[var(--layout-container-max)] flex-col gap-6 px-6 py-8 lg:px-10 lg:py-10">
        <div className="space-y-4">
          <div>
            <h1 className="text-[clamp(1.75rem,4vw,2.25rem)] font-medium tracking-[-0.02em] text-[var(--color-text-primary)]">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-2 max-w-3xl text-lg leading-8 text-[var(--color-text-secondary)]">
                {subtitle}
              </p>
            ) : null}
          </div>
          <ConfigStatusBar />
        </div>
        {children}
      </main>

      <footer className="border-t border-[var(--color-border-default)] bg-[var(--color-surface-primary)]">
        <div className="mx-auto flex max-w-[var(--layout-container-max)] flex-col gap-2 px-6 py-4 text-xs text-[var(--color-text-tertiary)] sm:flex-row sm:items-center sm:justify-between lg:px-10">
          <span>Open Source eligibility workbench</span>
          <span>v{APP_VERSION}</span>
        </div>
      </footer>
    </div>
  )
}
