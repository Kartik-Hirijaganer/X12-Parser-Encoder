# /bump-version

Bump the project version across all version-bearing files.

## Argument

$ARGUMENTS — must be one of: `major`, `minor`, `patch`, or an explicit semver like `1.2.3`.

## Instructions

1. **Read the current version** from the `VERSION` file at the repo root. If it doesn't exist, stop and explain that Phase 8 expects `VERSION` to exist.

2. **Calculate the new version** based on the argument:
   - `major`: increment the major component, reset minor and patch to 0 (e.g. `0.3.2` -> `1.0.0`)
   - `minor`: increment the minor component, reset patch to 0 (e.g. `0.3.2` -> `0.4.0`)
   - `patch`: increment the patch component (e.g. `0.3.2` -> `0.3.3`)
   - Explicit semver (e.g. `1.2.3`): use that version directly after validating it matches `X.Y.Z` format

3. **Run the repo script**:
   ```bash
   python scripts/bump_version.py <argument>
   ```
   This updates:
   - `VERSION`
   - `packages/x12-edi-tools/pyproject.toml`
   - `packages/x12-edi-tools/src/x12_edi_tools/__about__.py`
   - `apps/api/pyproject.toml`
   - `apps/web/package.json`
   - `apps/web/package-lock.json`
   - the README version table
   - `CHANGELOG.md`

4. **Verify version sync**:
   ```bash
   python scripts/check_version_sync.py
   ```

5. **Report what changed**: Print a summary showing:
   - Previous version -> New version
   - Each file that was updated

6. **Stage and commit**: Stage all modified files and create a commit with the message:
   ```
   chore: bump version to X.Y.Z
   ```

7. **Create an annotated git tag**:
   ```
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

8. **Do NOT push** — just confirm the commit and tag were created locally. Remind the user to push with `git push --follow-tags` when ready.
