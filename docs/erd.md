# Entity-Relationship Diagram — 837I / 837P / 835 Domain Model

**Document status:** Draft for implementation kickoff.
**Owner:** Platform Engineering (x12-edi-tools).
**Paired artifacts:** [`erd.er`](./erd.er) (eralchemy DSL source), [`erd.html`](./erd.html) (rendered SVG preview).
**Implementation plan:** [`../.agents/plans/837i-837p-835-implementation-plan.md`](../.agents/plans/837i-837p-835-implementation-plan.md).

---

## 1. Purpose and Scope

This ERD describes the **logical** domain model used by the `x12-edi-tools` Python library to
represent ANSI X12 healthcare claim submission (837I / 837P) and remittance advice (835)
transactions.

It is **not** a physical database schema:

- The library is stateless. No table is persisted by the library itself.
- The web application (`apps/web`) never persists PHI to browser storage.
- The API service (`apps/api`) never retains uploaded payloads beyond request scope.

The ERD exists so that:

1. Implementation agents share a single definition of each entity, its fields, and its
   relationships, independent of how each transaction serializes it.
2. Downstream consumers (operator tooling, data warehouses, MDM) have an unambiguous
   contract when they choose to **persist** parsed output on their side.
3. Validation rules, payer overrides, and reconciliation logic can be expressed against a
   stable domain vocabulary rather than against raw segments.

### What this ERD covers

- The **outbound** claim submission domain (837I and 837P).
- The **inbound** remittance advice domain (835).
- The **correlation** entities that tie 835 back to the originating 837.
- The **envelope** entities common to all X12 transactions (ISA/GS/ST).
- The **payer configuration** entities (companion guides, overrides).
- The **extensibility** hooks for future transactions (999, 277CA, 276/277, 278).

### What this ERD does not cover

- The existing 270/271 eligibility domain (already implemented; see
  [`packages/x12-edi-tools/src/x12_edi_tools/models/transactions.py`](../packages/x12-edi-tools/src/x12_edi_tools/models/transactions.py)).
  That model is preserved unchanged; new entities in this ERD are additive.
- Any physical storage choices (Postgres, DynamoDB, S3 object layout).
- Any authentication/authorization schema for the API service.

---

## 2. How to Read This Document

- **Entity names** use `PascalCase` and correspond directly to Pydantic v2 models under
  `packages/x12-edi-tools/src/x12_edi_tools/models/`.
- **Field names** use `snake_case` in Python but are shown here in their model form.
- **Cardinality** notation:
  - `1..1` — exactly one
  - `0..1` — optional, at most one
  - `1..*` — one or more
  - `0..*` — any number, including zero
- **PHI flag** marks fields that may carry Protected Health Information. PHI fields must
  never appear in logs, metrics, or error messages.
- **X12 origin** references the segment/loop the field is derived from, for traceability.

### Regenerating the diagram

The visual diagram is produced from [`erd.er`](./erd.er) via `eralchemy`:

```bash
pip install eralchemy
eralchemy -i docs/erd.er -o docs/erd.svg
# or, for a markdown mermaid variant:
eralchemy -i docs/erd.er -o docs/erd.mmd
```

The `docs/erd.html` wrapper embeds the resulting SVG with a system light/dark theme.

---

## 3. Domain Overview

The domain partitions cleanly into five clusters:

| Cluster | Purpose | Primary Entities |
|---|---|---|
| **Envelope** | X12 framing common to all transactions | `Interchange`, `FunctionalGroup`, `TransactionSet` |
| **Parties** | The humans and organizations on a claim | `Subscriber`, `Patient`, `Provider`, `Payer`, `Submitter`, `ServiceFacility` |
| **Claim (outbound)** | 837I and 837P submission data | `Claim`, `ServiceLine`, `Diagnosis`, `ClaimSupplementalInfo` |
| **Remittance (inbound)** | 835 advice and reconciliation | `Remittance`, `RemittancePayment`, `ClaimPayment`, `ServicePayment`, `Adjustment` |
| **Config & Audit** | Payer overrides, control numbers, correlation | `PayerProfile`, `CompanionGuide`, `ControlNumberState`, `CorrelationEvent` |

