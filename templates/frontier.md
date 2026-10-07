Continue the single canonical repository trajectory.

Reconstruct state from the repository, GitHub Issues/PRs, CONTEXT.md, ADRs, tests, and current canonical HEAD. Select the highest-value unblocked next action that can be completed coherently in this bounded pass.

Execute the work. Use subagents only for bounded parallel research, testing, or adversarial review. Keep the primary trajectory singular.

Do not merge, force-push, alter the trajectory branch, weaken validation, bypass security controls, or create handoff/status journals. Do not ask interactive questions. Leave a coherent reviewable candidate in the worktree.

Failure is evidence, not truth. If the intended work cannot be completed safely, make no speculative state transition.
