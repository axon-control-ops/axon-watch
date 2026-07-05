# AXON-X Visual Direction — JARVIS-Forward Shell

## Status

Accepted planning direction for AXON-X presentation layer.

## North Star

AXON-X should feel like an **Iron Man JARVIS command console** that remains a
real IDE and operator control plane — not a movie prop and not a generic admin
dashboard.

Concept reference mockup (planning artifact, not shipped UI):

- `assets/axon-x-jarvis-console-mockup.png` in the Cursor project assets folder

The mockup preserves the current shell geometry:

- left explorer
- center workbench
- right dock
- bottom terminal
- topbar + status bar

The visual upgrade is the **presentation layer** on top of that geometry.

## Product Replacement Context

This shell is the **future primary UI** for AXON-X and will replace the current
Axon Alpine console in `axon-local` through strangler migration.

During transition:

- `axon-local` console remains live until parity slices verify
- AXON-X shell becomes primary only after explicit cutover gates

See [`TRANSITION_ARCHITECTURE.md`](TRANSITION_ARCHITECTURE.md).

## Visual Identity

### Personality

The shell should feel:

- cinematic but controlled
- premium and high-trust
- always-on and aware
- operator-grade under pressure
- code-capable when IDE mode is active

### What "JARVIS-forward" Means

JARVIS-forward means the **whole shell** uses a coherent HUD language:

- dark atmospheric base
- frosted glass panels
- cyan/electric accent edges
- HUD corner brackets on important seams
- subtle grid/hex atmosphere in the background
- KAIRO presence visible at all times
- motion on state changes, not ambient noise

JARVIS-forward does **not** mean:

- blocking the editor with a giant 3D orb
- unreadable neon on every surface
- fake telemetry widgets
- sacrificing approval/run truth for spectacle

## Best-In-Class Blend

| Source | Take | Reject |
|---|---|---|
| Iron Man / JARVIS HUD references | glass, glow, boot identity, voice-state feedback | full-screen hologram gimmicks |
| Cursor | agent dock ergonomics, run beside editor | looking like Cursor |
| VS Code | workbench tabs, terminal discipline | looking like VS Code |
| SOC / command centers | alert hierarchy, scan order | military cosplay |

AXON-X identity rule:

> Cursor/VS Code mechanics, JARVIS presentation, SOC hierarchy.

## Design Tokens

### Base Surfaces

| Token | Role | Suggested value |
|---|---|---|
| `--surface-shell` | app background | deep navy `#0a0e14` |
| `--surface-panel` | primary glass panel | `rgba(12, 20, 32, 0.72)` |
| `--surface-panel-elevated` | hero cards, KAIRO briefing | `rgba(14, 24, 38, 0.82)` |
| `--surface-inset` | editor/terminal inset | `rgba(6, 10, 16, 0.9)` |
| `--surface-grid` | background atmosphere | subtle hex/grid at 3–6% opacity |

### Glass And HUD Chrome

| Token | Role |
|---|---|
| `--glass-blur` | `blur(16px)` to `blur(24px)` on panels |
| `--border-glass` | `rgba(120, 200, 255, 0.14)` |
| `--border-hud` | `rgba(72, 196, 255, 0.42)` |
| `--glow-hud-soft` | cyan outer glow for active panels |
| `--glow-hud-strong` | stronger glow for interrupts only |
| `--hud-corner-size` | `12px` bracket arms on hero seams |

### Text

| Token | Role |
|---|---|
| `--text-primary` | main labels |
| `--text-secondary` | metadata |
| `--text-muted` | placeholders |
| `--text-hud` | cyan-tinted emphasis labels |

### Accent And Semantic

| Token | Role |
|---|---|
| `--accent-brand` | AXON-X / KAIRO cyan `#48c4ff` |
| `--accent-brand-soft` | chip backgrounds, hover states |
| `--state-info` | informational |
| `--state-warning` | approval / caution |
| `--state-high` | urgent attention |
| `--state-critical` | immediate action |
| `--state-success` | healthy / connected |
| `--state-degraded` | degraded but usable |

Semantic colors carry meaning. Cyan brand accent carries identity and KAIRO
presence. Do not use brand cyan for critical severity.

