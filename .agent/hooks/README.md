# Deterministic hooks

The toolkit validator is a manually invoked hook; it is not installed into Git,
a provider lifecycle, CI or system configuration.

| Property | Contract |
| --- | --- |
| Trigger | After toolkit/adapter/index edits and before scoped delivery |
| Purpose | Detect invalid identity/metadata, missing skills, adapter policy drift, broken links and missing routing examples |
| Inputs | Repository toolkit files, referenced local paths and machine index |
| Side effects | None from validation; regression tests use temporary directories only |
| Runtime | Python >=3.11 standard library; normally below one second on this tree |
| Exit | 0 valid; 1 validation failure; 2 invalid CLI usage |
| Failure | Report exact structural errors; no auto-fix, mutation or gate bypass |
| Manual invocation | `python .agent/hooks/validate-toolkit/validate.py` |
| Regression invocation | `python .agent/hooks/validate-toolkit/test_validate.py` |

[Validator](validate-toolkit/validate.py) and [regressions](validate-toolkit/test_validate.py)
use no third-party dependency. Metadata uses JSON notation (YAML 1.2); skill
frontmatter uses exactly `name` and `description` with JSON double-quoted strings,
also valid YAML scalars. A deliberate schema/identity/activation change must update
its validator alongside the accepted decision. It does not parse arbitrary YAML.

Routing coverage is structural, not a semantic model evaluation. The validator does
not decide architectural correctness, authorization, severity or task completion.
Those remain agent reasoning workflows. Add other hooks only for real deterministic
invariants, with the same trigger/input/effect/runtime/exit/failure contract.
