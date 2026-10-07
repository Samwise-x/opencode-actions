# opencode-actions

Production substrate for a single logical repository trajectory executed by disposable OpenCode workers.

## Invariant

OpenCode may produce candidate state. OpenCode does not decide that candidate state became canonical truth.

The durable system is Git/GitHub state plus SHA-bound evidence. Model context, OpenCode sessions, local SQLite state, background jobs, and runner filesystems are disposable.

## Production flow

1. A scheduled or manual frontier workflow enters on canonical HEAD.
2. A dedicated trajectory ref grants one expiring lease using Git force-with-lease compare-and-swap.
3. GitHub write credentials are removed before OpenCode executes.
4. A fresh OpenCode worker runs with a pinned, SHA-verified OpenCode binary.
5. A lightweight deterministic pre-publish gate runs.
6. Validated work is committed to an attempt branch and opened as a pull request.
7. Immutable execution evidence is uploaded and bound to base SHA, candidate SHA, model, agent, and validation result.
8. Candidate CI runs independently: Nix/Dagger for the canonical build/test graph, Zizmor for Actions security, and Trivy for filesystem/dependency findings.
9. Admission downloads the original frontier evidence, verifies the exact candidate SHA, rechecks the canonical base, verifies named checks, and asks GitHub to merge that exact PR head.
10. Protected-branch rules remain authoritative.

## Components

- `action.yml`: disposable frontier worker.
- `admit/action.yml`: model-free protected-PR admission.
- `scripts/trajectory.sh`: expiring single-writer trajectory ledger with CAS updates.
- `scripts/worker.sh`: OpenCode execution and deterministic pre-publish validation.
- `scripts/publish.sh`: candidate commit/ref creation.
- `scripts/publish.py`: PR creation without exposing GitHub credentials to the model.
- `scripts/admit.py`: exact-SHA evidence/check verification and protected PR merge.
- `schemas/`: trajectory and evidence contracts.
- `templates/`: production caller workflows and frontier prompt.
- `tests/`: deterministic state-machine tests.

## Pinned OpenCode

The worker defaults to OpenCode `1.18.35`, Linux x64 release asset SHA-256:

`c8f888b451f5494a18f858fffb0e0b68f4e4baa9c241761c5f206884f0fa640d`

The upstream `anomalyco/opencode/github@latest` wrapper is intentionally not the production trust anchor.

## Target repository installation

Copy the three workflow templates into `.github/workflows/` and `templates/frontier.md` into `.github/opencode/frontier.md`. Keep the action references pinned to an immutable commit SHA.

Create the `OPENCODE_API_KEY` Actions secret. The supplied frontier template targets OpenCode Zen with `opencode/gpt-5.6-sol`.

The target repository must provide:

- `flake.nix` / `flake.lock`.
- a Dagger module exposing `dagger call validate`.
- repository context and ADRs where applicable.
- deterministic tests.
- protected `main`.

## Required main-branch rules

Require pull requests. Require the `deterministic` and `security` checks. Require branches to be up to date before merging. Do not permit ordinary worker credentials to bypass the ruleset.

The admission workflow uses GitHub's protected PR merge path. A candidate whose base moved, whose head moved, whose evidence does not match, or whose required checks are not successful is rejected.

## Containment

The frontier template places CargoWall around the probabilistic OpenCode job with:

- `mode: enforce`
- `offline: true`
- `fail-on-unsupported: true`
- `sudo-lockdown: true`

The full Dagger graph runs in the separate deterministic candidate-validation job. This is deliberate: CargoWall sudo lockdown removes Docker-group access, while ordinary Dagger runner provisioning requires a container runtime.

## Recovery

A dead worker leaves canonical state untouched. An expired lease can be superseded. A stale worker cannot finalize a moved trajectory ref. A failed validation cannot publish a qualified candidate. A moved PR head invalidates old evidence. A moved canonical base forces reconstruction.

See `docs/FAILURE-MODEL.md` for the complete failure contract.
