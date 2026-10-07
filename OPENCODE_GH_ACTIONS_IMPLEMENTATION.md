# OpenCode GitHub Actions Implementation

Status: production handoff artifact  
Repository: `Samwise-x/opencode-actions`  
Implementation branch: `implementation/production-v1`  
Design target: one singular logical repository trajectory, sequentially inhabited by disposable OpenCode/frontier-model workers.

## 1. Objective

This implementation turns OpenCode into a disposable execution substrate for a GitHub-native, deterministic software-development trajectory.

The model is not the durable system. The OpenCode session is not the durable system. The GitHub Actions runner is not the durable system.

Durable state is GitHub itself:

- canonical repository history
- GitHub Issues and dependency/frontier labels
- persistent candidate branches and pull requests
- exact-SHA CI results
- immutable workflow artifacts
- signed qualification evidence
- a dedicated trajectory branch used only for lease/CAS coordination

The worker can disappear after every pass. The next worker reconstructs the same logical trajectory from repository truth.

## 2. Non-negotiable invariants

1. Exactly one primary trajectory is active at a time.
2. Models/providers are replaceable labor.
3. OpenCode sessions are evidence, never canonical continuity.
4. GitHub is the durable body of the trajectory.
5. A worker never admits its own output.
6. Candidate code never becomes canonical merely because a model produced it.
7. Admission is deterministic and exact-SHA bound.
8. Admission fails closed when canonical base moved, candidate moved, evidence is stale, required checks are absent, or a protected path changed.
9. Autonomous workers do not receive canonical-admission credentials.
10. Control-plane files are protected from autonomous modification.
11. Coordination state uses compare-and-swap semantics.
12. Failure is evidence, not truth.
13. No handoff journal, STATUS file, or model-authored summary is required for continuity.
14. The next worker reconstructs from repository state, not prior model context.
15. Bounded subagents may research/test/review, but they do not create competing canonical trajectories.

## 3. Logical pipeline

```text
GitHub Issue frontier
        |
        v
12-minute scheduled frontier workflow
        |
        v
trajectory lease/CAS
        |
        v
deterministic frontier reconstruction
        |
        v
persistent candidate branch
        |
        v
CargoWall-contained disposable OpenCode worker
        |
        v
pre-publish deterministic validation
        |
        v
candidate commit + PR
        |
        v
exact-SHA deterministic CI
   |              |
   v              v
Dagger/Nix    Zizmor/Trivy
   \              /
    \            /
     v          v
      qualification seal
        |
        v
Cosign/Sigstore signed evidence
        |
        v
dedicated admission workflow
        |
        v
verify identity + evidence + checks + protected paths
        |
        v
force-with-lease exact-SHA canonical ref update
```

## 4. Repository implementation

The production implementation is intentionally small.

```text
.
├── action.yml
├── admit/
│   └── action.yml
├── seal/
│   └── action.yml
├── scripts/
│   ├── admit.py
│   ├── check-protected.py
│   ├── git-auth.sh
│   ├── install-opencode.sh
│   ├── publish.py
│   ├── publish.sh
│   ├── sanitize-git.sh
│   ├── seal.py
│   ├── select-frontier.py
│   ├── trajectory.sh
│   └── worker.sh
├── schemas/
│   ├── evidence-v2.schema.json
│   ├── qualification-v1.schema.json
│   └── trajectory-v2.schema.json
└── templates/
    ├── frontier.yml
    ├── candidate-validation.yml
    ├── admit.yml
    ├── frontier.md
    ├── opencode.json
    └── protected-paths.txt
```

## 5. Frontier action

`action.yml` is the reusable composite action.

It performs, in order:

1. checkout with `persist-credentials: false`
2. immutable attempt/base identity capture
3. action-byte integrity digest
4. pinned OpenCode installation with SHA-256 verification
5. trajectory lease acquisition
6. deterministic frontier reconstruction
7. persistent candidate branch preparation
8. GitHub credential removal assertion
9. CargoWall containment
10. disposable OpenCode execution
11. action-byte integrity revalidation
12. deterministic publication of the candidate
13. immutable evidence upload
14. trajectory finalization or failure release

The model step receives no GitHub token and cannot use the wrapper's privileged mutation path.

## 6. Frontier reconstruction

`scripts/select-frontier.py` reconstructs the logical continuation point.

Selection order:

1. explicit issue, when supplied
2. oldest still-open OpenCode candidate PR targeting the canonical branch
3. highest-priority open issue labeled `ready-for-agent`
4. idle when no work exists

