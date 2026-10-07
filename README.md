# opencode-actions

Production handoff for a **single logical repository trajectory** executed by fresh, disposable OpenCode workers on GitHub Actions.

## The invariant

> OpenCode may produce candidate state. OpenCode does not decide that candidate state became canonical truth.

Git/GitHub state is the durable body. OpenCode is disposable execution. Models/providers are replaceable cognition. Deterministic CI qualifies candidate SHAs. Admission is a model-free compare-and-swap of the canonical ref.

No OpenCode session, local SQLite database, model context, background registry, or runner filesystem is required for recovery.

## What this repository contains

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
10. Trusted wrapper code commits and updates one persistent issue branch with force-with-lease, then creates/updates one PR.
11. Candidate validation runs independently with Nix + Dagger, Zizmor, and Trivy.
12. A trusted seal job checks out the validated candidate's original canonical base, generates qualification evidence, and signs it with Cosign from the canonical Nix environment.
13. Admission verifies the Sigstore workflow identity, candidate SHA, PR head, original base SHA, required check runs, ancestry, and protected paths.
14. Canonical main advances only by a fast-forward force-with-lease update from the qualified base to the exact qualified candidate SHA.

If any identity or state changed, admission rejects and the next worker reconstructs from GitHub.

## OpenCode pin

The worker defaults to OpenCode v1.18.35.

Linux x64 asset SHA-256:

    c8f888b451f5494a18f858fffb0e0b68f4e4baa9c241761c5f206884f0fa640d

The upstream anomalyco/opencode/github@latest wrapper is intentionally not the production trust anchor. The repository uses the non-interactive OpenCode CLI directly and captures --format json events as evidence.

## Target repository contract

The target repository must provide a canonical main, GitHub Issues with ready-for-agent, deterministic tests, flake.nix + flake.lock, and a Dagger module exposing:

    dagger call validate

The trusted canonical Nix dev shell must provide both dagger and cosign. Candidate validation executes nix develop --no-write-lock-file --command dagger call validate; seal/admission use the same canonical Nix environment for Cosign.

Copy:

- templates/frontier.yml -> .github/workflows/opencode-frontier.yml
- templates/candidate-validation.yml -> .github/workflows/opencode-candidate-validation.yml
- templates/admit.yml -> .github/workflows/opencode-admit.yml
- templates/frontier.md -> .github/opencode/frontier.md
- templates/opencode.json -> opencode.json
- templates/harden-runtime.js -> .opencode/plugins/harden-runtime.js
- templates/protected-paths.txt -> .opencode-actions/protected-paths.txt

All Samwise-x/opencode-actions references in the final handoff templates are pinned to immutable implementation commit 23a6bf960b4ad104a2a237d48e3ba1a15619f250.

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
