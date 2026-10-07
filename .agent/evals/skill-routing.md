# Skill routing evaluations

For each request below, select the workflow before reading implementation detail.
Positive examples should select the named skill. Counterexamples select the stated
neighbor or stop an impermissible effect. Test semantic decisions, not exact wording.
A project skill may accompany a baseline workflow for its domain. These examples
exercise triggers; policy remains in contracts and skills.

Record actual execution/evaluation evidence in a dated handoff, not in this routing
specification. Structural validation counts examples; it does not prove model routing.

## build

Canonical: [build](../../skills/build/SKILL.md).

### Positive examples

- Implement a new bounded JPEG diagnostic option.
- Add structured report output through normal repository delivery.
- Develop support for an explicitly specified CLI mode.

### Counterexamples

- Repair the known missing-EOI regression. → fix
- Explain how classification works without edits. → investigate

## investigate

Canonical: [investigate](../../skills/investigate/SKILL.md).

### Positive examples

- Explain why this checkout differs from main.
- Find the source of the candidate scoring value without changes.
- Inspect why the optional decoder is unavailable.

### Counterexamples

- Compare external PDF libraries using their documentation. → research
- Repair the confirmed timeout failure. → fix

## research

Canonical: [research](../../skills/research/SKILL.md).

### Positive examples

- Compare current qpdf repair interfaces from official documentation.
- Research container limits before choosing a parser.
- Find authoritative evidence for JPEG marker handling.

### Counterexamples

- Trace our scoring function using repository code. → investigate
- Implement the parser already specified. → build

## verify

Canonical: [verify](../../skills/verify/SKILL.md).

### Positive examples

- Verify the PR head actually passed its required checks.
- Check whether the claimed release artifact matches source.
- Independently test the claim that original bytes remain unchanged.

### Counterexamples

- Review this diff for regressions and maintainability. → review
- Repair the failed capability check. → fix

## review

Canonical: [review](../../skills/review/SKILL.md).

### Positive examples

- Review this decoder diff for regressions.
- Assess the PR for output containment and source preservation bugs.
- Review the toolkit contracts for contradictions.

### Counterexamples

- Confirm whether commit abc passed its configured checks. → verify
- Implement the accepted review correction. → fix

## fix

Canonical: [fix](../../skills/fix/SKILL.md).

### Positive examples

- Fix the confirmed source/output overlap defect.
- Repair the exact-head CI failure caused by this change.
- Reconcile stale command docs with the current CLI.

### Counterexamples

- Design and add a new recovery mode. → build
- Diagnose a suspected issue without editing. → investigate

## release

Canonical: [release](../../skills/release/SKILL.md).

### Positive examples

- Prepare the next authorized package release using the established process.
- Create the requested version tag and release record after validation.
- Reconcile release notes and verify the intended artifacts.

### Counterexamples

- Deliver completed documentation via commit and PR. → push
- Activate an existing release in the configured runtime. → deploy

## deploy

Canonical: [deploy](../../skills/deploy/SKILL.md).

### Positive examples

- Deploy this release to the explicitly configured runtime and check health.
- Roll out the intended artifact using the normal approved process.
- Deploy the specified state and verify its live version.

### Counterexamples

- Push my completed branch and open its PR. → push
- Force publication past an eligible internal process gate. → publish

## publish

Canonical: [publish](../../skills/publish/SKILL.md).

### Positive examples

- Force-publish the stated target past an explicitly eligible internal gate.
- Publish despite the optional internal deployment checklist, retaining platform protections.
- Assess and execute the minimum authorized force-publication path.

### Counterexamples

- Use administrator override to bypass a required GitHub check. → refuse bypass; fix or report blocked
- Deploy using every normal gate. → deploy

## push

Canonical: [push](../../skills/push/SKILL.md).

### Positive examples

- Finish the completed toolkit through commit, PR and merge.
- Commit and push only the reviewed task files, ending at push as requested.
- Complete the existing PR delivery after its checks pass.

### Counterexamples

- Create versioned package artifacts and a release tag. → release
- Update my local clean checkout from upstream. → pull

## pull

Canonical: [pull](../../skills/pull/SKILL.md).

### Positive examples

- Fast-forward my clean branch from its verified upstream.
- Synchronize this branch while preserving unrelated local changes.
- Integrate the latest main and resolve the task-owned conflicts.

### Counterexamples

- Explain why my branch differs without updating it. → investigate
- Send my finished local changes to GitHub. → push

## uncorrupter-workflow

Canonical: [uncorrupter-workflow](../../skills/project/uncorrupter-workflow/SKILL.md).

### Positive examples

- Validate this JPEG recovery fix with synthetic corrupted fixtures.
- Check that recovered output provenance matches the exact artifact.
- Assess optional-decoder failures without overstating recovery fidelity.

### Counterexamples

- Fix a broken adapter link in the agent toolkit. → fix
- Research external parser alternatives before deciding. → research
