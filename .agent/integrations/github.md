# GitHub

- Binding: `jikovec/Uncorrupter`, owner `jikovec`, organization unset.
- Canonical configuration: [project metadata](../project.yaml), current Git `origin`,
  live repository metadata/protections and any tracked `.github/` workflows.
- Read operations: branches, relevant Issues/PRs/Projects, exact-SHA checks, tags and
  release records. Use `git` and authenticated `gh`, or an equivalent existing connector.
- Mutation operations: scoped source/PR/work-state delivery under
  [authorization](../contracts/authorization.md). Release/settings/deployment effects
  are separate; inspect push/merge triggers before delivery.
- Credentials: existing user-managed Git credential helper or GitHub CLI/connector
  authentication. Do not read credential files, echo tokens or commit credentials.
- Failure: report unavailable access or missing scopes precisely; continue authorized
  local work. Do not install a connector or change account/settings to bypass a gate.

Remote operational state is fetched per task, not cached as stable project metadata.
No CI success or Project adoption is implied by the existence of this integration.
