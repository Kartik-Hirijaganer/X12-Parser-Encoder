# Eligibility Template Spec

Canonical columns:

| Column | Required | Description | Example |
| --- | --- | --- | --- |
| `last_name` | Yes | Subscriber last name | `SMITH` |
| `first_name` | Yes | Subscriber first name | `JOHN` |
| `date_of_birth` | Yes | `YYYYMMDD`, `YYYY-MM-DD`, or `MM/DD/YYYY` | `19850115` |
| `gender` | Yes | `M`, `F`, or `U` | `F` |
| `member_id` | Conditional | Medicaid member identifier | `12345678` |
| `ssn` | Conditional | Social Security Number | `999887777` |
| `service_type_code` | No | Defaults from settings when omitted | `30` |
| `service_date` | Yes | Service date in `YYYYMMDD`, `YYYY-MM-DD`, or `MM/DD/YYYY` | `20260412` |
| `service_date_end` | No | End date for range queries | `20260430` |

Rules:

- Provide at least one of `member_id` or `ssn`.
- Extra columns are ignored with warnings.
- `member_id` values that look short are warned on, not auto-corrected.
- Dates are normalized to `YYYYMMDD`.
- Names are uppercased and surrounding whitespace is trimmed.
- Missing `service_type_code` values are filled from `SubmitterConfig.default_service_type_code`.
