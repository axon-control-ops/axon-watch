# Axon-Watch Product Spec

## Product Thesis

`Axon-Watch` is a new integrated local-first operator and coding environment.
It combines:

- Cursor-style agent workflow and agent dock ergonomics
- VS Code-style editor, explorer, and terminal geometry
- Axon-style control-plane truth, approvals, signals, and multi-workspace oversight

The goal is not to clone Cursor or VS Code literally. The goal is to create one
Axon-native product that feels familiar to power users while remaining its own
system.

## Core Promise

The product should feel:

- lighter than the current Axon monolith
- more durable for long-running monitoring and agent work
- more IDE-native for hands-on coding
- more trustworthy for approvals, signals, and run-state truth

## Primary Product Parts

### Control Plane

Owns:

- chat and composer
- agent run state
- approvals and guarded actions
- workspace routing and handoffs
- operator-facing summaries

### Axon-Watch

Owns:

- continuous monitoring
- signal normalization and correlation
- connector and runtime observation
- notification routing
- durable monitoring summaries

### Integrated IDE Shell

Owns:

- editor
- terminal
- explorer
- browser preview surfaces
- agent dock
- operator signal surfaces

## Primary User Journeys

### Operator Workflow

The user starts from overview, sees ranked signals, checks runtime state, and
approves or dispatches the next best action.

### Coding Workflow

The user works in an IDE-style layout with editor, terminal, and agent dock in
one shell without switching to a separate product.

### Watch Workflow

The system continues observing projects, connectors, and runtime health even if
the main control-plane process restarts.

### Remote Server Workflow

The same product can be moved onto a dedicated machine later without needing a
rewrite of the service boundaries or frontend contracts.

## Product Principles

1. One product, not three stitched products.
2. One run-state truth, not competing status systems.
3. One signal/inbox model, not scattered alerts.
4. One layout system with multiple modes, not multiple apps.
5. One source of truth for documentation and contracts.

## Non-Goals

- building a literal clone of Cursor
- building a literal clone of VS Code
- carrying over the current Axon codebase wholesale
- making prompt-driven ReAct the primary execution source of truth
- preserving legacy complexity just because it already exists

## Reuse Strategy

The current `axon-local` repo is a donor/reference codebase.

We may reuse:

- proven UX patterns
- route and DTO ideas
- operator workflows
- naming that still fits the new model

We should avoid wholesale reuse of:

- Alpine boot assumptions
- giant mixed-ownership modules
- scheduler-heavy in-process monitoring patterns
- legacy shell code that fights the new architecture

## Success Criteria

The product is on the right track when:

- the UI feels like one coherent IDE/control-plane shell
- the watcher is durable and independently supervised
- run-state and signal-state are explicit and trustworthy
- moving to a dedicated server later is operationally simple
- the codebase stays modular, typed, and easy to extend
