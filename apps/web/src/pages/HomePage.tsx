import { useSettings } from '../hooks/useSettings'
import { isValidNpi } from '../utils/npiValidator'

const checklist = [
  'Library packaging and smoke tests are in place.',
  'FastAPI app boots with request correlation IDs.',
  'React app is wired to Tailwind CSS v4 and local settings storage.',
]

export function HomePage() {
  const settings = useSettings()
  const providerConfigured = Boolean(
    settings.organizationName && settings.providerNpi && settings.tradingPartnerId,
  )
  const npiLooksValid = settings.providerNpi ? isValidNpi(settings.providerNpi) : false

  return (
    <main className="min-h-screen px-6 py-10 text-[var(--color-ink)] sm:px-10 lg:px-14">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="rounded-[2rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-8 shadow-[var(--shadow-panel)]">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--color-primary)]">
                Phase 0 Scaffold
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.03em]">
                X12 Eligibility Workbench
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--color-muted)]">
                The repo is now wired for install, lint, test, and frontend dev without
                introducing any transaction-domain behavior ahead of schedule.
              </p>
            </div>
            <div className="rounded-[1.5rem] bg-[var(--color-primary-soft)] px-5 py-4 text-sm">
              <div className="font-semibold text-[var(--color-primary-strong)]">
                Current payer profile
              </div>
              <div className="mt-1">{settings.payerName || 'DC MEDICAID'}</div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <article className="rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-8 shadow-[var(--shadow-panel)]">
            <h2 className="text-2xl font-semibold tracking-[-0.02em]">Bootstrap checklist</h2>
            <ul className="mt-6 space-y-4">
              {checklist.map((item) => (
                <li
                  key={item}
                  className="rounded-2xl border border-[var(--color-border)] bg-white px-4 py-4 text-sm leading-6"
                >
                  {item}
                </li>
              ))}
            </ul>
          </article>

          <aside className="rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-8 shadow-[var(--shadow-panel)]">
            <h2 className="text-2xl font-semibold tracking-[-0.02em]">Settings status</h2>
            <dl className="mt-6 grid gap-4 text-sm">
              <div className="rounded-2xl bg-[var(--color-surface)] px-4 py-4">
                <dt className="font-medium text-[var(--color-muted)]">Organization</dt>
                <dd className="mt-1 font-semibold">
                  {settings.organizationName || 'Not configured yet'}
                </dd>
              </div>
              <div className="rounded-2xl bg-[var(--color-surface)] px-4 py-4">
                <dt className="font-medium text-[var(--color-muted)]">Provider NPI</dt>
                <dd className="mt-1 font-semibold">
                  {settings.providerNpi || 'Not configured yet'}
                </dd>
                <p
                  className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                    npiLooksValid
                      ? 'bg-[var(--color-ok-soft)] text-[var(--color-ok)]'
                      : 'bg-[var(--color-warning-soft)] text-[var(--color-warning)]'
                  }`}
                >
                  {npiLooksValid ? 'Luhn-valid' : 'Awaiting valid NPI'}
                </p>
              </div>
              <div className="rounded-2xl bg-[var(--color-surface)] px-4 py-4">
                <dt className="font-medium text-[var(--color-muted)]">Ready for Generate 270</dt>
                <dd
                  className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                    providerConfigured
                      ? 'bg-[var(--color-ok-soft)] text-[var(--color-ok)]'
                      : 'bg-[var(--color-warning-soft)] text-[var(--color-warning)]'
                  }`}
                >
                  {providerConfigured ? 'Provider defaults present' : 'Settings still required'}
                </dd>
              </div>
            </dl>
          </aside>
        </section>
      </div>
    </main>
  )
}