```
                +-----------------+
                |  Interchange    |  (ISA/IEA)
                +--------+--------+
                         |
                         | 1..*
                +--------v--------+
                | FunctionalGroup |  (GS/GE)
                +--------+--------+
                         |
                         | 1..*
                +--------v--------+
                | TransactionSet  |  (ST/SE)  -- 837I / 837P / 835
                +--------+--------+
                         |
          +--------------+---------------+
          |                              |
    (837 outbound)                (835 inbound)
          |                              |
    +-----v------+                +------v------+
    |   Claim    |<-- reconciles--| ClaimPayment|
    +-----+------+                +------+------+
          | 1..*                         | 1..*
    +-----v------+                +------v------+
    | ServiceLine|<-- pays ------| ServicePayment|
    +------------+                +---------------+
                                         | 1..*
                                  +------v------+
                                  |  Adjustment |
                                  +-------------+
```

---

## 4. Entity Reference

### 4.1 Envelope Cluster

#### `Interchange`
Top-level container for one ISA/IEA envelope. Already exists; extended with `transaction_type` enumeration.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `sender_id` | str(15) | No | ISA06 | Trading partner ID of sender |
| `receiver_id` | str(15) | No | ISA08 | Trading partner ID of receiver |
| `interchange_control_number` | int | No | ISA13 | Must be unique per sender within retention window |
| `interchange_date` | date | No | ISA09 | |
| `interchange_time` | time | No | ISA10 | |
| `usage_indicator` | enum(P,T) | No | ISA15 | P=production, T=test |
| `functional_groups` | list[FunctionalGroup] | No | — | 1..* |

#### `FunctionalGroup`
One GS/GE envelope. Groups transactions sharing a functional identifier code.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `functional_id_code` | enum(HC,HP,FA,HR,HI,HB) | No | GS01 | HC=837, HP=835, FA=999, HR=276, HI=278, HB=270/271 |
| `sender_code` | str | No | GS02 | |
| `receiver_code` | str | No | GS03 | |
| `group_control_number` | int | No | GS06 | |
| `version_release` | str | No | GS08 | e.g., `005010X222A1` |
| `transaction_sets` | list[TransactionSet] | No | — | 1..* |

#### `TransactionSet`
One ST/SE envelope. Polymorphic across 837I, 837P, 835, etc.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `transaction_set_code` | enum(270,271,837,835,999,277,276,278) | No | ST01 | |
| `transaction_set_control_number` | str | No | ST02 | |
| `implementation_reference` | str | No | ST03 | e.g., `005010X223A2` |
| `body` | Union[EligibilityRequest, EligibilityResponse, Claim, Remittance, ...] | Yes | — | Payload polymorphism |

**Relationships**
- `Interchange` **1..1 → 1..\*** `FunctionalGroup`
- `FunctionalGroup` **1..1 → 1..\*** `TransactionSet`

---

### 4.2 Parties Cluster

#### `Submitter`
The entity sending the claim. Typically the billing provider or a clearinghouse.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `organization_name` | str | No | NM103 (Loop 1000A) | |
| `etin` | str | No | NM109 | Electronic transmitter identification number |
| `contact_name` | str | No | PER02 | |
| `contact_phone` | str | No | PER04 | |
| `contact_email` | str | No | PER06 | |

#### `Receiver`
The destination entity (clearinghouse or payer).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `organization_name` | str | No | NM103 (Loop 1000B) | |
| `payer_id` | str | No | NM109 | |

#### `Provider`
Unified party for billing, rendering, attending, operating, referring, supervising, and pay-to providers. Role is carried by `role` discriminator.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `role` | enum(BILLING, PAY_TO, RENDERING, ATTENDING, OPERATING, REFERRING, SUPERVISING, ORDERING, SERVICE_FACILITY, OTHER_OPERATING) | No | — | Discriminator |
| `npi` | str(10) | No | NM109 (XX qualifier) | |
| `tax_id` | str | No | REF (EI/SY) | |
| `taxonomy_code` | str | No | PRV03 | |
| `organization_name` | str | No | NM103 | Either organization or person must be set |
| `first_name` | str | Yes | NM104 | |
| `last_name` | str | Yes | NM103 | |
| `address` | Address | Partial | N3/N4 | Street/city/state/zip |
| `secondary_identifiers` | list[SecondaryId] | No | REF | Payer-specific provider IDs |