Priority labels are deterministic:

```text
priority:p0 / priority:critical
priority:p1 / priority:high
priority:p2 / priority:medium
priority:p3 / priority:low
unlabeled
```

Within equal priority, creation time and issue number break ties.

The selected issue and current PR state are serialized into `.opencode-evidence/frontier.json` and injected into the worker prompt.

## 7. Persistent candidate state

A selected issue owns one persistent candidate branch:

```text
opencode/issue-<issue-number>
```

If the branch already exists, the wrapper resumes it and merges the current canonical branch into it before model execution.

If that merge conflicts, the worker is told that conflicts exist and must resolve them before doing other work.

The candidate branch is continuity for unfinished implementation. It is not canonical truth.

## 8. Trajectory lease and CAS

`scripts/trajectory.sh` owns cross-run single-worker coordination.

Coordination lives on:

```text
refs/heads/opencode/trajectory
```

That branch carries only `trajectory.json`.

The state includes:

- schema version
- monotonic logical version
- status
- lease token
- owning attempt
- canonical base SHA
- run ID
- lease expiration
- last attempt
- last base
- last candidate
- last evidence reference
- last issue
- last PR

Lease acquisition is a Git compare-and-swap:

```text
read current trajectory ref
-> derive next state
-> commit next state
-> push with --force-with-lease against observed ref
```

Only one competing worker can win the observed ref.

A live unexpired lease blocks a second worker.

A previously published candidate also blocks fresh work while deterministic qualification/admission is still pending.

## 9. OpenCode worker boundary

`scripts/worker.sh` runs the probabilistic worker.

The worker receives:

- repository checkout
- selected issue
- existing PR state when present
- canonical base SHA
- persistent candidate branch
- repository instructions
- configured OpenCode agent/model

The worker is explicitly prohibited from:

- GitHub mutation
- commit/push
- branch switching
- rebase/reset
- Git configuration or remote mutation
- control-plane modification
- weakening security/admission policy
- interactive questions
- creating duplicate handoff/status state

The wrapper, not the model, performs privileged publication.

OpenCode is executed with JSON event output. Session IDs and event output are captured as evidence, but are not required for continuity.

## 10. Process containment

CargoWall is mandatory around probabilistic execution.

Required policy:

```yaml
mode: enforce
offline: true
fail-on-unsupported: true
sudo-lockdown: true
```

Only explicit model/provider hosts are allowlisted.

The wrapper additionally:

- removes GitHub tokens from the model environment
- redirects GitHub Actions command-file environment variables to decoys
- sanitizes Git configuration
- removes GitHub auth headers before model execution
- rejects model movement of Git HEAD
- rejects unresolved merge conflicts
- rejects protected-path modifications
- kills surviving same-user processes created during model execution
- re-hashes action implementation bytes after the model exits

CargoWall owns runtime/network containment. OpenCode permissions are defense in depth, not the sole security boundary.

## 11. OpenCode policy

The repository template config disables sharing and denies:

- secrets/environment files
- GitHub workflow control plane
- admission/coordination files
- OpenCode configuration
- AGENTS/CONTEXT/ADRs
- Nix/Dagger control files
- GitHub CLI mutation
- Git commit/push/reset/clean/checkout/switch/rebase/merge/config/remote
- sudo/background persistence/system services
- environment dumping
- external-directory access
- interactive questions
- web fetch/search

Normal repository read/edit, search, LSP, task delegation, and bounded shell execution remain available.

## 12. Protected paths

The deterministic wrapper independently enforces a protected-path file. This is separate from OpenCode's own permission layer.

Typical protected paths:

```text
.github/workflows/opencode-frontier.yml
.github/workflows/opencode-candidate-validation.yml
.github/workflows/opencode-admit.yml
.opencode-actions/**
.opencode/plugins/**
opencode.json
opencode.jsonc
AGENTS.md
CONTEXT.md
docs/adr/**
flake.nix
flake.lock
dagger.json
dagger/**
.zizmor.yml
.trivyignore
.trivyignore.yaml
```

A candidate touching these paths is rejected before publication and again before admission.

## 13. Candidate publication

Only the trusted wrapper publishes.

`scripts/publish.sh`:

1. stages non-evidence worktree changes
2. commits through a safe empty hooks path
3. records `OpenCode-Attempt` and issue identity in commit metadata
4. requires the candidate to descend from the canonical base
5. updates the persistent candidate branch with force-with-lease
6. binds evidence to the resulting candidate SHA

