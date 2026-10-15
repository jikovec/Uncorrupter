# CLI Contract

## Commands

### capabilities

Print registered/runtime-resolved format operations, limits, tool availability, fidelity, and fixture evidence in `text`, `json`, or `markdown`.

### scan

Inventory sources and detect bounded signatures. It does not classify or recover.

### classify

Run scan plus independent extension/signature/structure classification. It does not publish recovered artifacts.

### recover

Execute only explicitly requested goals and publish bounded artifacts. Resume is selected with `--resume RUN_ID`; it creates a linked new run rather than mutating the prior run.

### benchmark

Execute recovery and include quality/resource metrics in the final manifest.

### report

Export a selected persisted run without reopening source files.

## Common Safety Options

- source/scanned/materialized/candidate byte and count limits
- tool seconds and captured output bytes
- decompressed bytes, archive member size/count, nesting, and ratio
- artifact count and output bytes
- worker count
- cancellation marker path
- completion limit
- risky-layout explicit opt-in
- report/event path redaction

## Recovery Options

- repeatable `--goal repair|normalize|extract|preview|carve`
- `--save-raw-candidates`
- `--resume RUN_ID`
- `--changed-input-policy abort|reprocess|skip`
- `--exit-policy strict|partial-ok|report-only`
- JSON manifest, CSV, text, and JSONL event destinations
- required tool isolation and wrapper argument vector

Existing output destinations are preserved by the product CLI. Lower-level publisher collision policies are an internal API and are not exposed as a general recovery overwrite switch.

## Exit Codes

- `0`: requested work succeeded under the selected exit policy
- `1`: partial/adverse result under the selected exit policy
- `2`: fatal/cancelled/configuration/layout/capability failure
- `3`: no file results, except report-only policy treats this as success

Fatal conditions remain nonzero under every policy.

## Output Channels

- stderr: human progress unless `--quiet`
- stdout: final JSON summary
- JSONL file: monotonically sequenced machine events when configured/defaulted
- manifest/CSV/text files: durable no-clobber final reports

## Machine Events

Each JSONL record contains schema version, monotonically increasing sequence, UTC timestamp, event type, and structured payload. Events cover run/file lifecycle, candidates, tools, budgets, artifacts, goals, and final state.

## Compatibility

The historic `scan`, `classify`, `recover`, `benchmark`, and `report` names remain. Safety changes are explicit: scan no longer classifies, recover defaults to only repair, outputs no longer overwrite, and partial/fatal/no-result outcomes have meaningful exit codes.