#### `Subscriber`
The insured person (policyholder). May also be the patient.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `member_id` | str | Yes | NM109 (Loop 2010BA) | |
| `first_name` | str | Yes | NM104 | |
| `last_name` | str | Yes | NM103 | |
| `dob` | date | Yes | DMG02 | |
| `gender` | enum(M,F,U) | Yes | DMG03 | |
| `address` | Address | Yes | N3/N4 | |
| `relationship_code` | enum(18=self, ...) | No | SBR02 | 18 = patient is subscriber |
| `payer_responsibility` | enum(P=primary, S=secondary, T=tertiary) | No | SBR01 | |
| `group_number` | str | Yes | SBR03 | |
| `plan_name` | str | No | SBR04 | |

#### `Patient`
The person receiving care. If `subscriber.relationship_code == 18`, this entity is not separately serialized.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `first_name` | str | Yes | NM104 (Loop 2010CA) | |
| `last_name` | str | Yes | NM103 | |
| `dob` | date | Yes | DMG02 | |
| `gender` | enum(M,F,U) | Yes | DMG03 | |
| `relationship_to_subscriber` | enum | No | PAT01 | |
| `address` | Address | Yes | N3/N4 | |

#### `Payer`
The payer (insurance company, Medicare, Medicaid, etc.).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `name` | str | No | NM103 (Loop 2010BB) | |
| `payer_id` | str | No | NM109 | |
| `address` | Address | No | N3/N4 | |
| `plan_type` | enum(MEDICARE, MEDICAID, COMMERCIAL, BCBS, OTHER) | No | Derived | Used for payer-profile dispatch |

#### `ServiceFacility`
Optional location where service was rendered (Loop 2310E / 2310D).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `name` | str | No | NM103 | |
| `npi` | str | No | NM109 | |
| `address` | Address | No | N3/N4 | |

#### `Address` (value object)
| Field | Type | PHI | X12 Origin |
|---|---|---|---|
| `line1` | str | Partial | N301 |
| `line2` | str | Partial | N302 |
| `city` | str | No | N401 |
| `state` | str(2) | No | N402 |
| `zip` | str | No | N403 |
| `country_code` | str(3) | No | N404 |

**Relationships**
- `Claim` **1..1 → 1..1** `Submitter`
- `Claim` **1..1 → 1..1** `Receiver`
- `Claim` **1..1 → 1..1** `BillingProvider` (Provider with role=BILLING)
- `Claim` **1..1 → 0..1** `PayToProvider`
- `Claim` **1..1 → 1..1** `Subscriber`
- `Claim` **1..1 → 0..1** `Patient` (absent when subscriber IS patient)
- `Claim` **1..1 → 1..1** `Payer`
- `Claim` **1..1 → 0..1** `ServiceFacility`

---

### 4.3 Claim Cluster (outbound 837I/837P)

#### `Claim` (abstract base)
Concrete subclasses: `InstitutionalClaim` (837I), `ProfessionalClaim` (837P). Discriminated on `claim_type`.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `claim_type` | enum(INSTITUTIONAL, PROFESSIONAL) | No | — | Discriminator |
| `patient_control_number` | str | No | CLM01 | Provider-assigned claim ID; must be unique per submission |
| `total_charge_amount` | Decimal | No | CLM02 | Sum of service-line charges; validated |
| `facility_code` | str | No | CLM05-1 | POS (837P) or TOB first two digits (837I) |
| `claim_frequency_code` | str(1) | No | CLM05-3 | 1=original, 7=replacement, 8=void |
| `provider_signature_indicator` | enum(Y,N) | No | CLM06 | |
| `assignment_of_benefits` | enum(Y,N,W) | No | CLM07 | |
| `benefits_assignment_cert` | enum(Y,N) | No | CLM08 | |
| `release_of_info_code` | enum(Y,I,O) | No | CLM09 | |
| `statement_from_date` | date | No | DTP-434 | Required for 837I |
| `statement_to_date` | date | No | DTP-434 | Required for 837I |
| `onset_of_illness_date` | date | No | DTP-431 | 837P |
| `admission_date` | datetime | No | DTP-435 | 837I |
| `discharge_date` | date | No | DTP-096 | 837I |
| `diagnoses` | list[Diagnosis] | Yes | HI segments | 1..* |
| `service_lines` | list[ServiceLine] | Yes | Loop 2400 | 1..* |
| `supplemental_info` | list[ClaimSupplementalInfo] | Partial | PWK, K3, NTE, CRC, AMT, QTY | 0..* |
| `prior_authorization` | str | No | REF-G1 | |
| `referral_number` | str | No | REF-9F | |
| `payer_claim_control_number` | str | No | REF-F8 | Required when claim_frequency_code in (7,8) |