`scripts/publish.py` creates or updates exactly one PR for the candidate branch and verifies the PR head SHA equals the candidate SHA.

## 14. Attempt evidence

Each worker pass produces attributable machine-readable evidence.

Evidence includes:

- attempt ID
- issue number
- canonical base SHA
- candidate SHA
- candidate branch
- PR identity
- model
- OpenCode agent
- OpenCode exit status
- prevalidation exit status
- OpenCode session IDs
- SHA-256 of OpenCode NDJSON
- SHA-256 of worktree diff
- SHA-256 of validation log
- timestamps

The artifact name is:

```text
opencode-evidence-<run-id>-<run-attempt>
```

The evidence is an audit record. It does not grant admission authority.

## 15. Deterministic qualification

The candidate validation workflow runs against the exact PR head SHA.

Required checks are named:

```text
deterministic
security
```

The deterministic job executes the repository's canonical Nix/Dagger graph:

```bash
nix develop --no-write-lock-file --command dagger call validate
```

This makes the same build/test graph callable locally and in CI.

The security job executes:

- Zizmor for GitHub Actions static security
- Trivy for vulnerability, secret, and misconfiguration scanning

The seal job runs only after both succeed.

## 16. Qualification sealing

The seal job downloads the exact originating worker evidence by reading the `OpenCode-Attempt` marker from the candidate commit.

`scripts/seal.py` verifies:

- worker evidence schema/kind
- worker status is prevalidated
- evidence candidate SHA equals PR head SHA
- evidence PR number equals current PR
- OpenCode exited successfully
- pre-publish validation exited successfully

It emits `qualification.json` containing:

- repository
- candidate SHA
- canonical base SHA
- issue
- PR
- attempt
- model/agent
- hash of frontier evidence
- validation run ID
- validation workflow ref
- required checks
- generation time

The seal action then signs that exact blob keylessly with Cosign/Sigstore using GitHub Actions OIDC.

The signature bundle is stored beside the qualification manifest.

## 17. Admission

Admission is deliberately separate from model execution and validation.

The admission workflow is triggered only by successful completion of the named candidate-validation workflow.

It downloads the sealed qualification artifact from that exact validation run and calls `admit/action.yml`.

Admission requires a dedicated credential, `ADMISSION_TOKEN`, which is never exposed to the frontier worker.

`scripts/admit.py` verifies:

1. qualification schema and identity
2. repository identity
3. exact candidate SHA
4. exact PR number
5. PR is still open
6. PR head has not moved
7. canonical branch still equals the evidence base SHA
8. every required check exists on the candidate
9. every required check is completed successfully
10. fetched base/candidate refs equal the qualified SHAs
11. candidate is a descendant of base
12. candidate does not modify protected control-plane paths

Only then does it perform:

```text
candidate SHA -> canonical branch
```

using:

```text
--force-with-lease=refs/heads/<canonical>:<qualified-base-sha>
```

That is the final single-writer compare-and-swap admission primitive.

If canonical state moved, admission fails. The candidate must be reconstructed/revalidated against the new canonical state.

## 18. Sigstore identity verification

Before admission, Cosign verifies the qualification bundle against:

- GitHub Actions OIDC issuer
- the repository identity
- the configured validation workflow path

This prevents an arbitrary artifact from being treated as qualified evidence merely because it has the right filename.

## 19. Failure semantics

Expected failures are fail-closed.

### Worker timeout/failure

No candidate is admitted. Attempt evidence is retained. Lease is released/expired. Next pass reconstructs.

### Worker leaves merge conflicts

Publication fails.

### Worker changes HEAD

Publication fails.

### Worker changes protected path

Publication fails.

### Candidate branch races

Force-with-lease rejects stale publication.

### Two workers race for trajectory

Only one lease CAS succeeds.

### Candidate awaiting CI

New frontier execution is suppressed until qualification resolves.

### CI failure

Candidate remains noncanonical. A later worker may resume the same issue/branch and repair it.

### Canonical branch moves before admission

Admission CAS fails. Evidence is stale by definition.

### PR head moves after validation

Admission rejects the mismatch.

### Missing required check

Admission rejects.

### Signature identity mismatch

Admission rejects.

### Admission credential absent

Canonical mutation is impossible.

## 20. Caller repository contract

A target repository must provide:

