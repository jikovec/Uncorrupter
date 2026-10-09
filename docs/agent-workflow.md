# UNCorrupter workflow navigation

The canonical workflow system is [the repository toolkit](../.agent/README.md).
Read [AGENTS.md](../AGENTS.md) and the selected canonical skill before acting.
This compatibility entry point owns no separate execution or authorization rules.

- `inspect` → [investigate](../skills/investigate/SKILL.md).
- `implement` → [build](../skills/build/SKILL.md); known defects → [fix](../skills/fix/SKILL.md).
- `verify` → [verify](../skills/verify/SKILL.md).
- `prepare delivery` or `finish` → [push](../skills/push/SKILL.md), bounded by the task endpoint.
- Recovery-specific work → [uncorrupter-workflow](../skills/project/uncorrupter-workflow/SKILL.md).

[Commands](commands.md) and [testing](testing/VERIFICATION.md) remain the native
command references. [Provider migration](../.agent/workflows/provider-discovery.md)
explains the retired local deploy-as-push meaning and preserved local Spec Kit setup.
