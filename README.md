# opencode-actions

Production GitHub substrate for continuously progressing repositories executed by disposable OpenCode workers.

## Contract

The repository trajectory persists. Individual model sessions, OpenCode processes, and runners do not.

OpenCode owns cognition and candidate execution. GitHub owns durable refs, pull requests, workflow identity, artifacts, and protected branch state. Deterministic repository machinery owns validation and final admission.

A model may produce candidate state. A model never decides that candidate state became canonical truth.

## What ships here

- `action.yml` — one bounded frontier pass with a Git-backed CAS lease.
- `admit/action.yml` — model-free exact-SHA pull-request admission.
- `scripts/trajectory.sh` — durable trajectory ledger with lease expiry and stale-writer rejection.
- `scripts/worker.sh` — non-interactive OpenCode execution plus deterministic repository validation.
- `scripts/publish.sh` / `scripts/publish.py` — candidate commit, branch, and PR publication.
- `scripts/admit.py` — evidence, current-base, check-run, and exact-head verification before GitHub merge.
- `schemas/` — machine-readable trajectory and evidence contracts.
- `examples/` — frontier, validation, and admission workflow templates.
- `tests/` — state-machine regression tests.

## Pinned OpenCode

The worker defaults to OpenCode `1.18.35`.

For Linux x64, the release asset `opencode-linux-x64.tar.gz` is verified against:

```
c8f888b451f5494a18f858fffb0e0b68f4e4baa9c241761c5f206884f0fa640d
```

The upstream `anomalyco/opencode/github@latest` wrapper is intentionally not the production trust anchor.

## Execution lifecycle

```
canonical Git SHA
  -> acquire trajectory lease by compare-and-swap
  -> remove GitHub write credential from model execution
  -> run fresh OpenCode worker
  -> run deterministic validation
  -> commit candidate on isolated branch
  -> open candidate PR
  -> upload SHA-bound evidence
  -> finalize trajectory
  -> terminate worker

candidate PR + exact evidence + required checks
  -> re-read canonical base
  -> verify PR head == evidence candidate SHA
  -> reject stale base or stale candidate
  -> GitHub protected-branch merge API
  -> canonical state
```

## Concurrency

The trajectory branch is the authoritative cross-run serialization primitive.

Each transition reads an exact trajectory ref head and publishes the next state with `--force-with-lease=<expected SHA>`. A competing or stale worker therefore fails instead of overwriting newer trajectory state.

GitHub Actions `concurrency` remains the first overlap barrier. It is not treated as final admission authority.

## Security boundary

The model execution step does not receive the GitHub write credential configured by this action. Git authentication is enabled only around deterministic trajectory and publication steps, then removed.

Repository `opencode.json` denies interactive questions, external directories, web fetch/search, and sensitive `.env` reads by default. OpenCode permissions are still tool policy, not host isolation.

Use CargoWall for runner egress enforcement. The production posture is:

```yaml
mode: enforce
offline: true
fail-on-unsupported: true
sudo-lockdown: true
```

Allow only GitHub infrastructure and the selected model-provider destinations.

## Deployment

Start from the templates:

```
examples/frontier.yml
examples/validate.yml
examples/admit.yml
```

The target repository must provide:

```
.github/opencode/frontier.md
./ci/validate
opencode.json
provider credentials
OPENCODE_MODEL repository variable
OPENCODE_ALLOWED_HOSTS repository variable
OPENCODE_REQUIRED_CHECKS repository variable
```

`./ci/validate` is the repository's deterministic gate. For the locked production stack it should execute the Nix/Dagger build-test graph; the validation workflow then adds Zizmor and Trivy, while release workflows may sign accepted artifacts with Cosign.

Protect the canonical branch and do not grant the model direct admission authority.

## Required GitHub permissions

Frontier workflow:

```yaml
permissions:
  contents: write
  pull-requests: write
  actions: read
```

Admission workflow:

```yaml
permissions:
  actions: read
  checks: read
  contents: write
  pull-requests: write
```

Branch protection/rulesets remain authoritative. The admission action does not bypass them.

## Production acceptance tests

Before enabling recurrence, prove all of the following:

- a normal worker acquires the trajectory and produces attributable evidence;
- a concurrent worker cannot steal an unexpired lease;
- an expired lease can be recovered;
- model execution has no GitHub write credential;
- failed OpenCode execution cannot publish a qualified candidate;
- failed deterministic validation cannot publish a qualified candidate;
- candidate evidence names the exact candidate SHA;
- changing the PR head after evidence causes admission rejection;
- moving canonical base after evidence causes admission rejection;
- missing or failed required checks cause admission rejection;
- a stale trajectory finalization is rejected;
- CargoWall fails closed when unsupported;
- protected canonical state can change only through the configured admission path.

Failure may become evidence. Failure does not become truth merely because it was produced.