#### `InstitutionalClaim` (837I extension)
Adds fields required by the institutional implementation guide (005010X223A2).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `type_of_bill` | str(3) | No | CLM05-1 + frequency | Derived |
| `admission_type_code` | str(1) | No | CL101 | |
| `admission_source_code` | str(1) | No | CL102 | |
| `patient_status_code` | str(2) | No | CL103 | |
| `drg_code` | str | No | HI (DR qualifier) | Diagnosis-related group |
| `occurrence_codes` | list[OccurrenceCode] | No | HI (BH/BI/BG/BE) | |
| `value_codes` | list[ValueCode] | No | HI (BE) | |
| `condition_codes` | list[ConditionCode] | No | HI (BG) | |
| `occurrence_span_codes` | list[OccurrenceSpanCode] | No | HI (BI) | |
| `treatment_authorization_code` | str | No | REF-G1 | |

#### `ProfessionalClaim` (837P extension)
Adds fields required by the professional implementation guide (005010X222A1).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `place_of_service_code` | str(2) | No | CLM05-1 | POS code |
| `accident_related_causes` | list[AccidentCause] | No | CLM11 | |
| `related_causes_codes` | list[str] | No | CLM11 | |
| `auto_accident_state` | str(2) | No | CLM11-4 | |
| `special_program_code` | str(2) | No | CLM12 | |
| `delay_reason_code` | str(2) | No | CLM20 | |

#### `Diagnosis`
One diagnosis. Stored as an ordered list on the claim.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `code` | str | Yes | HI01-2 | ICD-10-CM code |
| `code_qualifier` | enum(ABK, ABF, APR, ABJ, BN, BF, BR, BQ, BJ) | No | HI01-1 | ABK=principal, ABF=other |
| `poa_indicator` | enum(Y,N,U,W,1) | No | HI01-9 | Present-on-admission (837I) |

#### `ServiceLine`
One service line (Loop 2400). Polymorphic between SV1 (professional), SV2 (institutional), SV3 (dental — not in scope).

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `line_number` | int | No | LX01 | 1-based ordinal |
| `service_type` | enum(SV1, SV2) | No | — | Discriminator |
| `procedure_code` | str | No | SV1/SV2-01 | HCPCS/CPT |
| `procedure_modifiers` | list[str] | No | SV1/SV2-01 sub-elements | Up to 4 |
| `charge_amount` | Decimal | No | SV1/SV2-02 | |
| `unit_basis` | enum(UN=unit, MJ=minutes, DA=days) | No | SV1/SV2-03 | |
| `unit_count` | Decimal | No | SV1/SV2-04 | |
| `place_of_service_override` | str(2) | No | SV1-05 | 837P only; overrides claim-level POS |
| `diagnosis_pointers` | list[int] | No | SV1-07 | 1-based pointers into `Claim.diagnoses` (837P) |
| `revenue_code` | str | No | SV2-01 | 837I only |
| `service_date` | date | No | DTP-472 | |
| `line_adjustments` | list[LineAdjustment] | No | AMT, CAS (rare on 837) | Usually only in 835 |
| `supplemental_info` | list[ServiceLineSupplementalInfo] | Partial | PWK, K3, NTE, MEA, CN1 | |

#### `ClaimSupplementalInfo` / `ServiceLineSupplementalInfo`
Open-ended bag for segments that are optional and payer-specific.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `segment_id` | str | No | — | PWK, K3, NTE, CRC, AMT, QTY, HCP, MEA, CN1 |
| `raw_elements` | list[str] | Partial | — | Preserved verbatim for round-trip fidelity |

**Relationships**
- `Claim` **1..1 → 1..\*** `ServiceLine`
- `Claim` **1..1 → 1..\*** `Diagnosis`
- `Claim` **1..1 → 0..\*** `ClaimSupplementalInfo`
- `ServiceLine` **1..1 → 0..\*** `ServiceLineSupplementalInfo`

---

### 4.4 Remittance Cluster (inbound 835)

