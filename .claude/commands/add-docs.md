# /add-docs

Add missing documentation (docstrings, JSDoc) to functions and classes across the codebase following Google style standards.

## Arguments

- `$ARGUMENTS` — optional: a file path, directory, or glob pattern to scope the update. If omitted, scan the entire codebase.

## Instructions

1. **Determine scope**:
   - If `$ARGUMENTS` is provided, limit work to matching files.
   - If omitted, scan all Python files under `packages/` and `apps/` and all TypeScript/TSX files under `apps/web/src/`.
   - Skip: `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, test files (`test_*.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`).

2. **For each Python file** (`.py`):
   - Check every public module, class, function, and method for a docstring.
   - If missing, add a **Google-style docstring**:
     - First line: imperative summary ending with a period.
     - `Args:` section — one entry per parameter as `name: Description.`
     - `Returns:` section — describe the return value.
     - `Raises:` section — list exceptions the function explicitly raises.
     - `Yields:` instead of `Returns:` for generators.
   - If a docstring exists but is incomplete (missing Args, Returns, or Raises), fill in the missing sections.
   - Do NOT modify existing docstrings that are already complete and accurate.
   - Do NOT add docstrings to private helpers (`_name`) unless the logic is genuinely non-obvious.
   - Do NOT add docstrings to test files.
   - Ensure type hints exist on all public function signatures. Add them if missing.

   Example:
   ```python
   def parse_segment(raw: str, delimiter: str = "*") -> Segment:
       """Parse a raw X12 segment string into a Segment model.

       Args:
           raw: The raw segment string (e.g., "ISA*00*...").
           delimiter: Element separator character. Defaults to "*".

       Returns:
           A fully populated Segment instance.

       Raises:
           X12ParseError: If the segment ID is missing or unrecognized.
       """
   ```

3. **For each TypeScript/TSX file** (`.ts`, `.tsx`):
   - Check every exported function, class, component, interface, type alias, and enum for JSDoc.
   - If missing, add a **TSDoc comment**:
     - First line: imperative summary sentence.
     - `@param name - Description.` for each parameter.
     - `@returns Description.` for the return value.
     - `@throws {ErrorType} Description.` for thrown errors.
   - If JSDoc exists but is incomplete (missing `@param` or `@returns`), fill in the missing tags.
   - Do NOT modify existing JSDoc that is already complete and accurate.
   - Do NOT add JSDoc to test files.
   - Ensure exported function signatures have explicit parameter and return types. Add them if missing.
   - For React components, document both the component and its Props interface.

   Example:
   ```typescript
   /** Props for the SegmentViewer component. */
   interface SegmentViewerProps {
     /** The parsed X12 segment to display. */
     segment: Segment;
     /** Whether to highlight validation errors. */
     showErrors?: boolean;
   }

   /**
    * Display a single X12 segment with syntax highlighting.
    *
    * @param props - Component props.
    * @returns The rendered segment viewer element.
    */
   export function SegmentViewer({ segment, showErrors = false }: SegmentViewerProps): JSX.Element {
   ```

4. **Validation** — after all edits, run:
   ```bash
   make lint 2>/dev/null || ruff check --fix packages/ apps/ 2>/dev/null
   make typecheck 2>/dev/null || mypy packages/ 2>/dev/null
   ```
   Fix any issues your edits introduced.

5. **Report** — summarize:
   - How many files were scanned.
   - How many functions/classes had documentation added or updated.
   - Any files skipped and why.
   - Any lint/type errors encountered and fixed.
