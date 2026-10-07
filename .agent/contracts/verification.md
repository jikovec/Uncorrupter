# Verification

Assign every relevant check exactly one status:

| Status | Meaning |
| --- | --- |
| passed | Executed against the identified state and met its criterion. |
| failed | Executed and did not meet its criterion. |
| blocked/unavailable | Could not run or obtain trustworthy evidence; name prerequisite. |
| intentionally bypassed | Eligible process gate deliberately skipped under publication authority. |
| not required | Does not apply to this change; state the reason where material. |

Choose proportional checks from [commands](../../docs/commands.md),
[testing](../../docs/testing/VERIFICATION.md) and actual configuration.
For toolkit-only edits run `python .agent/hooks/validate-toolkit/validate.py`,
validate `docs/agent-index.json`, inspect changed links and run `git diff --check`.
Use synthetic fixtures for runtime work; private damaged inputs are not CI fixtures.

Identify the checkout/commit/artifact and exact commands. Do not count unexecuted,
skipped, neutral or stale results as test passes. Check results on the exact pushed
head; a missing remote workflow is unavailable remote execution evidence, not success.
Distinguish applicable enforced merge requirements from checks not configured at all.

Repair task-caused defects and rerun affected checks. Do not weaken a test, suppress
a failure or change acceptance criteria to make it pass. Missing prerequisites do
not justify unrequested system installation or an unpinned substitute environment.
Keep local validation, remote checks, merged source, release artifacts, deployment
identity and observed live behavior as separate claims.
