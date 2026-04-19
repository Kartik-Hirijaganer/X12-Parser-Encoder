# Contributing

## Scope

This repository is built for X12 270/271 eligibility workflows. Contributions should preserve:

- No PHI in logs, fixtures, screenshots, or committed examples
- Synthetic fixtures only
- `VERSION` as the release source of truth
- Public API stability for `x12_edi_tools.parse`, `encode`, and `validate`

## Local Setup

```bash
make install
make lint
make typecheck
make test
make coverage
```

## Required Checks

Before opening a pull request:

1. Run `make lint`.
2. Run `make typecheck`.
3. Run `make test`.
4. Run `make coverage` for changes that affect critical paths.
5. Run `python scripts/check_version_sync.py` if you touched release metadata.

## Documentation Rules

- Update `README.md` and `docs/architecture.md` when public behavior changes.
- Update `docs/design-system.md` when visual rules, storage boundary, or workflow routing change, and `docs/ui-components.md` when primitive APIs change.
- Document tricky parser, encoder, and validator invariants close to the code.
- Avoid boilerplate comments on obvious control flow.

## Commit Style

Conventional commits are preferred:

- `feat(parser): add delimiter invariant coverage`
- `fix(api): propagate correlation id to validator`
- `docs(readme): clarify deployment boundary`

## Release Workflow

- Update versions with `python scripts/bump_version.py <major|minor|patch|X.Y.Z>`.
- Do not hand-edit scattered version strings.
- Keep changelog updates in `CHANGELOG.md`.

## Security and Data Handling

- Never commit real patient data.
- Never reintroduce `metadata/` to tracked files or release artifacts.
- Preserve the retention policy described in `SECURITY.md`.
