# opencode-actions

Production handoff for deterministic rotating OpenCode workers on GitHub Actions.

This repository is a reusable substrate, not an application. It turns each model invocation into disposable cognition while Git/GitHub carries durable trajectory state, candidate commits, checks, pull requests, and evidence.

## Core rule

> OpenCode may mutate candidate state. OpenCode does not decide that candidate state became canonical truth.

## Execution path

```text
canonical GitHub/Git state
        |
        v
trajectory CAS lease
        |
        v
fresh OpenCode + fresh model context
        |
        v
candidate worktree mutation
        |
        v
deterministic repository validation
        |
        v
candidate commit + PR + SHA-bound evidence
        |
        v
model-free admission
        |
        v
protected canonical branch
```

The successor reconstructs from GitHub/Git. OpenCode sessions, model context, runner filesystems, local SQLite, and background registries are intentionally disposable.

## Handoff contents

`action.yml` is the reusable composite worker action. `scripts/trajectory.sh` implements the Git-backed expiring lease with force-with-lease CAS. `scripts/worker.sh` executes OpenCode and the deterministic validation command. `scripts/publish.sh` and `scripts/publish.py` publish the exact candidate and PR. `scripts/admit.py` is the model-free admission gate. The schemas define trajectory/evidence contracts. `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, and `docs/FAILURE-MODEL.md` define the operational contract.

## OpenCode boundary

The audited upstream implementation is OpenCode v1.18.35. This handoff does not use `anomalyco/opencode/github@latest` as a production trust anchor. OpenCode is installed as an explicitly versioned, SHA-256-verified release asset and invoked through the non-interactive `opencode run --format json` interface.

## What must be supplied by the target repository

The target repository supplies its objective/prompt, explicit `provider/model`, provider credential, deterministic validation command, canonical branch policy, and provider/build egress allowlist. Existing Nix and Dagger graphs should be called by the validation command rather than duplicated here.

## Deployment

Start with `docs/DEPLOYMENT.md`. The handoff intentionally does not enable a recurring schedule because a blank repository has no legitimate objective source, model credential, or application validation graph. Those are deployment inputs, not things this substrate should hallucinate into existence.
