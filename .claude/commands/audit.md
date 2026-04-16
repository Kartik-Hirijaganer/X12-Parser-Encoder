# /audit

Run a code quality and security audit across the codebase.

## Arguments

- `$ARGUMENTS` — optional: a file path, directory, or glob pattern to scope the audit. If omitted, audit the entire codebase.

## Instructions

1. **Determine scope**:
   - If `$ARGUMENTS` is provided, limit work to matching files/directories.
   - If omitted, audit all Python files under `packages/` and `apps/` and all TypeScript/TSX files under `apps/web/src/`.
   - Skip: `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`.

2. **Ensure tools are available**:
   - Check that `bandit` is installed. If not, install it: `pip install bandit`.
   - Verify `ruff`, `mypy` are available (should already be in the project).
   - Verify `tsc` and `npm` are available for frontend checks.

3. **Run Python audit** on scoped `.py` files:

   a. **Linting** — run ruff and report issues:
      ```bash
      ruff check <scope>
      ```

   b. **Type checking** — run mypy and report issues:
      ```bash
      mypy <scope>
      ```

   c. **Security scan** — run bandit and report findings:
      ```bash
      bandit -r <scope> -f json -ll
      ```
      - `-ll` reports medium and high severity only.
      - Pay special attention to:
        - Hardcoded secrets or passwords
        - SQL injection / command injection
        - Insecure deserialization
        - Use of `eval()`, `exec()`, `pickle.loads()`
        - Weak cryptography
        - Logging of sensitive data (especially relevant — this project handles healthcare EDI)

4. **Run TypeScript/React audit** on scoped `.ts`/`.tsx` files:

   a. **Type checking** — run tsc:
      ```bash
      cd apps/web && npx tsc --noEmit 2>&1; cd -
      ```

   b. **Linting** — run eslint if configured:
      ```bash
      cd apps/web && npx eslint src/ 2>&1; cd -
      ```

   c. **Dependency vulnerabilities** — run npm audit:
      ```bash
      cd apps/web && npm audit 2>&1; cd -
      ```

5. **Analyze results** and produce a report organized by severity:

   ### Report format

   **CRITICAL** — issues that must be fixed before merge:
   - Security vulnerabilities (bandit high-severity, npm audit critical/high)
   - Type errors that could cause runtime failures

   **WARNING** — issues that should be addressed soon:
   - Bandit medium-severity findings
   - Lint violations that affect correctness
   - npm audit moderate vulnerabilities

   **INFO** — suggestions for improvement:
   - Style/formatting lint issues
   - npm audit low vulnerabilities
   - Minor type annotation gaps

   For each finding, report:
   - File path and line number
   - Tool that flagged it
   - Description of the issue
   - Suggested fix (one-liner if possible)

6. **Summary** — at the end, provide:
   - Total issues by severity (critical / warning / info)
   - Top 3 most impactful issues to fix first
   - Whether the codebase is safe to merge in its current state (yes/no with reason)

7. **Do NOT auto-fix** — this command is read-only. Report findings only. The user will decide what to fix. If the user wants auto-fixing, they should use `ruff check --fix` or address issues manually.
