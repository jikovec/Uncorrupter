# Format Handler Contract

## Registration

Each handler exposes one or more capability records with:

- stable family and variant identifiers
- extensions and signature rules
- supported operation levels
- required/optional tools
- default limits
- encryption and active-content policy
- output kinds and fidelity guarantees
- fixture evidence identifiers

## Operations

### detect

Consumes bounded byte-source windows and extension evidence. Returns independent signature, structure, extension, and ambiguity evidence.

### inspect

Parses bounded structure without publishing artifacts. Returns diagnostics, logical parts/members/streams, declared resource sizes, and risk flags.

### validate

Evaluates a source or artifact through one or more validators. Returns exact validation scope; success cannot imply untested fidelity.

### plan

Returns deterministic candidate plans for a requested goal. Each plan declares estimated resource costs and provenance.

### execute

Runs one plan through active budgets and cancellation. It may validate and publish zero or more artifacts through the shared atomic writer and returns artifact records plus diagnostics.

### publication boundary

The shared publisher validates containment/collision rules, consumes output/artifact budgets, hashes bytes, flushes a temporary sibling, and atomically publishes before the handler returns a published artifact.

## Required Invariants

- source paths and bytes are immutable
- reads, allocations, tool calls, extraction, and output are budgeted
- cancellation is checked at safe points
- candidate and artifact ordering is deterministic
- identical payload validation is shared without dropping strategy provenance
- unavailable dependencies and encrypted content are explicit outcomes
- previews and partial content cannot be promoted to full recovery
- all published artifacts carry source relations and validator evidence

## Compatibility Adapter

The existing JPEG engine may emit eager candidates through an adapter. The adapter must enforce materialization limits and convert its outputs into the same attempt and artifact evidence model.
