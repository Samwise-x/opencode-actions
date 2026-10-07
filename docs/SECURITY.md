# Security contract

## Trust zones

### Probabilistic zone

The frontier OpenCode/model process is untrusted for canonical authority.

It receives source code, issue/PR context, selected provider credentials needed for inference, and only the runtime capabilities permitted by repository OpenCode policy. It does not receive the admission token or a GitHub mutation token.

### Candidate-validation zone

Candidate code is untrusted. Deterministic/security jobs run with read-only repository authority and no admission secret or OIDC signing authority.

### Trusted qualification zone

The seal job runs only after deterministic and security jobs succeed. It checks out the original canonical base, not candidate code, before entering the canonical Nix environment. It has OIDC solely to create the keyless Cosign signature.

### Trusted admission zone

Admission executes no candidate code. It verifies evidence and GitHub state, then performs one atomic fast-forward CAS.

## Credential separation

OPENCODE_API_KEY belongs only to the frontier job.

ADMISSION_TOKEN belongs only to the admission job.

GitHub OIDC signing authority belongs only to the trusted seal job.

Do not collapse these credentials into one job or one long-lived token.

## Model-job defense in depth

The model subprocess has GH_TOKEN and GITHUB_TOKEN removed; GitHub command-file environment variables redirected to decoys; strict CargoWall enforcement, offline policy mode, fail-on-unsupported, and sudo lockdown; OpenCode question/web network/external-directory permissions denied; a runtime plugin that blanks secret-like environment variables for shell tools and blocks direct GitHub/Git mutation commands; protected-path checks; HEAD/conflict checks; bounded runtime; and post-run process cleanup.

Privileged candidate publication and trajectory mutation are reconstructed in fresh temporary Git repositories rather than trusting model-controlled `.git` metadata. These controls reduce model authority. They do not make model output trustworthy. Trust is conferred only by deterministic qualification plus admission.

## Supply-chain pins

Production templates pin third-party GitHub Actions to immutable commit SHAs.

OpenCode is downloaded from a fixed release asset and SHA-256 verified before execution.

The target `flake.lock` owns the reproducible Dagger/project validation toolchain. Qualification and admission obtain Cosign from exact nixpkgs revision `2833a4f2f08058f980a143c9fb447953ef15f1cb`. Workflows use `--no-write-lock-file`; CI may not silently mutate project lock state.

## Network

CargoWall is authoritative around the probabilistic worker and trusted sign/admit phases.

Provider-specific hosts belong in OPENCODE_ALLOWED_HOSTS. Keep the set minimal. Do not wildcard broad public hosting domains merely to make a failing build green.

Candidate validation is intentionally isolated from provider/admission secrets. It may require broader package/build egress because it executes the project's Nix/Dagger graph.

## Protected policy

The default protected-path file prevents autonomous workers from changing their own workflow, admission, Nix/Dagger, OpenCode, scanner, architecture, and ADR control plane.

Repository-specific control files should be added before production.

## Branch rules and admission identity

The dedicated admission identity may need a narrowly scoped ruleset bypass to fast-forward protected main. That exception belongs only to the admission identity.

A worker identity with the same bypass destroys the security model.

## Evidence

Worker evidence is diagnostic and attributable but not sufficient for admission.

Qualification is a separate document produced only after exact-SHA deterministic/security jobs succeed and is signed through GitHub OIDC with Cosign. Admission verifies the expected workflow identity and OIDC issuer before using it.
