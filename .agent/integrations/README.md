# Integrations

[GitHub](github.md) is the repository's configured source/work-management service.
Python packaging and optional media tools are local runtime dependencies described
by `pyproject.toml` and existing development docs; they are not cloud integrations.

For an actual integration, record its canonical configuration, external service,
read versus mutation operations, required tooling/environment, project/organization
binding and credential source. Configuration does not establish current credentials,
connectivity or action authority. Never put tokens/secrets in these files or logs.

No Mind-Seed/MemPalace, Jira, Cloudflare, package registry or hosted deployment
binding is established here. Connector availability alone is not configuration.
Do not add placeholder integrations, credentials, accounts or background services.
