# Deployment

This repository is a handoff substrate. The target repository receives the templates and pins this implementation by commit SHA.

## 1. Canonical build environment

The target must have committed flake.nix and flake.lock.

The canonical dev shell must contain project build/test dependencies, Dagger CLI, and Cosign CLI.

The target Dagger module must expose:

    dagger call validate

That call is the portable deterministic build/test/package graph. Local and CI validation should execute the same graph.

## 2. Install repository files

Copy the files listed in the root README. Do not copy runtime evidence or trajectory state into main.

Review .opencode-actions/protected-paths.txt. Its default denies autonomous modification of workflow/admission policy, OpenCode policy/plugins, AGENTS/CONTEXT/ADRs, Nix/Dagger definitions, and security scanner policy.

## 3. Configure OpenCode

Set OPENCODE_MODEL.

Create the provider credential required by that model. The included example uses OPENCODE_API_KEY.

Set OPENCODE_ALLOWED_HOSTS to the smallest CargoWall egress allowlist needed by that provider and the lightweight pre-publish validation command. GitHub service hosts required by Actions are automatically covered by CargoWall.

Do not enable OpenCode session sharing for the worker.

## 4. Configure the admission identity

Create a dedicated GitHub App or equivalently scoped token for ADMISSION_TOKEN.

It needs only the authority required to read repository/PR/ref state, fast-forward the canonical branch despite the ordinary PR-only rule, and close the accepted Issue.

It must not be available to the frontier worker, deterministic candidate job, or security candidate job.

If the repository ruleset cannot narrowly allow this identity to perform the exact final fast-forward, deployment is incomplete. Do not compensate by granting the ordinary worker broad bypass.

## 5. Canonical branch rules

Protect main.

For ordinary changes, require PRs and successful deterministic and security checks. Deny force pushes/non-fast-forward updates. Do not grant worker credentials ruleset bypass.

The admission algorithm still verifies current base, exact PR head, exact check runs, ancestry, protected paths, signed qualification, and then uses force-with-lease. Branch rules are defense in depth, not the algorithm itself.

## 6. Labels

Create ready-for-agent.

Optional deterministic priority labels understood by the selector are priority:p0/critical, priority:p1/high, priority:p2/medium, and priority:p3/low.

Without priority labels, oldest ready issue then lowest issue number wins.

## 7. Prove the protocol before scheduling

Keep the schedule workflow disabled or remove its schedule trigger during acceptance.

Run one explicit issue manually. Confirm the model receives issue/PR context and produces one opencode/issue-N branch and PR.

Then deliberately test validation failure, worker interruption, overlapping frontier runs, candidate branch movement after evidence, canonical main movement after qualification, protected-path modification, tampered qualification, expired lease recovery, and one successful exact-SHA admission.

Every failure must leave canonical main unchanged.

## 8. Enable cadence

Enable the 12-minute schedule only after all acceptance cases pass.

A no-work frontier finalizes idle. A currently validating candidate returns validation_pending. A qualified candidate waiting for admission returns admission_pending. These are normal states, not worker failures.
