# Failure model

The protocol fails closed around canonical state.

## Worker dies before publication

Only a lease may exist. When it expires, a successor reconstructs from GitHub/Git. main is unchanged.

## OpenCode exits non-zero or times out

The attempt is failed. Diagnostic evidence may upload, but no candidate is qualified and no model output becomes truth.

## Model attempts GitHub mutation

The OpenCode subprocess receives no GitHub mutation token. gh, Git mutation commands, sudo/background-service commands, and protected control-plane edits are denied by repository policy/runtime guard. CargoWall constrains egress.

The wrapper still revalidates Git state after the model because prompt/tool policy is not the final security boundary.

## Model alters Git state or wrapper bytes

The attempt is rejected if HEAD changed, merge conflicts remain, protected paths changed, or the checked-out action bytes no longer match the pre-execution digest.

Privileged Git phases replace .git/config, use /dev/null hooks, safe HOME/global config, and trusted absolute tool paths.

## Background process survives model exit

The worker snapshots same-user processes before model execution and terminates newly created survivors afterward. Canonical authority still remains outside the model process.

## Two workers overlap

The trajectory ref is advanced by force-with-lease CAS. Only the worker that observed and owns the expected trajectory SHA can continue as the single writer.

Publication revalidates the current trajectory SHA, lease token, attempt, base, and expiry immediately before any candidate branch push. A worker that loses or outlives its lease cannot publish and cannot rely on a later failed finalize to clean up already-mutated remote state.

GitHub workflow concurrency is an outer optimization. The ref CAS plus publication-time lease assertion is the authority.

## Candidate branch races

Publishing a persistent opencode/issue-N branch uses force-with-lease against the remote head observed before the model ran. A stale worker cannot replace a newer candidate.

## Candidate authorization is revoked

If an Issue is closed or loses `ready-for-agent`, a linked PR no longer authorizes autonomous work. Frontier reconstruction skips it and autonomous candidate validation rejects newly published agent state until authorization is explicitly restored.

## Candidate validation fails

Trajectory state remains validated, but the next acquisition observes failed required checks and permits a repair pass on the same linked Issue branch when that Issue is still authorized.

## Candidate validation is still running

The next acquisition returns validation_pending and does not start another model.

## Validation passes but admission has not completed

The next acquisition returns admission_pending. No competing candidate is created.

Admission does not trust a same-named check from another run. Signed qualification names the exact candidate-validation run, workflow identity, PR, candidate SHA, and required jobs; any mismatch rejects.

## Worker evidence missing

The seal job cannot reconstruct the originating attempt artifact and therefore cannot produce signed qualification. Canonical state is unchanged.

## Qualification tampered

Cosign verification fails. Canonical state is unchanged.

## Candidate branch moves after qualification

Admission requires the live PR head to equal the signed candidate SHA. It rejects.

## Canonical base moves after qualification

Admission requires live main to equal the signed base SHA. It rejects and a successor reconstructs.

## Protected control-plane file changes

Both pre-publish policy and final admission compare the candidate against the qualified base. The default target policy protects the entire `.github/workflows/**` tree as well as the other autonomous control surfaces. Admission refuses a candidate touching a protected pattern even if another check was misconfigured.

## Two admissions race

Each admission pushes the exact candidate with force-with-lease against the qualified base. Only a process that still observes the qualified canonical base can succeed. The losing process fails atomically.

## GitHub/API/network failure

Partial execution is not interpreted as success. Recovery rereads current refs, Issues, PRs, checks, artifacts, and the trajectory ref.

## OpenCode local state disappears

Expected. OpenCode sessions, local SQLite, model context, MCP connections, and background registries are runtime-only state. They are not needed to resume the logical trajectory.

## Managed-file drift

Bootstrap upgrades a managed file only when its exact Git blob is a known previously generated release artifact. Unknown edits are not guessed around or overwritten; reconciliation stops. Runtime-bearing distribution drift is detected separately and may generate a release-promotion PR, never an automatic canonical promotion.

## Greenfield repository has no real validation

Bootstrap may create a Dagger module shape, but the generated `Validate` implementation fails deliberately. No autonomous candidate can become qualified until the repository supplies a real deterministic validation contract and reruns `make`.
