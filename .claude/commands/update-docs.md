# /update-docs

Refresh the public documentation so it matches shipped behavior.

## Instructions

1. Review the public surface first:
   - `README.md`
   - `docs/architecture.md`
   - `docs/design-system.md`
   - `docs/ui-components.md`
   - `packages/x12-edi-tools/README.md`
   - template docs under `apps/api/templates/`
2. Compare docs to the actual implementation in:
   - `packages/x12-edi-tools/src/x12_edi_tools/`
   - `apps/api/app/`
   - `apps/web/src/`
3. Update only the user-facing docs that drifted.
4. Preserve the documentation standards from Phase 8:
   - concise Google-style docstrings for public Python API only
   - system-level explanation in `README.md` and `docs/architecture.md`
   - no blanket docstring churn on private helpers or straightforward tests
5. Run the relevant checks after edits:
   ```bash
   make lint
   make typecheck
   ```
6. Summarize the docs that changed and any drift you found.
