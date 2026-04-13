# x12-edi-tools

`x12-edi-tools` is the installable Python package in this monorepo. It provides:

- typed models for X12 270 and 271 envelopes
- delimiter-aware parsing with transaction-scoped recovery
- roundtrip-safe encoding
- SNIP 1 through 5 validation plus payer-profile rules

## Install

```bash
pip install x12-edi-tools
```

## Public API

```python
from x12_edi_tools import encode, parse, validate
```

- `parse(raw_x12, strict=True, on_error="raise", correlation_id=None)` returns `ParseResult`
- `encode(interchange, delimiters=None, config=None, correlation_id=None)` returns X12 text
- `validate(interchange, levels=None, profile=None, custom_rules=None, correlation_id=None)` returns `ValidationResult`

See the repo root `README.md` and `docs/architecture.md` for system-level context.
