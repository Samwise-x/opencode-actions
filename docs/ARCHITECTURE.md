# Architecture

OpenCode owns cognition and candidate execution. GitHub owns durable refs, triggers, identities, pull requests, checks, and commit history. Repository policy owns trajectory continuity, evidence qualification, concurrency, and admission.

## Invariant

OpenCode may mutate candidate state. OpenCode does not decide that candidate state became canonical truth.

No OpenCode session, model context, background task registry, local SQLite database, or runner filesystem is required for recovery.

## Identity

Every attempt carries trajectory_id, trajectory_version, attempt_id, github_run_id, base_sha, candidate_sha, and the OpenCode session_id when available. The candidate SHA is the evidence join key.

## Worker lifecycle

Reconstruct canonical state; acquire single-writer ownership; start a fresh worker; execute bounded work; export evidence bound to the resulting SHA; validate deterministically; revalidate ownership and base; admit with compare-and-swap semantics; terminate.

## Concurrency and admission

GitHub Actions concurrency is the first overlap barrier. Admission is authoritative.

A candidate is admissible only when the expected canonical base is still current, required evidence names the exact candidate SHA, deterministic checks succeeded for that SHA, and the attempt still owns the expected trajectory version.

Any mismatch is a stale-worker rejection. Never force the write.

Conceptually:

    qualified(candidate_sha, evidence)
    AND canonical_head == expected_base_sha
    AND trajectory_version == expected_version
    THEN compare-and-swap canonical ref
    ELSE reject and reconstruct

The final ref update is the serialization point.

## Durable state

Derive state from GitHub and Git: CONTEXT.md for domain language; ADRs for irreversible decisions; Issues for work; commits for implementation; candidate refs or PRs for proposed transitions; deterministic checks for correctness; protected main for accepted state; signed digests for releases.

Do not create STATUS.md, HANDOFF.md, CURRENT_TASK.md, agent journals, or model summaries as competing truth.

## Security boundary

OpenCode permissions are tool policy, not host isolation. Runner/network containment and GitHub token permissions are separate enforcement layers. Use least-privilege GitHub permissions, immutable action SHAs, CargoWall enforcement, deterministic validation, and scoped/OIDC credentials where available.
