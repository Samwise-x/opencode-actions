# Deployment

This repository is a handoff package. The target repository receives the templates and keeps this implementation pinned by immutable commit SHA.

## 1. Copy target files

- `templates/frontier.yml` -> `.github/workflows/opencode-frontier.yml`
- `templates/candidate-validation.yml` -> `.github/workflows/opencode-candidate-validation.yml`
- `templates/admit.yml` -> `.github/workflows/opencode-admit.yml`
- `templates/frontier.md` -> `.github/opencode/frontier.md`
- `templates/opencode.json` -> `opencode.json`
- `templates/protected-paths.txt` -> `.opencode-actions/protected-paths.txt`

Do not replace immutable action SHAs with floating tags.

## 2. Supply deterministic project validation

Commit `flake.nix` and `flake.lock`. The Nix development environment must expose Dagger.

Provide a Dagger module with a zero-argument `validate` function. It should own formatting, linting, unit/integration tests, build/package validation, and repository-specific deterministic policy.

Candidate CI contract:

`nix develop --no-write-lock-file --command dagger call validate`

## 3. Configure work state

Create the `ready-for-agent` label. Optional understood priorities are `priority:p0` through `priority:p3` plus critical/high/medium/low aliases.

Only apply `ready-for-agent` after blocking dependencies are resolved.

## 4. Configure model access

Actions secret: `OPENCODE_API_KEY`.

Actions variable: `OPENCODE_MODEL`.

Actions variable: `OPENCODE_ALLOWED_HOSTS`, newline-separated CargoWall host[:port] entries needed by the model provider or project-specific worker commands.

## 5. Configure admission authority

Create `ADMISSION_TOKEN` as a dedicated GitHub App installation token or equivalent credential exposed only to `.github/workflows/opencode-admit.yml`.

It needs the minimum authority required to update the canonical branch and close the accepted issue. If the canonical ruleset blocks all direct updates, grant bypass only to this admission identity.

The frontier worker identity must not receive ruleset bypass.

## 6. Protect canonical state

Block ordinary direct pushes to `main`. Require `deterministic` and `security` for normal PRs. Keep control-plane files under CODEOWNERS/rulesets where practical.

Automated admission independently rechecks named checks and exact-SHA CAS, so branch protection is defense in depth rather than the only correctness boundary.

## 7. Acceptance test before enabling cron

1. Dispatch one explicit issue.
2. Confirm one candidate branch/PR is created.
3. Confirm OpenCode cannot push or call GitHub directly.
4. Confirm attempt evidence is uploaded.
5. Confirm deterministic/security jobs run on the exact PR head.
6. Confirm the seal artifact contains `qualification.json` and a Sigstore bundle.
7. Move `main` before admission and confirm stale admission rejects.
8. Move the PR head after qualification and confirm exact-SHA rejection.
9. Attempt a protected-path edit and confirm publication/admission rejects it.
10. Overlap two frontier dispatches and confirm one trajectory lease owns execution.

Only after those checks should the five-times-per-hour schedule remain enabled.