### Typography

| Use | Font direction |
|---|---|
| Product title, seam headers, KAIRO labels | display sans with slightly futuristic tone |
| Data, run IDs, terminal, editor | monospace |
| Body copy | neutral sans |

Avoid decorative sci-fi fonts in dense data areas.

### Motion

| Token | Duration | Use |
|---|---|---|
| `--motion-fast` | 120ms | hover/focus |
| `--motion-normal` | 180ms | panel expand/collapse |
| `--motion-emphasis` | 260ms | KAIRO state change, interrupt arrival |

`prefers-reduced-motion`: disable pulses/shimmers; keep static borders and icons.

## HUD Component Rules

### Glass Panel

Every major seam uses:

- blurred translucent background
- thin HUD border
- optional corner brackets when seam is hero
- inner padding sufficient for long-session reading

### Hero Seam

Only one hero seam at a time.

Hero seams get:

- elevated surface token
- `--border-hud`
- corner brackets
- slightly stronger glow

### KAIRO Chip

Topbar chip always visible.

States use glow intensity, not unrelated colors:

- `idle` — muted border
- `observing` — soft pulse
- `listening` / `speaking` — accent glow
- `alerting` — semantic high/critical edge
- `privacy_blocked` — muted, no animation

### Background Atmosphere

Use a **subtle** grid/hex layer behind the shell only.

Rules:

- never reduce text contrast
- never animate the full background in steady state
- disable or simplify under reduced motion

## Operator-Facing Copy Rules

Dev/skeleton labels must not ship in operator-facing surfaces.

| Dev/skeleton label | Operator-facing label |
|---|---|
| `CANONICAL SEAM` | `Workspace` / `Active Run` / `Signals` / etc. |
| `Awaiting WorkspaceRecord` | `No workspace selected` |
| `Awaiting ApprovalRecord` | `No pending approvals` |
| `Awaiting ThreadMessage` | `No active conversation` |
| `SHELL STATE` | `Loaded workspaces` |
| `Run seam` | `Active Run` |
| `Signals seam` | `Signals` |
| `Approvals seam` | `Approvals` |
| `Thread seam` | `Conversation` |
| `DTO tags in status bar` | hidden in production; dev-only behind `VITE_DEV_SEAMS=1` |

Copy may use KAIRO tone in briefing and spoken alerts, but numeric truth and
action eligibility must remain literal.

## Mode Presentation

### Operator Mode

Feels like the **JARVIS command deck**:

- KAIRO briefing card is the default visual hero
- approvals/signals promote above run when interruptive
- center workbench shows evidence, not primary status
- atmosphere slightly stronger than IDE mode

### IDE Mode

Feels like the **Stark workshop**:

- editor is visual hero
- KAIRO collapses to chip + compact briefing
- dock remains present but denser
- HUD chrome remains, but glow is reduced

## Boot / Wake Sequence

UX-0 must include a bounded boot sequence before the main shell is shown.

Sequence:

1. dark frame
2. AXON-X mark appears
3. short system line stack (`watch`, `control-plane`, `runtime`, `KAIRO`)
4. shell regions fade in
5. KAIRO chip settles to `observing` or `idle`

Rules:

- total sequence target `<= 2.5s` on standard dev hardware
- skip button available after `500ms`
- respect `prefers-reduced-motion` with immediate cut to shell
- boot is presentation only; must not delay real API bootstrap work

## Relationship To Current Screenshot

The current AXON-X operator console screenshot is the **functional skeleton**.

Missing relative to this visual direction:

- glass/HUD chrome
- KAIRO briefing hero treatment
- operator-facing labels
- cyan accent system
- boot/wake identity
- background atmosphere

The geometry is already correct. The next work is presentation, not layout
restructuring.

## Acceptance Criteria

This visual direction is being followed when:

- a new user can identify the product as a JARVIS-style command console within 5
  seconds
- the shell still supports long coding sessions in IDE mode
- KAIRO is visible without blocking workbench use
- dev seam labels are gone from operator-facing surfaces
- the concept mockup and implemented shell share the same region geometry
