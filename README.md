# opencode-actions

GitHub-native production substrate for one logical software trajectory inhabited sequentially by disposable OpenCode workers.

## Core invariant

OpenCode may produce candidate state. OpenCode never decides that candidate state became canonical truth.

Model context, OpenCode sessions, local SQLite state, background tasks, and runner filesystems are disposable. Durable continuity is reconstructed from Git/GitHub state, issue/PR state, immutable commits, trajectory coordination state, and exact-SHA evidence.

## Production protocol

1. A scheduled frontier run starts from canonical `main`.
2. `opencode/trajectory` grants one expiring lease using Git force-with-lease compare-and-swap.
3. The wrapper deterministically resumes the oldest open `opencode/issue-N` PR, otherwise selects the highest-priority oldest open issue labeled `ready-for-agent`.
4. The persistent issue branch is reconstructed against current canonical state before the model runs.
5. GitHub credentials are removed, GitHub Actions command files are replaced with decoys, the loaded action bytes are hashed, and CargoWall starts fail-closed.
6. A fresh SHA-verified OpenCode binary runs one bounded pass and leaves candidate changes in the worktree.
7. Deterministic policy rejects HEAD mutation, unresolved conflicts, protected-control-plane edits, or failed pre-publish checks.
8. Publication occurs from a fresh trusted Git repository in RUNNER_TEMP, never from model-controlled `.git` metadata.
9. The wrapper force-with-lease updates the persistent issue branch and creates/updates its PR.
10. Independent CI runs the repository's pinned Nix/Dagger validation graph plus Zizmor and Trivy.
11. A trusted seal job consumes immutable worker evidence and emits an exact-SHA qualification manifest signed keylessly with Cosign.
12. Admission verifies the Sigstore workflow identity, PR head, canonical base, named checks, ancestry, and protected paths, then performs one force-with-lease fast-forward of canonical state.

The final canonical ref CAS is the serialization point.

## Components

- `action.yml`: rotating frontier worker.
- `seal/action.yml`: trusted qualification/sealing action.
- `admit/action.yml`: model-free canonical admission.
- `scripts/trajectory.sh`: isolated cross-run ownership ledger with atomic CAS.
- `scripts/select-frontier.py`: deterministic GitHub issue/PR reconstruction.
- `scripts/worker.sh`: bounded credential-stripped OpenCode execution.
- `scripts/publish.sh` and `scripts/publish.py`: trusted candidate reconstruction, commit, ref, and PR mutation.
- `scripts/seal.py`: qualification manifest generation.
- `scripts/admit.py`: exact-SHA evidence/check/path verification and canonical CAS.
- `templates/`: ready-to-copy target-repository files pinned to an immutable implementation commit.
- `schemas/`: machine-readable trajectory, attempt, and qualification contracts.
- `tests/`: deterministic state-machine and policy tests.

## Pinned OpenCode

The worker intentionally does not use the floating `anomalyco/opencode/github@latest` wrapper as its production trust anchor.

Default OpenCode release: `v1.18.35`.

Linux x64 asset SHA-256:

`c8f888b451f5494a18f858fffb0e0b68f4e4baa9c241761c5f206884f0fa640d`

The runtime invokes `opencode run --format json`; the NDJSON stream is retained as attributable attempt evidence.

## Target-repository contract

A target repository supplies project semantics and validation: `AGENTS.md`, `CONTEXT.md`, ADRs where appropriate, a locked Nix environment, a Dagger module exposing `dagger call validate`, deterministic tests, and protected canonical state.

Install the files under `templates/`, configure model/provider access, and create a dedicated admission credential unavailable to the OpenCode worker. Exact deployment steps are in `docs/DEPLOYMENT.md`.

## Security boundary

OpenCode permissions are defense in depth, not the isolation boundary. The worker has no GitHub credential; CargoWall constrains egress; control-plane paths are denied by policy and rechecked deterministically; privileged Git work uses fresh isolated repositories and trusted scripts; canonical admission is model-free and CAS-protected.

See `docs/SECURITY.md` and `docs/FAILURE-MODEL.md`.

## Deliberately absent

No `STATUS.md`. No `HANDOFF.md`. No model-authored journal. No session persistence requirement. No second truth store.

Persist the trajectory, not the OpenCode process.
