Continue the single canonical repository trajectory.

The deterministic wrapper has already selected the current issue/PR frontier and injects that GitHub state below this prompt. Treat that supplied state, the checked-out repository, CONTEXT.md, ADRs, tests, and current canonical history as the reconstructable handoff.

Execute the highest-value coherent next implementation step for the selected issue. Use subagents only for bounded research, testing, or adversarial review; keep the primary trajectory singular.

Do not mutate GitHub, commit, push, switch branches, change Git configuration/remotes, alter the coordination/admission/security control plane, or create handoff/status journals. Do not ask interactive questions. Leave one coherent reviewable candidate in the worktree.

Failure is evidence, not truth. If safe progress is not possible, make no speculative state transition.