#### `Remittance`
Top-level 835 transaction set body.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `transaction_handling_code` | enum(I=info, H=notification, C=credit, D=debit, P=paid) | No | BPR01 | |
| `total_paid_amount` | Decimal | No | BPR02 | |
| `credit_debit_flag` | enum(C,D) | No | BPR03 | |
| `payment_method` | enum(ACH, CHK, FWT, NON) | No | BPR04 | |
| `payment_format` | enum(CCP, CTX) | No | BPR05 | |
| `payment_date` | date | No | BPR16 | Effective entry date |
| `payment` | RemittancePayment | No | BPR | 1..1 |
| `payer` | Payer | No | N1-PR | |
| `payee` | Provider | No | N1-PE | |
| `claim_payments` | list[ClaimPayment] | Yes | Loop 2100 | 1..* |
| `provider_level_adjustments` | list[ProviderAdjustment] | No | PLB | 0..* |

#### `RemittancePayment`
The BPR header payment block.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `check_or_eft_trace_number` | str | No | TRN02 | |
| `payer_identifier` | str | No | TRN03 | |
| `origin_company_id` | str | No | TRN04 | |
| `depository_routing_number` | str | No | BPR06 | |
| `account_number` | str | No | BPR08 | |

#### `ClaimPayment`
One 2100-loop entry: the 835 adjudication for one claim.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `patient_control_number` | str | No | CLP01 | **Correlation key to outbound Claim** |
| `claim_status_code` | str | No | CLP02 | 1=primary paid, 4=denied, 22=reversal, ... |
| `total_charge_amount` | Decimal | No | CLP03 | |
| `total_paid_amount` | Decimal | No | CLP04 | |
| `patient_responsibility` | Decimal | No | CLP05 | |
| `claim_filing_indicator_code` | str | No | CLP06 | |
| `payer_claim_control_number` | str | No | CLP07 | ICN / DCN |
| `facility_code` | str | No | CLP08 | |
| `claim_frequency_code` | str | No | CLP09 | |
| `diagnosis_drg_code` | str | No | CLP11 | 837I reconciliation |
| `subscriber` | Subscriber | Yes | NM1-QC | |
| `corrected_subscriber` | Subscriber | Yes | NM1-74 | When payer corrects submitted info |
| `service_payments` | list[ServicePayment] | Yes | Loop 2110 | 0..* |
| `claim_adjustments` | list[Adjustment] | No | CAS (claim-level) | 0..* |
| `claim_supplemental_info` | list[AmountInfo] | No | AMT, QTY, MOA, MIA | 0..* |

#### `ServicePayment`
One 2110-loop entry: the 835 adjudication for one service line.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `procedure_code` | str | No | SVC01-2 | HCPCS/CPT |
| `procedure_modifiers` | list[str] | No | SVC01 sub-elements | |
| `charge_amount` | Decimal | No | SVC02 | |
| `paid_amount` | Decimal | No | SVC03 | |
| `revenue_code` | str | No | SVC04 | 837I tie |
| `paid_units` | Decimal | No | SVC05 | |
| `service_date` | date | No | DTM-472 | |
| `line_adjustments` | list[Adjustment] | No | CAS (line-level) | |
| `line_identifiers` | list[ReferenceIdentifier] | No | REF-6R, REF-LU | Line item control number; correlates to `ServiceLine.line_number` |
| `line_supplemental_info` | list[AmountInfo] | No | AMT, QTY, LQ, HCP | |

#### `Adjustment` (CAS)
| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `group_code` | enum(CO, CR, OA, PI, PR) | No | CAS01 | Contractual, Corrective, Other, Payer-initiated, Patient-responsibility |
| `reason_code` | str | No | CAS02 | CARC code |
| `amount` | Decimal | No | CAS03 | |
| `quantity` | Decimal | No | CAS04 | |
| `additional_reasons` | list[AdjustmentReason] | No | CAS05-CAS19 | Up to 5 additional triplets |

#### `ProviderAdjustment` (PLB)
Provider-level adjustments reported outside any specific claim.

| Field | Type | PHI | X12 Origin | Notes |
|---|---|---|---|---|
| `provider_id` | str | No | PLB01 | Usually NPI |
| `fiscal_period_date` | date | No | PLB02 | |
| `adjustment_identifier` | str | No | PLB03-1 | e.g., WO (Overpayment Recovery), L6 (Interest Owed) |
| `amount` | Decimal | No | PLB03-2 | |

