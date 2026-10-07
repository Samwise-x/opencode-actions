# Security model

## Probabilistic zone

OpenCode and any delegated subagent are untrusted candidate producers.

Before model execution, GitHub credentials are removed, GitHub Actions command-file paths are replaced with decoys, the immutable action checkout is hashed, and CargoWall starts with `mode: enforce`, `offline: true`, `fail-on-unsupported: true`, and `sudo-lockdown: true`.

After execution, the action checkout digest is rechecked before any privileged mutation.

## GitHub authority separation

The frontier wrapper owns a normal repository token only in deterministic pre/post steps. The OpenCode process receives neither `GH_TOKEN` nor `GITHUB_TOKEN`.

The final `ADMISSION_TOKEN` is a separate credential exposed only to the admission workflow. It should be a narrowly scoped GitHub App installation token or equivalent credential with just enough authority to advance canonical state and close the accepted issue.

## Git metadata isolation

Do not trust the worker worktree's `.git` directory after model execution. Publication creates a fresh Git repository in RUNNER_TEMP, fetches trusted refs, mirrors candidate filesystem content while excluding `.git`, stages the result, rechecks protected paths, and only then commits/pushes.

Trajectory CAS operations also create a fresh temporary Git repository per invocation.

This prevents candidate-controlled local Git config, hooks, clean/smudge filters, remotes, or credential helpers from becoming privileged execution paths.

## Protected control plane

The target installs `.opencode-actions/protected-paths.txt`. The default policy protects the three orchestration workflows, OpenCode configuration/plugins, context/ADR files, Nix/Dagger control files, and Zizmor/Trivy policy.

OpenCode permissions deny those edits first. Deterministic path validation denies them again before publication and admission. A candidate cannot redefine the tests or controls that qualify itself.

## Network containment

CargoWall restricts the probabilistic job to GitHub infrastructure plus explicitly allowed model/provider/build destinations. Provider hosts remain an intentional egress channel because inference requires them, which is precisely why GitHub admission credentials are absent from the model process.

## Remaining boundary

This is strong CI containment, not a hypervisor. Candidate code can consume runner CPU/memory, alter ordinary candidate files, and transmit data to explicitly allowed provider hosts. Repositories treating candidate code as actively hostile should add a disposable VM/container boundary around the probabilistic job.
