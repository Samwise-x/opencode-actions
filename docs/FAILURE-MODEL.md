# Failure model

The design fails closed around canonical state.

## Worker dies before publishing

Nothing canonical changed. The next attempt reconstructs from GitHub/Git.

## Worker publishes a candidate but evidence upload fails

The candidate remains non-canonical. Admission requires evidence and therefore rejects it.

## OpenCode exits non-zero

The attempt is failed. Diagnostic output may survive, but it is not qualified state.

## Deterministic validation fails

The candidate is not published by the composite action. No model message can override the validation exit code.

## Worker lease expires

A successor may acquire the trajectory. The expired worker can still possess a local worktree, but its later trajectory finalization fails CAS if the trajectory ref moved.

## Two workers race

The trajectory ref is updated with Git force-with-lease. Only the writer holding the expected ref version can advance it. GitHub Actions concurrency is useful as an outer optimization, not the authority.

## Canonical branch moves during work

Admission compares evidence base SHA to the current PR base ref. If canonical state moved, admission rejects and requires reconstruction/revalidation.

## Candidate branch moves after evidence

Admission requires the PR head SHA to equal the evidence candidate SHA. A moved branch invalidates the old evidence.

## Two admissions race

GitHub merge is submitted with the exact expected head SHA and branch protection remains authoritative. The second path sees moved canonical state or a closed/moved PR and fails.

## OpenCode local state disappears

Expected. Sessions, local SQLite, model context, MCP connections, and background registries are runtime state, not recovery state.

## Network or GitHub API fails

No success is inferred from partial execution. Retry begins by rereading canonical GitHub/Git state.

## Agent modifies governance files

That change is only a candidate until deterministic checks and admission accept it. Target repositories that prohibit agent-authored governance changes should protect those paths with CODEOWNERS/rulesets or validate their hashes in the repository-specific deterministic gate.