**Relationships**
- `Remittance` **1..1 → 1..\*** `ClaimPayment`
- `Remittance` **1..1 → 0..\*** `ProviderAdjustment`
- `ClaimPayment` **1..1 → 0..\*** `ServicePayment`
- `ClaimPayment` **1..1 → 0..\*** `Adjustment` (claim-level)
- `ServicePayment` **1..1 → 0..\*** `Adjustment` (line-level)

#### Reconciliation projection (virtual, not persisted)

The library exposes a read-only projection object that joins `ClaimPayment.patient_control_number` back to the originating `Claim.patient_control_number`. This is in-memory only; see
[`x12_edi_tools.reconciliation.ReconciliationResult`](../packages/x12-edi-tools/src/x12_edi_tools/reconciliation/__init__.py)
once Phase 5 lands.

| Field | Type | Source |
|---|---|---|
| `claim` | Claim \| None | Caller-supplied claim corpus |
| `claim_payment` | ClaimPayment | Parsed 835 |
| `charge_variance` | Decimal | `claim.total_charge_amount - claim_payment.total_charge_amount` |
| `paid_ratio` | Decimal | `claim_payment.total_paid_amount / claim.total_charge_amount` |
| `line_matches` | list[LineMatch] | Heuristic join on line number / procedure + modifiers |
| `unmatched_claims` | list[Claim] | Outbound claims with no 835 response |
| `orphan_payments` | list[ClaimPayment] | 835 entries whose `patient_control_number` is unknown |

---

### 4.5 Config & Audit Cluster

#### `PayerProfile`
Per-payer customization of defaults and validation. Implemented as a Python Protocol;
concrete profiles live in `x12_edi_tools/payers/<payer>.py`.

| Field | Type | PHI | Notes |
|---|---|---|---|
| `name` | str | No | Canonical key (e.g., `medicare-national`) |
| `payer_id` | str | No | |
| `version` | str | No | Companion-guide revision |
| `defaults_270_271` | dict | No | Existing |
| `defaults_837i` | dict | No | **New in Phase 4** |
| `defaults_837p` | dict | No | **New in Phase 4** |
| `overrides_835` | dict | No | **New in Phase 5** |
| `rules` | list[ValidationRule] | No | Appended to engine |
| `element_max_lengths` | dict[str,int] | No | Optional stricter caps |

#### `CompanionGuide`
Data file describing a payer's companion guide; seed YAML/JSON loaded at profile construction time.

| Field | Type | Notes |
|---|---|---|
| `payer_name` | str | |
| `payer_id` | str | |
| `transactions` | list[enum] | Which transactions this guide applies to |
| `segment_requirements` | dict | Keyed by `(transaction, loop, segment)` |
| `element_requirements` | dict | Keyed by `(transaction, segment, element_id)` |
| `code_lists` | dict | e.g., allowed facility codes |

#### `ControlNumberState`
**Advisory** data contract only. The library does NOT persist state; downstream consumers
must implement their own store. Exposed so the contract is stable.

| Field | Type | Notes |
|---|---|---|
| `submitter_id` | str | |
| `receiver_id` | str | |
| `next_isa_control_number` | int | Caller-owned |
| `next_gs_control_number` | int | Caller-owned |
| `next_st_control_number` | int | Caller-owned |

#### `CorrelationEvent`
Structured log event emitted by builders/parsers for observability. Non-PHI only.

| Field | Type | PHI | Notes |
|---|---|---|---|
| `correlation_id` | str | No | Trace ID |
| `stage` | enum(build, validate, encode, parse, reconcile) | No | |
| `transaction_code` | str | No | |
| `duration_ms` | int | No | |
| `result` | enum(success, warning, error) | No | |
| `error_code` | str | No | Never raw message |

---

## 5. Cardinality Summary (Quick Reference)

