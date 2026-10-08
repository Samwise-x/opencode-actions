# opencode-actions

Production handoff for a **single logical repository trajectory** executed by fresh, disposable OpenCode workers on GitHub Actions.

## The invariant

> OpenCode may produce candidate state. OpenCode does not decide that candidate state became canonical truth.

Git/GitHub state is the durable body. OpenCode is disposable execution. Models/providers are replaceable cognition. Deterministic CI qualifies candidate SHAs. Admission is a model-free compare-and-swap of the canonical ref.

No OpenCode session, local SQLite database, model context, background registry, or runner filesystem is required for recovery.

## What this repository contains

- Makefile + scripts/bootstrap.py: one idempotent repository bootstrap interface.
- action.yml: one bounded frontier worker: lease, reconstruct, execute, prevalidate, publish, evidence.
- seal/action.yml: trusted post-validation qualification and keyless Cosign signature.
- admit/action.yml: signed-evidence verification plus exact-SHA canonical CAS.
- scripts/trajectory.sh: global expiring single-writer lease on opencode/trajectory.
- scripts/select-frontier.py: deterministic GitHub Issue/PR frontier reconstruction.
- scripts/worker.sh: tokenless OpenCode execution and evidence export.
- scripts/publish.*: trusted candidate commit/ref/PR mutation after the model exits.
- scripts/admit.py: final ancestry, evidence, checks, protected-path and base-SHA revalidation.
- templates/: the three caller workflows, worker prompt, OpenCode config, runtime guard, and protected-path policy.
- schemas/: machine-readable trajectory, attempt-evidence, and qualification contracts.
- docs/: architecture, deployment, failure, and security contracts.

## Execution path

1. A scheduled/manual frontier workflow starts from canonical main.
2. The wrapper obtains a global lease with Git force-with-lease CAS.
3. It reconstructs the current trajectory from open opencode/issue-* PRs or the deterministic ready-for-agent issue frontier.
4. It fetches issue/PR context before model execution.
5. GitHub credentials are removed and GitHub command files are replaced with disposable decoys.
6. Strict CargoWall starts.
7. A fresh pinned OpenCode process runs for a bounded interval.
8. The model can modify candidate files but cannot become the GitHub mutation authority.
9. The wrapper checks HEAD, conflicts, protected paths, control-action integrity, and a lightweight deterministic command.
10. Trusted wrapper code reconstructs publication in a fresh Git repository outside the model worktree, commits and force-with-lease updates one persistent issue branch, then creates/updates one PR.
11. Candidate validation runs independently with Nix + Dagger, Zizmor, and Trivy.
12. A trusted seal job checks out the validated candidate's original canonical base, generates qualification evidence, and signs it with Cosign from the canonical Nix environment.
13. Admission verifies the Sigstore workflow identity, candidate SHA, PR head, original base SHA, required check runs, ancestry, and protected paths.
14. Canonical main advances only by a fast-forward force-with-lease update from the qualified base to the exact qualified candidate SHA.

If any identity or state changed, admission rejects and the next worker reconstructs from GitHub.

## OpenCode pin

The worker defaults to OpenCode v1.18.35.

Linux x64 asset SHA-256:

    c8f888b451f5494a18f858fffb0e0b68f4e4baa9c241761c5f206884f0fa640d

Linux arm64 asset SHA-256:

    f7f2ba59ee8aa94d388f9696575a32d20e71c2ee48def9f80fc693a60fec6c72

The upstream anomalyco/opencode/github@latest wrapper is intentionally not the production trust anchor. The repository uses the non-interactive OpenCode CLI directly and captures --format json events as evidence.

## Bootstrap

The public setup interface is one command:

    make

The bootstrap observes the target before mutating it, reuses existing AGENTS/CONTEXT/Nix/Dagger state, installs only missing playbook-owned files, validates through `dagger call validate`, and reconciles the GitHub label, variables, secrets, and canonical-branch ruleset. A repeated run with the same inputs is a semantic no-op.

From a separate `opencode-actions` checkout, point the same interface at a target with:

    make TARGET=/path/to/repository

A first greenfield run requires authenticated `gh`, Nix, an existing or supplied `OPENCODE_MODEL`, existing or supplied `OPENCODE_API_KEY` and `ADMISSION_TOKEN`, and the admission bypass actor ID. Existing secret values are never rewritten merely because `make` ran again.

No bootstrap state file exists. Repository and GitHub state are the bootstrap state.

## Target repository contract

The target repository must provide a canonical main, GitHub Issues with ready-for-agent, deterministic tests, flake.nix + flake.lock, and a Dagger module exposing:

    dagger call validate

The canonical Nix dev shell must provide Dagger and all project validation dependencies. Candidate validation executes `nix develop --no-write-lock-file --command dagger call validate`. Seal/admission obtain Cosign from an exact pinned nixpkgs revision, so candidate-controlled project flakes do not supply the signing/verifying binary.

The bootstrap installs the caller workflows, worker prompt, OpenCode policy/runtime guard, and protected-path policy from `templates/`. Existing brownfield Nix/Dagger/domain/agent state is preserved and must satisfy the same validation contract.

All Samwise-x/opencode-actions references in the handoff templates are pinned to the CI-validated implementation commit `caa4756ccd14ee820d4a0cb0b476889088ad8412`.

## Required GitHub configuration

Repository secrets:

- OPENCODE_API_KEY: example template uses OpenCode Zen. Replace provider secret/environment if another provider is selected.
- ADMISSION_TOKEN: dedicated GitHub App installation token or equivalent credential authorized to update the canonical branch and close the accepted issue. Do not expose it to worker or candidate-validation jobs.

Repository variables:

- OPENCODE_MODEL: for example opencode/gpt-5.6-sol.
- OPENCODE_ALLOWED_HOSTS: newline-separated CargoWall egress destinations required by the selected provider and any prevalidation command.

Canonical branch rules should reject direct ordinary writes and require the deterministic and security checks for ordinary PRs. The dedicated admission identity must be narrowly permitted to perform the final fast-forward update; worker credentials must not have that bypass.

## CargoWall posture

Probabilistic execution is fail-closed:

    mode: enforce
    offline: true
    fail-on-unsupported: true
    sudo-lockdown: true

Candidate Dagger validation runs in a separate read-only/no-secret job because CargoWall sudo lockdown deliberately removes Docker-group access. Qualification and admission are trusted jobs, execute no candidate code, and use strict CargoWall.

## State ownership

The coordination ref stores only a lease/version and last transition identifiers. It is not a cognitive handoff.

The actual handoff is reconstructable from:

    GitHub Issues + PRs + canonical Git history + candidate refs + exact-SHA CI + signed evidence

No STATUS.md, HANDOFF.md, agent diary, model summary, or persisted OpenCode session is needed.

## First deployment test

Before enabling the schedule, manually dispatch one issue and prove all of the following: the model sees no GitHub write credential; one persistent issue branch/PR is produced; failed checks block qualification; changing candidate HEAD invalidates old evidence; moving main invalidates old qualification; overlapping workers cannot both own the trajectory; protected control-plane changes are rejected; and final admission lands exactly the qualified SHA or does nothing.

See docs/DEPLOYMENT.md for the cutover sequence and docs/SECURITY.md for the trust boundary.
