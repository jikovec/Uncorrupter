# Recovery artifact ignore rules — 2026-10-15

Added directory rules for `input/`, `inputs/`, `single-input/`, `output/`,
`outputs/` and `.uncorrupter-workspace/` at any depth. These keep local recovery
inputs, derived outputs and run configuration artifacts out of ordinary Git staging.
Existing tracked files are unaffected; no recovery data was removed or committed.

Verification: `git check-ignore` covered each rule at the root and in nested paths;
negative controls covered source, tests, documentation and specification paths.
`git diff --check` passed. Recovery execution is not required for ignore-only changes.
