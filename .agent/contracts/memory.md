# Persistent memory

> Memory is contextual state, not repository truth.

Memory never overrides current source, configuration, tests, schemas, manifests,
Git state, GitHub operational state, live/runtime evidence or accepted decisions.
Durable technical decisions belong in the repository first.

Load this contract with [scopes](scopes.md) only for memory, persistent context,
registry/identity, cross-project relationships or scope promotion work.
Determine the configured backend, readable scopes, relevant freshness and tool
permissions before reading. Reconcile mutable facts with authoritative sources.
When they conflict, current authoritative evidence wins; label memory stale or
contextual. Do not silently repair the memory record.

Access is not mutation authority. A write requires a writable destination scope,
explicit or valid standing authority, appropriate content and a supported persistence
mechanism. Respect provider-specific restrictions, including explicit-write-only
memory systems. No memory-write grant is created by this toolkit.

Memory can assist discovery, preserve user-approved durable context, and summarize
or point to accepted repository decisions and relationships. It cannot manufacture
identity, governance, action authority or current work state. Preserve canonical
references rather than copying full ADRs/issues/documents.

Do not automatically persist session observations, task hypotheses, temporary
failures or unverified interpretations. Do not write merely to record ordinary work.
Never store credentials, keys, tokens or unnecessary sensitive runtime data.

Preferred promotion order: accepted repository decision → committed/accepted
repository state → authorized memory pointer/summary. Promotion must satisfy the
scope contract and backend rules. If the backend is unavailable, report the blocked
binding/write; do not create a local substitute memory store or fabricate scope IDs.
`.mind-seed/`, if legitimately enabled, holds durable bindings, not mutable memories.
