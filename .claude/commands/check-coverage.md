# /check-coverage

Run the staged coverage gates for Python, web, or both and explain any drift.

## Argument

`$ARGUMENTS` must be one of `python`, `web`, or `all`.

## Instructions

1. Map the argument to commands:
   - `python`: `make coverage-lib` then `make coverage-api`
   - `web`: `make coverage-web`
   - `all`: `make coverage`
2. If a coverage run fails, inspect the uncovered lines and add or tighten tests in the affected critical path.
3. Do not lower thresholds to make the check pass.
4. If coverage artifacts were regenerated, update `docs/coverage-badge.svg` or note explicitly that the badge still needs regeneration.
5. Summarize:
   - which coverage gates ran
   - pass/fail outcome
   - files or flows that needed new tests
