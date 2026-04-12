# /bump-version

Bump the project version across all version-bearing files.

## Argument

$ARGUMENTS — must be one of: `major`, `minor`, `patch`, or an explicit semver like `1.2.3`.

## Instructions

1. **Read the current version** from the `VERSION` file at the repo root. If it doesn't exist, assume `0.0.0`.

2. **Calculate the new version** based on the argument:
   - `major`: increment the major component, reset minor and patch to 0 (e.g. `0.3.2` -> `1.0.0`)
   - `minor`: increment the minor component, reset patch to 0 (e.g. `0.3.2` -> `0.4.0`)
   - `patch`: increment the patch component (e.g. `0.3.2` -> `0.3.3`)
   - Explicit semver (e.g. `1.2.3`): use that version directly after validating it matches `X.Y.Z` format

3. **Update version in all of these files** (skip any that don't exist yet):
   - `VERSION` — write the bare version string (e.g. `0.2.0`), no trailing newline beyond one
   - `packages/x12-edi-tools/pyproject.toml` — update the `version = "..."` field under `[project]`
   - `packages/x12-edi-tools/src/x12_edi_tools/__about__.py` — update `__version__ = "..."`
   - `packages/x12-edi-tools/src/x12_edi_tools/__init__.py` — update `__version__` if it's defined there
   - `apps/api/pyproject.toml` — update the `version = "..."` field under `[project]` if present
   - Any other `pyproject.toml` or `package.json` in the repo that carries a project version

4. **Update CHANGELOG.md** (if it exists):
   - Find the `## [Unreleased]` section
   - Insert a new section `## [X.Y.Z] - YYYY-MM-DD` (today's date) between `[Unreleased]` and the previous version
   - Move all content under `[Unreleased]` into the new version section
   - Leave `[Unreleased]` empty with a blank line beneath it
   - Update the comparison links at the bottom if they exist

5. **Report what changed**: Print a summary showing:
   - Previous version -> New version
   - Each file that was updated
   - Each file that was skipped (not found)

6. **Stage and commit**: Stage all modified files and create a commit with the message:
   ```
   chore: bump version to X.Y.Z
   ```

7. **Create an annotated git tag**:
   ```
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

8. **Do NOT push** — just confirm the commit and tag were created locally. Remind the user to push with `git push --follow-tags` when ready.
