# Security Policy

## Supported Release Line

The current supported release line is `0.1.x`.

## Reporting

If you discover a security issue, do not open a public issue with exploit details. Report it privately to the maintainers and include:

- affected version
- reproduction steps
- impact assessment
- suggested remediation if known

## Data Retention and Cleanup Policy

### Browser `localStorage`

- Only `SubmitterConfig` settings persist.
- No PHI, uploaded filenames, raw X12, patient rows, or parsed eligibility results are stored.

### Server Side

- Zero retention after request completion.
- No server-side caches or durable upload storage are used.
- `SpooledTemporaryFile` handling is limited to in-memory request parsing and objects are discarded after the response lifecycle.

### Cloud Run or Hosted Logs

- Logs contain correlation IDs, endpoints, status codes, durations, and sanitized upload metadata only.
- No filenames, member names, identifiers, raw X12 payloads, or worksheet cell data may be logged.
- Correlation IDs are request-linkable but contain no PHI.
- Default cloud log retention is typically 30 days and should be configured per deployment.

### Browser Memory

- Parsed eligibility results remain in React state only.
- No `IndexedDB`, `sessionStorage`, or `Cache API` storage is used for workflow data.
- Data is released when the user navigates away or closes the tab.

## Production Readiness Gate

Real PHI should only be processed after all of the following are true:

- SNIP 1 through 5 checks are green on synthetic fixtures.
- DC Medicaid profile behavior matches the intended companion-guide abstraction.
- PHI boundary tests are green: no filenames in logs, no temp files on disk, no client-side PHI persistence.
- External identity boundary is configured and tested.
- Rate limiting and input hardening are enabled for production.
- Deep health and `/metrics` are healthy.
- This retention policy has been reviewed by the stakeholder responsible for deployment.