```text
AGENTS.md
CONTEXT.md
docs/adr/
flake.nix
flake.lock
dagger.json
dagger/
.github/opencode/frontier.md
.opencode-actions/protected-paths.txt
opencode.json
.github/workflows/opencode-frontier.yml
.github/workflows/opencode-candidate-validation.yml
.github/workflows/opencode-admit.yml
```

It must also provide issues labeled `ready-for-agent`.

The repository's Dagger module must expose:

```text
validate
```

as the canonical deterministic validation entry point.

## 21. Required repository settings

Create:

- repository variable `OPENCODE_MODEL`
- optional variable `OPENCODE_ALLOWED_HOSTS`
- secret `OPENCODE_API_KEY`
- secret `ADMISSION_TOKEN`

The admission credential should be the narrowest possible GitHub App/token capable of:

- updating the canonical contents/ref
- closing the admitted issue

It must not be available to the frontier workflow.

Protect `main` against ordinary direct pushes. The dedicated admission identity is the only automated writer intended to advance canonical state.

## 22. Installation

Copy the templates into the target repository:

```text
templates/frontier.yml
  -> .github/workflows/opencode-frontier.yml

templates/candidate-validation.yml
  -> .github/workflows/opencode-candidate-validation.yml

templates/admit.yml
  -> .github/workflows/opencode-admit.yml

templates/frontier.md
  -> .github/opencode/frontier.md

templates/opencode.json
  -> opencode.json

templates/protected-paths.txt
  -> .opencode-actions/protected-paths.txt
```

Replace `__IMPLEMENTATION_SHA__` in all workflow templates with the immutable commit SHA of this implementation.

Never deploy production callers against a mutable branch/tag.

## 23. Schedule

The frontier workflow uses:

```cron
0,12,24,36,48 * * * *
```

This creates five deterministic phase points per hour.

The lease is intentionally shorter than the next phase interval and the OpenCode worker timeout is shorter than the lease.

Default values:

```text
worker runtime: 540 seconds
lease lifetime: 690 seconds
phase interval: 720 seconds
```

## 24. Ownership boundaries

OpenCode owns probabilistic implementation execution.

GitHub Issues own work intent/frontier.

Git commits own implementation state.

PRs own proposed transitions.

Nix owns reproducible environment closure.

Dagger owns portable deterministic build/test execution.

Zizmor owns GitHub Actions static-security validation.

Trivy owns vulnerability/secret/misconfiguration scanning.

CargoWall owns runtime/network containment.

Cosign/Sigstore owns qualification signing and identity verification.

The trajectory branch owns single-worker coordination only.

The admission action owns the final canonical compare-and-swap.

No model owns admission.

## 25. Why OpenCode session persistence is intentionally excluded

OpenCode already has useful local session/message/event persistence. That is valuable for audit and local resumption, but a hosted GitHub Actions runner is disposable.

Trying to preserve the entire OpenCode runtime would couple continuity to:

- runner lifetime
- local SQLite
- a particular model/provider
- internal OpenCode storage semantics

This implementation instead persists the trajectory OpenCode operates on.

A fresh worker needs repository truth, current issue/PR state, candidate branch, canonical SHA, CI/evidence, and deterministic policy. It does not need the previous model's hidden state.

## 26. Production acceptance criteria

The implementation is production-ready only when an end-to-end canary proves all of the following:

- a ready issue is selected deterministically
- exactly one worker acquires the trajectory
- a second concurrent worker is rejected
- OpenCode can modify ordinary source code
- OpenCode cannot mutate protected paths
- OpenCode has no usable GitHub credential
- a candidate branch and PR are created
- worker evidence binds to the exact candidate SHA
- deterministic and security checks run on that SHA
- qualification is signed by the expected workflow identity
- admission rejects a stale base
- admission rejects a moved PR head
- admission rejects a missing/failed required check
- admission rejects protected-path changes
- admission succeeds for one fully qualified candidate
- canonical branch lands on the exact qualified SHA
- the associated issue closes only after successful admission
- the next scheduled worker reconstructs from the new canonical state

## 27. Canonical mental model

The implementation reduces to this:

```text
GitHub is the durable body.
OpenCode is disposable execution.
The frontier model is disposable cognition.
Nix + Dagger + security gates are deterministic evaluation.
Evidence is exact-SHA bound and signed.
The trajectory lease prevents competing writers.
The admission CAS decides canonical truth.
```

The system does not preserve an agent.

It preserves a trajectory.
