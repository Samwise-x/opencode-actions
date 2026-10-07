# Architecture

## Ownership

| Concern | Owner |
| --- | --- |
| Work definition | GitHub Issues + repository context |
| Candidate cognition/execution | disposable OpenCode worker |
| Cross-run serialization | trajectory ref + force-with-lease CAS |
| Proposed implementation | persistent issue branch + PR |
| Correctness | deterministic Nix/Dagger + security checks |
| Qualification | signed exact-SHA manifest |
| Accepted state | canonical protected ref |
| Recovery | Git/GitHub canonical state |

## State machine

`idle -> leased -> validated -> admitted` is the successful path.

`leased -> failed` records failure without advancing canonical state. A lease expires automatically. A candidate awaiting required checks blocks redundant worker execution. A failed candidate remains on its persistent issue branch so the next fresh model can continue from Git state rather than session state.

The trajectory branch contains coordination state only. It never contains implementation code and never replaces Issues/PRs as work state.

## Frontier selection

The primary trajectory is singular. Existing open `opencode/issue-N` PRs are resumed before new work. Otherwise the selector chooses an open `ready-for-agent` issue ordered by P0/P1/P2/P3 priority and then age/issue number.

The persistent issue branch carries implementation continuity across model turnover. The model itself is disposable.

## Evidence chain

Worker evidence binds attempt, issue, base SHA, model/agent, OpenCode event stream digest, worktree diff digest, prevalidation result, candidate SHA, and PR.

Candidate CI independently evaluates the exact PR head. The trusted seal job consumes worker evidence and emits a qualification binding repository, base SHA, candidate SHA, issue, PR, attempt, required checks, and the frontier-evidence digest.

Cosign signs that qualification with GitHub OIDC. Admission accepts only a signature whose certificate identity corresponds to the target repository's configured validation workflow.

## Privileged mutation boundary

The probabilistic worktree is never trusted as a Git control plane after model execution. Candidate publication reconstructs a fresh Git repository under RUNNER_TEMP, overlays only worktree content while excluding `.git` and evidence internals, reruns protected-path checks, commits there, and pushes with force-with-lease.

Trajectory acquisition/finalization likewise uses an isolated temporary Git repository. Model-controlled local Git config, hooks, filters, remotes, and object metadata therefore do not become privileged execution inputs.

## Admission

Admission requires signed qualification, exact PR-head equality, exact canonical-base equality, successful named checks on the candidate SHA, descendant ancestry, no protected-path changes, and a dedicated admission credential.

The final write is:

`force-with-lease(canonical_ref, expected=base_sha, new=candidate_sha)`

If canonical state moved, the write fails and the system reconstructs from the new truth.

## Nix and Dagger

Nix fixes the project toolchain/environment. Dagger owns the portable validation graph. Candidate CI calls:

`nix develop --no-write-lock-file --command dagger call validate`

Project-specific checks belong inside that Dagger graph instead of being duplicated into orchestration.
