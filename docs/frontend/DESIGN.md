# Sentinel Risk Engine — Design DNA & Visual System

---

## 1. STITCH PROJECT IDENTITY
- **Project Title**: Sentinel Risk Engine
- **Project Resource**: `projects/11308574227067643177`
- **Art Direction**: Institutional Fintech & Editorial Precision
- **Primary Viewport**: `max-w-5xl` centered instrument container

---

## 2. VISUAL DIRECTION & NORTH STAR
Sentinel Risk Engine visually expresses institutional financial authority through quiet restraint, crisp monospace data alignment, and decisive risk communication—hiding machine-learning complexity behind a single focused screening instrument.

---

## 3. COLOR SYSTEM (SEMANTIC TOKENS)

| Token Name | Token Role | Value / Class |
| :--- | :--- | :--- |
| `color-canvas-bg` | Page Background | `slate-50` (`#f8fafc`) |
| `color-surface-card` | Primary Container Surface | `white` (`#ffffff`) |
| `color-surface-subtle` | Sub-panel Tint | `slate-50/50` |
| `color-border-subtle` | Fine 1px Border | `slate-200` (`#e2e8f0`) |
| `color-border-focus` | Focus Ring Outline | `slate-800` (`#1e293b`) |
| `color-text-primary` | Primary Body & Headings | `slate-900` (`#0f172a`) |
| `color-text-secondary` | Subtitles & Field Labels | `slate-600` (`#475569`) |
| `color-text-muted` | Captions & Placeholders | `slate-400` (`#94a3b8`) |
| `color-brand-primary` | Primary CTA Button | `slate-900` (`#0f172a`) |

---

## 4. LOCALIZED RISK STATE PALETTE

Risk severity is localized exclusively to decision badges, percentage displays, and action cards:

| Backend `decision` | Badge Label | Badge Color Tint | Action Card Title | Color Accent |
| :--- | :--- | :--- | :--- | :--- |
| `APPROVED_LEGITIMATE` | **LEGITIMATE** | `bg-emerald-50 text-emerald-700 border-emerald-200` | Safe to Process | Forest Green |
| `APPROVED_WITH_MONITORING` | **MONITORING** | `bg-amber-50 text-amber-700 border-amber-200` | Process with Automated Monitoring | Warm Amber |
| `FLAGGED_FRAUD` | **FLAGGED FRAUD** | `bg-red-50 text-red-700 border-red-200` | Hold for Manual Review | Coral Red |
| `FLAGGED_CRITICAL_FRAUD` | **CRITICAL FRAUD** | `bg-rose-100 text-rose-900 border-rose-300` | Decline Transaction Immediately | Maroon Red |

---

## 5. TYPOGRAPHY SYSTEM
- **Sans-Serif Font Family**: `Inter, system-ui, sans-serif` (Headings, body text, form field labels, action badges).
- **Monospace Font Family**: `JetBrains Mono, monospace` (`transaction_id`, timestamps, account keys, bank IDs, monetary amounts, probability figures).

### Relative Type Scale
- **P0 Probability Score**: `text-4xl font-extrabold tracking-tight font-mono`
- **Risk Badge**: `text-xs font-semibold uppercase tracking-wide rounded-full`
- **Section Headings**: `text-xs font-bold uppercase tracking-wider text-slate-700`
- **Form Field Labels**: `text-xs font-semibold text-slate-700`
- **Input Text**: `text-xs font-mono font-medium text-slate-900`
- **Body & Captions**: `text-xs text-slate-500`

---

## 6. SPACING, ELEVATION & GEOMETRY
- **Page Canvas Margins**: `mx-auto max-w-5xl px-4 py-8 sm:px-6`
- **Form Group Spacing**: `space-y-6`
- **Grid Layout**: 2-column or 3-column structured form grid (`gap-4`)
- **Panel Padding**: `p-6` (Main containers) / `p-4` (Sub-cards)
- **Borders**: Uniform 1px solid borders (`border border-slate-200`)
- **Corner Radii**:
  - Form Controls: `rounded-md` (6px)
  - Result & Form Panels: `rounded-xl` (12px)
  - Status Badges: `rounded-full` (Pill format)

---

## 7. PROHIBITED PATTERNS (ANTI-DASHBOARD AUDIT)
- ❌ NO sidebar navigation
- ❌ NO KPI summary cards ("Total Volume", "Approval Rate")
- ❌ NO trend charts, sparklines, or time-series plots
- ❌ NO neon green/red cyberpunk hacker aesthetics
- ❌ NO glassmorphism or backdrop-blur translucent cards
- ❌ NO fake hardcoded production values
- ❌ NO client-side exposed 61-feature vectors
