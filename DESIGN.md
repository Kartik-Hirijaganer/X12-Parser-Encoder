# Design System — Eligibility Workbench

> Inspired by **Meta (Store)** via [awesome-design-md](https://github.com/VoltAgent/awesome-design-md).
> Adapted for a healthcare eligibility workbench serving non-technical users doing bulk Medicaid 270/271 workflows.

---

## 1. Visual Theme & Atmosphere

The Eligibility Workbench is a task-driven healthcare tool — not a marketing site, not a dashboard for power users. The design is light-mode-first, rooted in Meta's retail-grade clarity: a generous white canvas where content, status, and actions are instantly legible. Every pixel serves the workflow. Non-technical users should feel confident, not overwhelmed.

The surface strategy is predominantly light — pure white for browsing and configuration, soft gray for secondary sections, and a controlled dark palette reserved exclusively for immersive data moments (raw X12 preview, code blocks). This is a tool people use once a week for 20 minutes; it must be self-evident every time they return.

The color system is built around a single action blue (`#0064E0` — Meta Blue) that drives all CTAs, links, and interactive focus. Eligibility status is communicated through a disciplined four-color semantic system: green for active/success, red for inactive/error, amber for warnings/corrections, and slate for not-found/unknown. These status colors appear only in badges, stat cards, and table cells — never in chrome or navigation.

Typography uses the system's native sans-serif stack (Inter as the preferred render, with system-ui fallbacks) paired with JetBrains Mono for X12 segment previews and technical labels. The type scale is compact — this is a tool, not an editorial experience. Headlines stay at 28-36px, body at 16px, and captions at 13-14px. Weight 500 (Medium) dominates headings; 400 (Regular) handles body; 600 (Semibold) marks emphasis in tables and stat cards.

Buttons are pill-shaped, fully rounded, and unmistakable. Cards have generous 16-20px radius. The overall impression is clean, approachable, and medical-grade trustworthy — the visual equivalent of a well-organized clinic reception desk.

**Key Characteristics:**
- Light-mode-first: white canvas (`#FFFFFF`) with soft gray sections (`#F1F4F7`)
- Single action blue (`#0064E0`) for all interactive elements — no competing accent colors
- Four-color eligibility status system: green/red/amber/slate
- Pill-shaped CTAs (100px radius) — the primary call to action is always obvious
- 8px spacing grid with 16px base rhythm
- Cards at 16-20px radius — smooth, approachable, never sharp
- System font stack with Inter preferred, JetBrains Mono for X12/code content
- WCAG AA contrast compliance on all text — non-negotiable for healthcare

---

## 2. Color Palette & Roles

### Primary Action

- **Action Blue** (`#0064E0`): Primary CTA background, active links, focus rings, selected states. The singular interactive color in the system.
- **Action Blue Hover** (`#0051B5`): Darkened blue for hover states on primary buttons.
- **Action Blue Pressed** (`#004BB9`): Deepest blue for active/pressed states.
- **Action Blue Light** (`#E8F3FF`): Subtle blue tint for info backgrounds, selected rows, active tab underlines.
- **Action Blue Text** (`#0064E0`): Link text color, breadcrumb active state.

### Surface & Background

- **White** (`#FFFFFF`): Primary page canvas, nav bar, card surfaces, modal backgrounds.
- **Soft Gray** (`#F1F4F7`): Secondary background sections (e.g., Templates page, alternating content blocks).
- **Warm Gray** (`#F7F8FA`): Flat card fill, table header background, input group backgrounds.
- **Web Wash** (`#F0F2F5`): Drop zone background, sidebar tinting, footer.
- **Near Black** (`#1C1E21`): Raw X12 preview background, code blocks only.
- **Overlay** (`rgba(0, 0, 0, 0.5)`): Modal/dialog backdrop.

### Text & Content

- **Primary Text** (`#1C2B33`): Main headings and body text. Not pure black — warmer and easier on the eyes.
- **Secondary Text** (`#5D6C7B`): Descriptions, help text, field labels, table secondary columns.
- **Tertiary Text** (`#65676B`): Placeholder text, timestamps, metadata.
- **Disabled Text** (`#BCC0C4`): Inactive labels, disabled button text.
- **Inverse Text** (`#FFFFFF`): Text on blue/dark backgrounds.

### Eligibility Status (semantic — used only in badges, stat cards, and table cells)

- **Active Green** (`#007D1E`): Active eligibility, valid, pass. Text on light backgrounds.
- **Active Green BG** (`#ECFDF3`): Background for green badges and stat cards.
- **Active Green Border** (`#A6F4C5`): Border for green containers.
- **Inactive Red** (`#C80A28`): Inactive eligibility, fail, critical error.
- **Inactive Red BG** (`#FEF2F2`): Background for red badges and stat cards.
- **Inactive Red Border** (`#FECACA`): Border for red containers.
- **Warning Amber** (`#B45309`): Auto-corrections applied, non-critical warnings, partial matches.
- **Warning Amber BG** (`#FFFBEB`): Background for amber badges and stat cards.
- **Warning Amber Border** (`#FDE68A`): Border for amber containers.
- **Not Found Slate** (`#475569`): Member not found, unknown status, no data.
- **Not Found Slate BG** (`#F1F5F9`): Background for slate badges and stat cards.
- **Not Found Slate Border** (`#CBD5E1`): Border for slate containers.

### Border & Divider

- **Border Default** (`#DEE3E9`): Standard borders — inputs, cards, table rows.
- **Border Subtle** (`#E5E7EB`): Lighter borders for minimal separation.
- **Border Strong** (`#909396`): Emphasis borders — active input focus stroke (behind the focus ring).
- **Divider** (`#CED0D4`): Horizontal rules, section separators.
- **Focus Ring** (`rgba(0, 100, 224, 0.4)`): 3px outer ring on focused interactive elements.

### Gradient & Overlay

- **Dark Code Gradient**: `linear-gradient(to bottom, #1C1E21, #111314)` — X12 raw preview backgrounds.
- **Drop Zone Gradient**: `linear-gradient(to bottom, #F7F8FA, #F0F2F5)` — drag-and-drop target area.

---

## 3. Typography Rules

### Font Family

**Primary:** Inter, with fallbacks: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif`

**Monospace:** JetBrains Mono, with fallbacks: `'SF Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace`

### Hierarchy

| Role | Size | Weight | Line Height | Letter Spacing | Use |
|------|------|--------|-------------|----------------|-----|
| Page Title | 36px (2.25rem) | 500 | 1.22 | -0.5px | Page-level headings: "Eligibility Results", "Settings" |
| Section Title | 28px (1.75rem) | 500 | 1.28 | -0.3px | Section headings: "Submitter / Provider Identity" |
| Card Title | 20px (1.25rem) | 600 | 1.40 | -0.1px | Action card headers: "Generate 270", stat card labels |
| Subtitle | 18px (1.125rem) | 400 | 1.44 | normal | Descriptive text under headings, intro copy |
| Body | 16px (1rem) | 400 | 1.50 | normal | Standard body text, form descriptions, table cells |
| Body Medium | 16px (1rem) | 500 | 1.50 | normal | Navigation links, emphasized body, field values |
| Label | 14px (0.875rem) | 500 | 1.43 | -0.1px | Form labels, table headers, button text |
| Caption | 13px (0.8125rem) | 400 | 1.38 | normal | Help text, timestamps, secondary metadata |
| Small | 12px (0.75rem) | 400 | 1.33 | normal | Footer text, version numbers, legal copy |
| Badge | 12px (0.75rem) | 600 | 1.00 | 0.2px | Status badges (uppercase): "ACTIVE", "FAIL", "PASS" |
| Stat Value | 32px (2rem) | 600 | 1.00 | -0.5px | Dashboard stat card numbers: "34", "8", "3" |
| Mono Body | 14px (0.875rem) | 400 | 1.57 | normal | X12 raw preview, segment content |
| Mono Caption | 12px (0.75rem) | 400 | 1.33 | normal | Segment IDs, technical labels, SNIP codes |

### Principles

- **500 for headings, 400 for reading, 600 for data emphasis**: A three-tier weight system. Headlines use medium weight for authority without heaviness. Body text stays at regular for comfortable reading. Stat numbers and table emphasis use semibold for at-a-glance scanning.
- **Negative tracking only at display sizes**: Letter-spacing tightens at 28px+ to keep headings compact. Below that, spacing stays normal for readability.
- **Uppercase only in badges**: Status badges ("ACTIVE", "INACTIVE", "PASS", "FAIL") use uppercase + weight 600 + 0.2px tracking. Nothing else is uppercased — this is a medical tool, not a marketing page.
- **Mono for X12 only**: JetBrains Mono appears exclusively in raw X12 previews, segment content, and technical labels (SNIP codes, segment IDs). Never use it for general UI text.

---

## 4. Component Stylings

### Buttons

**Primary (Pill)**
- Background: Action Blue (`#0064E0`)
- Text: White (`#FFFFFF`)
- Border: none
- Border radius: 100px (fully rounded pill)
- Padding: 10px 24px
- Font: 14px, weight 500, -0.1px tracking
- Hover: background darkens to `#0051B5`, subtle scale(1.02)
- Pressed: `#004BB9`, scale(0.98)
- Focus: 3px ring `rgba(0, 100, 224, 0.4)`, outline auto
- Transition: background 200ms ease, transform 150ms ease
- Use: Primary actions — "Process", "Download X12", "Save Changes", "Export Excel"

**Secondary (Outlined Pill)**
- Background: transparent
- Text: Primary Text (`#1C2B33`)
- Border: 2px solid `#DEE3E9`
- Border radius: 100px (fully rounded pill)
- Padding: 10px 24px
- Font: 14px, weight 500
- Hover: background `#F1F4F7`, border darkens to `#909396`
- Use: Secondary actions — "Cancel", "Upload Another", "Copy to Clipboard"

**Ghost Button**
- Background: transparent
- Text: Action Blue (`#0064E0`)
- Border: none
- Border radius: 8px
- Padding: 8px 16px
- Font: 14px, weight 500
- Hover: background `#E8F3FF`
- Use: Tertiary actions — "View Details", inline links, navigation

**Disabled (any variant)**
- Background: `#DEE3E9`
- Text: `#BCC0C4`
- Cursor: not-allowed, no hover effects
- Use: Settings gate blocking (e.g., "Generate 270" when config is incomplete)

### Cards & Containers

**Action Card (Home Page)**
- Background: White (`#FFFFFF`)
- Border: 1px solid `#DEE3E9`
- Border radius: 20px
- Padding: 24px
- Shadow: `0 2px 8px rgba(0, 0, 0, 0.06)`
- Hover: shadow intensifies to `0 8px 24px rgba(0, 0, 0, 0.10)`, translateY(-2px)
- Transition: transform 300ms ease, box-shadow 300ms ease
- Icon: 48px, Action Blue, top-aligned
- Title: 20px/600, Primary Text
- Description: 14px/400, Secondary Text, max 3 lines
- CTA: Ghost button or file input at bottom

**Stat Card (Eligibility Dashboard)**
- Background: status-specific BG color (green/red/amber/slate `*-BG` token)
- Border: 1px solid status-specific border color
- Border radius: 16px
- Padding: 20px
- Stat value: 32px/600, status-specific text color
- Stat label: 14px/500, Primary Text
- No shadow — color differentiation is sufficient

**Content Card (generic)**
- Background: White (`#FFFFFF`)
- Border: 1px solid `#DEE3E9`
- Border radius: 16px
- Padding: 20px
- Shadow: `0 1px 3px rgba(0, 0, 0, 0.04)`

### Inputs & Forms

- Background: White (`#FFFFFF`)
- Border: 1px solid `#DEE3E9`
- Border radius: 8px
- Padding: 10px 14px
- Font: 16px/400, Primary Text
- Placeholder: Tertiary Text (`#65676B`)
- Focus: border `#0064E0`, 3px outer ring `rgba(0, 100, 224, 0.25)`
- Error: border `#C80A28`, label color `#C80A28`, helper text in red below
- Disabled: background `#F7F8FA`, text `#BCC0C4`
- Label: 14px/500, positioned above the input with 4px gap
- Helper text: 13px/400, Secondary Text, 4px below input
- Select dropdowns: same styling, with a chevron-down icon right-aligned
- Transition: border-color 200ms ease, box-shadow 200ms ease

**NPI Validation Indicator (Settings)**
- Valid: green checkmark icon inline after the field, `#007D1E`
- Invalid: red X icon inline, `#C80A28`, with "Invalid NPI (Luhn check failed)" helper text

### Badges & Pills

**Status Badge**
- Background: status-specific BG color
- Text: status-specific text color
- Border radius: 100px (pill)
- Padding: 2px 10px
- Font: 12px/600, uppercase, 0.2px tracking
- Variants:
  - Active/Pass: green text on green BG
  - Inactive/Fail: red text on red BG
  - Warning: amber text on amber BG
  - Not Found: slate text on slate BG

**SNIP Level Badge (Validation Results)**
- Background: `#F1F4F7`
- Text: `#475569`
- Border: 1px solid `#DEE3E9`
- Border radius: 6px
- Padding: 2px 8px
- Font: 12px/500, monospace (JetBrains Mono)
- Content: "SNIP 1", "SNIP 2", etc.

### Tables

**Standard Table (Eligibility Dashboard, Validation Results)**
- Header background: `#F7F8FA`
- Header text: 13px/600, Primary Text, uppercase, 0.5px tracking
- Header border-bottom: 2px solid `#DEE3E9`
- Row background: White, alternating `#FAFBFC`
- Row border-bottom: 1px solid `#E5E7EB`
- Cell padding: 12px 16px
- Cell text: 14px/400, Primary Text
- Hover row: background `#F1F4F7`
- Selected row: background `#E8F3FF`, left border 3px solid `#0064E0`
- Expandable row icon: chevron-right, rotates 90deg on expand

### Navigation

- Background: White (`#FFFFFF`), sticky top
- Height: 56px
- Border-bottom: 1px solid `#DEE3E9`
- Logo/title: 18px/600, Primary Text, left-aligned
- Links: 14px/500, Secondary Text
- Active link: Action Blue, with 2px bottom border
- CTA (Settings): pill button or ghost button
- Mobile: hamburger collapse at 768px

### File Upload / Drop Zone

- Background: `#F7F8FA` with 2px dashed border `#DEE3E9`, border radius 16px
- Padding: 40px
- Icon: upload cloud, 48px, Secondary Text color
- Primary text: 16px/500, Primary Text — "Drag & drop any file here"
- Secondary text: 14px/400, Secondary Text — "or click to browse (.xlsx .csv .x12 .edi)"
- Hover/drag-over: background `#E8F3FF`, border solid `#0064E0`, border color blue
- Transition: background 200ms ease, border-color 200ms ease

### Config Status Bar (Home Page)

- Background: `#E8F3FF`
- Border: 1px solid `#B3D4FC`
- Border radius: 12px
- Padding: 10px 16px
- Text: 14px/500, `#1C2B33`
- Content: "Provider: ACME HOME HEALTH | NPI: 1234567890 | DC Medicaid"
- Clickable: entire bar navigates to Settings, cursor pointer
- Missing config variant: background `#FFFBEB`, border `#FDE68A`, with amber warning icon

### Raw X12 Preview (Generate Result)

- Background: Near Black (`#1C1E21`)
- Text: `#E2E8F0` (light gray on dark)
- Font: JetBrains Mono, 14px/1.57
- Border radius: 12px
- Padding: 20px
- Overflow: horizontal and vertical scroll
- Line numbers: `#64748B`, right-aligned, 48px gutter
- Max height: 400px with scroll

### Toast / Banner Notifications

**Auto-correction Banner (dismissible)**
- Background: `#FFFBEB`
- Border-left: 4px solid `#F59E0B`
- Border radius: 8px (right corners only)
- Padding: 12px 16px
- Icon: info circle, `#B45309`
- Text: 14px/400, Primary Text
- Dismiss: X button, right-aligned

**Error Banner**
- Background: `#FEF2F2`
- Border-left: 4px solid `#C80A28`
- Text: 14px/400, `#C80A28`

**Settings Gate Warning (on Home Page action card)**
- Inline within the disabled action card
- Text: 13px/400, `#B45309`
- Icon: lock or warning triangle, `#B45309`
- Content: "Configure your provider details in Settings first."

---

## 5. Layout Principles

### Spacing System

Base unit: 8px

| Token | Value | Use |
|-------|-------|-----|
| space-1 | 2px | Hairline gaps, badge internal |
| space-2 | 4px | Label-to-input gap, tight inline spacing |
| space-3 | 8px | Icon gaps, compact padding |
| space-4 | 12px | Input padding, cell padding, button icon spacing |
| space-5 | 16px | Standard paragraph spacing, card internal sections |
| space-6 | 20px | Card padding, stat card padding |
| space-7 | 24px | Grid gaps, section content padding, card padding (large) |
| space-8 | 32px | Major content block spacing |
| space-9 | 40px | Section vertical padding (compact), drop zone padding |
| space-10 | 48px | Section vertical padding (standard) |
| space-11 | 64px | Page-level vertical padding, hero spacing |
| space-12 | 80px | Maximum section separation |

### Grid & Container

- Max container width: 1200px, centered with auto margins
- Page horizontal padding: 24px (mobile), 32px (tablet), 40px (desktop)
- Home page: 3-column card grid on desktop, 24px gap
- Dashboard: full-width table with 16px cell padding
- Settings: single-column form, max-width 640px, centered
- Templates: 2-column card grid, 24px gap

### Whitespace Philosophy

This is a task-focused tool. Whitespace communicates hierarchy and breathing room, not luxury. Sections use 40-64px vertical padding — generous enough to feel uncluttered, compact enough to keep the workflow visible without scrolling. Action cards on the home page float in moderate negative space to feel approachable and tappable. The settings form is narrow (640px max) to keep field labels and inputs close together, reducing eye travel.

### Border Radius Scale

| Value | Use |
|-------|-----|
| 6px | SNIP badges, small tags |
| 8px | Inputs, ghost buttons, small containers |
| 12px | Config status bar, banners, X12 preview |
| 16px | Content cards, stat cards, drop zone |
| 20px | Action cards (home page) |
| 100px | Pill buttons, status badges (fully rounded) |

---

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat | No shadow, background color only | Default state, table rows, form sections |
| Level 1 | `0 1px 3px rgba(0, 0, 0, 0.04)` | Content cards, resting state |
| Level 2 | `0 2px 8px rgba(0, 0, 0, 0.06)` | Action cards (home), resting |
| Level 3 | `0 8px 24px rgba(0, 0, 0, 0.10)` | Action card hover, dropdown menus |
| Level 4 | `0 16px 40px rgba(0, 0, 0, 0.14)` | Modals, dialogs |
| Overlay | `rgba(0, 0, 0, 0.5)` full-screen | Modal backdrop |

The Eligibility Workbench uses a flat elevation model. Most differentiation comes from background color shifts (white to soft gray) and borders, not shadows. Shadows appear only on interactive cards (home page) and floating elements (modals, dropdowns). This keeps the interface feeling grounded and utilitarian — appropriate for a healthcare tool where trust matters more than visual flair.

---

## 7. Do's and Don'ts

### Do

- Use pill-shaped buttons (100px radius) for all primary and secondary CTAs
- Use Action Blue (`#0064E0`) exclusively for interactive elements — never decoratively
- Use the four-color status system consistently: green=active/pass, red=inactive/fail, amber=warning, slate=unknown
- Keep body copy brief and scannable — this is a task tool, not documentation
- Use generous whitespace (40-64px section padding) to keep the interface breathable
- Use uppercase only in status badges — nowhere else
- Always show form validation errors inline, immediately below the field
- Use JetBrains Mono exclusively for X12 content and technical labels
- Ensure all text meets WCAG AA contrast (4.5:1 for body, 3:1 for large text)
- Show the Config Status Bar on every page so the user always knows their context
- Use the disabled button state + inline warning for settings gate enforcement
- Maintain the 8px spacing grid — all spacing values should be multiples of 4 or 8

### Don't

- Don't use sharp corners (< 6px radius) — the system is all smooth curves
- Don't introduce additional accent colors beyond Action Blue — the status colors handle semantics
- Don't use shadows on flat content — shadows are reserved for interactive cards and floating elements
- Don't place critical actions in hard-to-find locations — the primary CTA should be visually dominant
- Don't use dark mode for any page except the X12 raw preview component
- Don't use decorative icons or illustrations — icons are functional only (upload, download, status, navigation)
- Don't use more than 2 levels of text hierarchy in a single card (title + description is the max)
- Don't make the user guess file routing — the drop zone auto-detects and the action cards have clear descriptions
- Don't show raw SNIP codes to users without plain-English explanations alongside
- Don't use toast notifications for important outcomes — use inline banners that persist until dismissed
- Don't crowd the settings form — one field per row, generous vertical spacing, clear group headers

---

## 8. Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <768px | Single column, hamburger nav, page title shrinks to 28px, cards stack vertically, 24px page padding |
| Tablet | 768-1024px | 2-column card grid (home), compact nav, settings form at full width with 32px padding |
| Desktop | 1024-1280px | 3-column card grid (home), full horizontal nav, settings form at 640px centered, 40px page padding |
| Large Desktop | >1280px | Max-width container (1200px) centered, increased margins |

### Touch Targets

- Minimum touch target: 44x44px (WCAG 2.1 AAA)
- Mobile button height: minimum 44px with 12px vertical padding
- Nav hamburger: 48x48px touch area
- Action cards: full card surface is tappable
- Table rows: full row surface is tappable for expand
- Drop zone: full area is tappable for file browser

### Collapsing Strategy

- **Navigation**: horizontal links collapse to hamburger at 768px; logo and Settings CTA remain visible
- **Action cards (Home)**: 3-column at 1024px+ → 2-column at 768px → stacked single column below 768px
- **Stat cards (Dashboard)**: 4-column at 1024px+ → 2x2 grid at 768px → horizontal scroll or 2x2 below 768px
- **Tables**: horizontal scroll with sticky first column below 768px; key columns (Name, Status) always visible
- **Settings form**: single column at all sizes; max-width 640px on desktop, full-width on mobile
- **Drop zone**: maintains full width, reduces vertical padding on mobile (40px → 24px)
- **Page titles**: 36px → 28px below 768px
- **Section padding**: 64px → 40px → 24px as viewport narrows

### Image Behavior

- No hero images — this is a tool, not a marketing site
- File type icons (Excel, X12, CSV): SVG, scale proportionally, maintain crispness at all sizes
- Status icons: inline SVG, 16-20px, color-matched to their semantic status

---

## 9. Agent Prompt Guide

### Quick Color Reference

- Primary CTA: Action Blue (`#0064E0`)
- Background: White (`#FFFFFF`)
- Secondary BG: Soft Gray (`#F1F4F7`)
- Heading text: Dark Charcoal (`#1C2B33`)
- Body text: Slate Gray (`#5D6C7B`)
- Muted text: Tertiary Gray (`#65676B`)
- Border: Divider Gray (`#DEE3E9`)
- Focus ring: `rgba(0, 100, 224, 0.4)`
- Active/Pass: `#007D1E` on `#ECFDF3`
- Inactive/Fail: `#C80A28` on `#FEF2F2`
- Warning: `#B45309` on `#FFFBEB`
- Not Found: `#475569` on `#F1F5F9`
- Code BG: Near Black (`#1C1E21`)

### Tailwind v4 Token Mapping

These design tokens map directly to `apps/web/src/styles/tokens.css` via `@theme`:

```css
@theme {
  /* Action */
  --color-action-500: #0064E0;
  --color-action-600: #0051B5;
  --color-action-700: #004BB9;
  --color-action-50: #E8F3FF;

  /* Surfaces */
  --color-surface-primary: #FFFFFF;
  --color-surface-secondary: #F1F4F7;
  --color-surface-tertiary: #F7F8FA;
  --color-surface-wash: #F0F2F5;
  --color-surface-dark: #1C1E21;

  /* Text */
  --color-text-primary: #1C2B33;
  --color-text-secondary: #5D6C7B;
  --color-text-tertiary: #65676B;
  --color-text-disabled: #BCC0C4;
  --color-text-inverse: #FFFFFF;

  /* Status: Active */
  --color-active-500: #007D1E;
  --color-active-50: #ECFDF3;
  --color-active-200: #A6F4C5;

  /* Status: Inactive */
  --color-inactive-500: #C80A28;
  --color-inactive-50: #FEF2F2;
  --color-inactive-200: #FECACA;

  /* Status: Warning */
  --color-warning-500: #B45309;
  --color-warning-50: #FFFBEB;
  --color-warning-200: #FDE68A;

  /* Status: Not Found */
  --color-notfound-500: #475569;
  --color-notfound-50: #F1F5F9;
  --color-notfound-200: #CBD5E1;

  /* Border */
  --color-border-default: #DEE3E9;
  --color-border-subtle: #E5E7EB;
  --color-border-strong: #909396;

  /* Fonts */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 20px;
  --radius-pill: 100px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.10);
  --shadow-xl: 0 16px 40px rgba(0, 0, 0, 0.14);

  /* Motion */
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

### Example Component Prompts

- "Create the Home Page with 3 action cards in a grid. Each card: white background, 1px `#DEE3E9` border, 20px radius, `0 2px 8px rgba(0,0,0,0.06)` shadow. 48px blue icon at top, 20px/600 title, 14px/400 slate description, ghost button at bottom. Cards hover with translateY(-2px) and shadow `0 8px 24px rgba(0,0,0,0.10)`. Below the cards, a dashed-border drop zone on `#F7F8FA`."

- "Create the Eligibility Dashboard with 4 stat cards in a row. Each card uses its status BG color, 16px radius, 20px padding. Stat number at 32px/600, label at 14px/500. Below, a data table with `#F7F8FA` header background, 13px/600 uppercase column headers, alternating white/`#FAFBFC` rows, status badges as colored pills."

- "Build the Settings page as a single-column form (max-width 640px centered). Group headers at 20px/600 with a subtle bottom border. Inputs: 8px radius, 1px `#DEE3E9` border, 16px font. Labels above at 14px/500 with 4px gap. Required fields marked with blue asterisk. Save button: primary blue pill, bottom-right aligned."

- "Create the raw X12 preview: `#1C1E21` background, 12px radius, 20px padding, max-height 400px with scroll. JetBrains Mono 14px, `#E2E8F0` text. Line numbers in `#64748B` in a 48px left gutter."

- "Build the Config Status Bar for the home page: `#E8F3FF` background, 1px `#B3D4FC` border, 12px radius, 10px 16px padding. Text at 14px/500 showing 'Provider: ACME HOME HEALTH | NPI: 1234567890 | DC Medicaid'. Full bar is clickable (cursor: pointer) to navigate to Settings."

### Iteration Guide

When refining screens built with this design system:
1. Always use Action Blue (`#0064E0`) for interactive elements — no other blue variants in the UI chrome
2. Status colors appear only in badges, stat cards, and table status cells — never in buttons, nav, or chrome
3. Three font weights: 400 (body), 500 (headings/labels), 600 (stat values/emphasis)
4. All spacing aligns to the 8px grid — if a value isn't a multiple of 4, question it
5. Pill buttons (100px radius) for CTAs, 8px radius for inputs and containers, 16-20px for cards
6. When in doubt about a component, refer to the Meta Store's retail clarity: simple, obvious, no visual noise
7. X12/code content always uses JetBrains Mono on a dark background — never mix code styling into the light UI
8. Every interactive element needs a visible focus state (3px blue ring) for keyboard accessibility
