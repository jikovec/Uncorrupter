# Recovery change evidence

Use this process for changes to recovery behavior or claims, not toolkit-only edits.

1. Read the checkout's `pyproject.toml`, CLI, selected engine/handler, decoder path
   and directly related tests. Follow [source map](../../docs/SOURCE-MAP.md) and
   [connections](../../docs/CONNECTIONS.md); verify paths against current files.
   A dirty newer candidate is not the committed branch's capability surface.
2. Preserve source inputs; use generated/synthetic corrupt fixtures, isolated output
   and disposable SQLite/workspace paths. Prevent input/output overlap. Never upload
   real damaged files or identifying reports as review/CI evidence.
3. Trace detection/classification → candidate/goal execution → decoder validation →
   persisted output/provenance → report. A recognized extension or successful decoder
   is not proof of semantic fidelity, restored missing bytes or broad format support.
4. For changed behavior, reproduce the defect or specify the expected outcome and
   add focused fixture coverage. Consider source preservation, output containment,
   bounded resource use, failed/unavailable tools and evidence attribution where
   those boundaries are affected. Preserve existing architecture and scope.
5. Use [commands](../../docs/commands.md) and
   [verification](../../docs/testing/VERIFICATION.md). The tracked base declares
   Python >=3.11 and Pillow; pytest is configured but must be available separately.
   Do not assume an unmerged candidate's dev extra, capability command, tests or
   environment flags exist in this checkout.
6. Run focused tests and the applicable broader suite. Separate native/synthetic
   results from optional-tool-present results and disclose skipped tool paths.
   Record exact artifact identity and measured fidelity; do not infer corpus quality
   or security certification from unit tests.
7. Update affected behavior/command/security docs and the machine index. If generated
   capabilities exist in the target checkout, use their actual generation/drift gate.
   Record meaningful evidence in a dated handoff and use the selected skill's endpoint.
