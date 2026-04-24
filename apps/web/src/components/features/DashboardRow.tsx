import type { BenefitEntity, EligibilityResult, EligibilitySegment } from '../../types/api'

const ENTITY_LABELS: Record<string, string> = {
  P3: 'Primary Payer',
  P5: 'Plan Sponsor',
  '1I': 'Preferred Provider',
}

export function DashboardRow({ result }: { result: EligibilityResult }) {
  const entityGroups = groupBenefitEntities(result.benefitEntities)

  return (
    <div className="space-y-5">
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] p-4">
        <h4 className="text-xs font-semibold uppercase text-[var(--color-text-secondary)]">Status Reason</h4>
        <p className="mt-1 text-base font-semibold text-[var(--color-text-primary)]">
          {result.statusReason ?? 'No status reason returned'}
        </p>
        {result.traceNumber || result.stControlNumber ? (
          <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
            {result.traceNumber ? `Trace ${result.traceNumber}` : null}
            {result.traceNumber && result.stControlNumber ? ' • ' : null}
            {result.stControlNumber ? `ST ${result.stControlNumber}` : null}
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">Eligibility Segments</h4>
          {result.eligibilitySegments.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">No eligibility segments returned.</p>
          ) : (
            <ul className="space-y-2 text-sm text-[var(--color-text-primary)]">
              {result.eligibilitySegments.map((segment, index) => (
                <li key={`${segment.eligibilityCode}-${index}`}>
                  {segment.planCoverageDescription ?? 'Coverage returned'} • Code{' '}
                  {segment.eligibilityCode}
                  {formatServiceTypes(segment)}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">Benefit Entities</h4>
          {entityGroups.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">
              No PCP or plan entity details returned.
            </p>
          ) : (
            <div className="space-y-3">
              {entityGroups.map((group) => (
                <section className="space-y-2" key={group.code}>
                  <h5 className="text-xs font-semibold text-[var(--color-text-primary)]">
                    {entityGroupLabel(group.code)}
                  </h5>
                  <ul className="space-y-3 text-sm text-[var(--color-text-primary)]">
                    {group.entities.map((entity, index) => (
                      <li key={`${group.code}-${entity.identifier ?? entity.name ?? index}`}>
                        <p>{entity.name ?? entity.description ?? entity.identifier ?? 'Entity name not returned'}</p>
                        {entity.identifier || entity.qualifier ? (
                          <p className="text-xs text-[var(--color-text-secondary)]">
                            {entity.qualifier ? `${entity.qualifier} ` : null}
                            {entity.identifier ?? null}
                          </p>
                        ) : null}
                        {entity.contacts.length > 0 ? (
                          <ul className="mt-1 space-y-1 text-xs text-[var(--color-text-secondary)]">
                            {entity.contacts.map((contact) => (
                              <li key={contact}>{contact}</li>
                            ))}
                          </ul>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">AAA Errors</h4>
          {result.aaaErrors.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">No AAA errors returned.</p>
          ) : (
            <ul className="space-y-2 text-sm text-[var(--color-text-primary)]">
              {result.aaaErrors.map((error, index) => (
                <li key={`${error.code}-${index}`}>
                  {error.message}
                  {error.suggestion ? (
                    <span className="text-[var(--color-text-secondary)]"> • {error.suggestion}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function formatServiceTypes(segment: EligibilitySegment): string {
  const serviceTypes = segment.serviceTypeCodes.length
    ? segment.serviceTypeCodes
    : segment.serviceTypeCode
      ? [segment.serviceTypeCode]
      : []
  return serviceTypes.length ? ` • Service ${serviceTypes.join(', ')}` : ''
}

function groupBenefitEntities(entities: BenefitEntity[]): Array<{
  code: string
  entities: BenefitEntity[]
}> {
  const groups = new Map<string, BenefitEntity[]>()
  for (const entity of entities) {
    const code = entity.entityIdentifierCode ?? 'other'
    groups.set(code, [...(groups.get(code) ?? []), entity])
  }

  return [...groups.entries()]
    .sort(([left], [right]) => entitySortRank(left) - entitySortRank(right))
    .map(([code, groupedEntities]) => ({
      code,
      entities: groupedEntities,
    }))
}

function entityGroupLabel(code: string): string {
  if (code === 'other') {
    return 'Other Entity'
  }
  return `${code} ${ENTITY_LABELS[code] ?? 'Benefit Entity'}`
}

function entitySortRank(code: string): number {
  return ['P3', 'P5', '1I'].indexOf(code) === -1 ? 99 : ['P3', 'P5', '1I'].indexOf(code)
}
