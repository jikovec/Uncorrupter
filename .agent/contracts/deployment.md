# Release, deployment and publication

Release creates release state (versions, notes, tags, archives or release records).
Deployment makes an intended state available in a configured runtime/distribution
target. Publication is an explicitly requested force path through eligible process
gates. Source push/PR/merge is a separate workflow, not a live deployment.

UNCorrupter is a local CLI. Discover current configuration before each task. The
tracked baseline has historical release archives and changelog material, but no
maintained hosted deployment pipeline, release automation or distribution target.
The portable skills remain available; they must report a missing concrete target or
procedure rather than inventing a service, registry, PyPI publication or Pages site.
Consult [commands](../../docs/commands.md), package metadata and actual workflows.

## Normal release/deploy

Confirm scoped action authority, intended immutable source/artifact, target and
normal process. Inspect version consistency, release notes, artifact provenance,
applicable tests, migrations, rollback and health/acceptance requirements where real.
Follow repository and provider gates. Verify exact resulting release/artifact identity
and observed live behavior separately. Never switch from deploy to publish implicitly.

## Force publication

An explicit publish request can cover bypassing repository-controlled or
deployment-process-controlled gates for its stated target. It cannot expand into
external-control bypass or unrelated settings changes.

1. Identify the actual normal-deployment blocker and source of enforcement.
2. Classify each gate: repository/process controlled, externally enforced, or unknown.
3. Only bypass an eligible internal gate when the scoped publication authority covers
   it; unknown gates are unresolved. Use the minimum force path supported by the real
   deployment process. Do not invent an unsafe shell path when none exists.
4. Preserve external GitHub branch protection/rulesets, required checks/reviews,
   protected environment approvals, organization governance, hosting protections,
   IAM and cloud policy. Do not disable, reconfigure, impersonate or use administrator
   overrides to circumvent them. A repository-authored check required by external
   protection is externally enforced for this decision.
5. Keep failed and intentionally bypassed results truthful. Record the gate, reason,
   authority and risk; publication success does not turn a failed check green.
6. Verify resulting live identity and acceptance using the target's real procedure;
   if blocked, report partial effects and exact unmet requirement.

Source-input safety, secrets/privacy boundaries and unrelated-work preservation are
not optional deployment gates. A request to publish does not waive them.