| Parent | Child | Cardinality | Notes |
|---|---|---|---|
| Interchange | FunctionalGroup | 1..* | |
| FunctionalGroup | TransactionSet | 1..* | |
| TransactionSet | Claim | 1..* | When `transaction_set_code` = 837 |
| TransactionSet | Remittance | 1..1 | When `transaction_set_code` = 835 |
| Claim | Submitter | 1..1 | |
| Claim | Receiver | 1..1 | |
| Claim | Subscriber | 1..1 | |
| Claim | Patient | 0..1 | Absent when subscriber is patient |
| Claim | Payer | 1..1 | |
| Claim | Provider(BILLING) | 1..1 | |
| Claim | Provider(PAY_TO) | 0..1 | |
| Claim | Provider(RENDERING) | 0..* | 837P primarily |
| Claim | Provider(ATTENDING) | 0..1 | 837I primarily |
| Claim | Provider(OPERATING) | 0..1 | 837I |
| Claim | Provider(REFERRING) | 0..1 | |
| Claim | Diagnosis | 1..* | |
| Claim | ServiceLine | 1..* | |
| Claim | ClaimSupplementalInfo | 0..* | |
| ServiceLine | ServiceLineSupplementalInfo | 0..* | |
| Remittance | ClaimPayment | 1..* | |
| Remittance | ProviderAdjustment | 0..* | |
| ClaimPayment | ServicePayment | 0..* | |
| ClaimPayment | Adjustment | 0..* | |
| ServicePayment | Adjustment | 0..* | |

---

## 6. Code Set Reference Tables

These are closed-vocabulary enums the library validates against. They live as Python enums in `x12_edi_tools.codes.*`.

| Code Set | Enum | Scope | Source of Truth |
|---|---|---|---|
| CARC | `ClaimAdjustmentReasonCode` | 835 `CAS02` | WPC (X12.org), revised quarterly |
| RARC | `RemittanceAdviceRemarkCode` | 835 `LQ` | WPC, revised quarterly |
| Claim Status | `ClaimStatusCode` | 835 `CLP02` | X12 code list 65 |
| Claim Adjustment Group | `AdjustmentGroupCode` | 835 `CAS01` | X12 code list 20 |
| Place of Service | `PlaceOfServiceCode` | 837P `CLM05-1` | CMS POS code set |
| Type of Bill | `TypeOfBillCode` | 837I CLM05-1 | NUBC TOB list |
| Patient Relationship | `RelationshipCode` | 837 `SBR02` | X12 code list 1069 |
| Diagnosis Qualifier | `DiagnosisQualifier` | 837 `HI01-1` | X12 code list 1270 |
| Revenue Code | `RevenueCode` | 837I `SV201` | NUBC |

---

## 7. Extensibility Hooks (Future Transactions)

The ERD is explicitly shaped to accept additional transaction bodies without reshaping the
envelope or party clusters.

| Future Transaction | Body Entity (Proposed) | Cluster | Notes |
|---|---|---|---|
| 999 (Implementation Ack) | `FunctionalAcknowledgement` | Envelope-level | Acknowledges a GS/GE group |
| 277CA (Claims Ack) | `ClaimsAcknowledgement` | Claim | Parsed-only; correlates on `patient_control_number` |
| 276 (Claim Status Inquiry) | `ClaimStatusInquiry` | Claim | Outbound; subset of 837 parties |
| 277 (Claim Status Response) | `ClaimStatusResponse` | Claim | Inbound pair to 276 |
| 278 (Authorization Request/Response) | `AuthorizationRequest`, `AuthorizationResponse` | Claim | Distinct body; reuses Provider/Patient/Payer |

No envelope or party entity requires changes; only a new `TransactionSet.body` union member.

---

## 8. Open Questions for Review

1. **Claim adjudication reversals (CLP02=22).** Should the reconciliation projection expose
   reversals as paired `ClaimPayment` objects, or collapse them into a single `paid_net`
   delta? Recommendation: keep them paired; reversals are legally distinct events.
2. **Multi-interchange 835s.** Some payers send one GS group containing multiple ST/SE blocks
   for the same check. Should `Remittance` expose a sibling-aware `sibling_group_id`?
   Recommendation: yes, derived from `FunctionalGroup.group_control_number`.
3. **Line-level CAS on 837.** Rare but legal (on corrected claims). Should the builder emit
   them? Recommendation: support via `ServiceLine.line_adjustments`, default empty.
4. **PHI minimization in reconciliation output.** Should `ReconciliationResult` expose raw
   `Subscriber` or only a redacted fingerprint? Recommendation: expose the full `Claim`
   since caller already holds it, but never serialize it in logs.

---

## 9. Change Log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-04-17 | Initial draft; covers 837I/837P/835 domain + envelope + payer config. |
