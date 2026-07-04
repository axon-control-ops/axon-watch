# ADR-001: Use Vue 3, Pinia, Monaco, And xterm.js For The Console Shell

## Status

Accepted

## Context

Axon-Watch is an IDE-grade integrated application, not a light progressive-enhancement
shell. The console needs:

- multiple coordinated panels
- explicit shared state across boot, runtime summary, runs, inbox, and workbench surfaces
- editor and terminal hosts
- agent-dock and operator-dashboard behavior

The donor `axon-local` UI uses Alpine-style progressive enhancement. That approach
is useful for enhancement scenarios, but it is not the best long-term fit for this
class of application.

The `apps/console-web` package already boots with Vue 3 and Pinia, hosts Monaco
through `EditorHost`, and hosts xterm through `TerminalHost`.

## Decision

Use the following stack for `apps/console-web`:

- Vue 3 with TypeScript
- Pinia for shared shell state
- Monaco Editor for the workbench editor host
- xterm.js for the terminal host

Shared shell state and control-plane DTO consumption live in Pinia stores such as
`stores/shell.ts`. Editor and terminal integration live in bounded Vue components
and helper modules rather than inline HTML.

## Alternatives Considered

### Continue with Alpine-style progressive enhancement

Rejected because the product is an IDE-grade application with shared state,
multiple coordinated panels, and richer long-lived UI behavior.

### Use a different frontend stack such as React

Not chosen at this stage because Vue 3 + Pinia provides a strong component and
state model with a simpler path toward the planned shell structure and explicit
state contracts.

## Trade-Offs

- Gains stronger component boundaries and explicit state management
- Costs a fuller frontend toolchain and deliberate reimplementation effort
- Gains Monaco and xterm alignment with IDE-class UX
- Reduces direct reuse of the current Alpine-style UI implementation approach

## Consequences

### Positive

- component boundaries suited to a large integrated shell
- explicit shared state through Pinia stores
- stronger typing and contract reuse with shared DTO packages
- native-feeling editor and terminal building blocks already present in the repo

### Negative

- requires a fuller frontend toolchain than the donor UI approach
- reimplementation cost versus copy-pasting current UI logic from `axon-local`
- team discipline needed around shared stores and DTO boundaries

## Reevaluation Triggers

Reevaluate this ADR if:

- the chosen stack fails to support the integrated shell cleanly
- performance or developer-experience costs are consistently unacceptable
- another stack becomes materially better aligned with documented product needs
