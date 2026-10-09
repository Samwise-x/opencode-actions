# Security contract

## Trust zones

### Probabilistic zone

The frontier OpenCode/model process is untrusted for canonical authority.

It receives source code, issue/PR context, selected provider credentials needed for inference, and only the runtime capabilities permitted by repository OpenCode policy. It does not receive the admission token or a GitHub mutation token.

### Candidate-validation zone

Candidate code is untrusted. Deterministic/security jobs run with read-only repository authority and no admission secret or OIDC signing authority. Autonomous candidate identity is derived from commit evidence plus GitHub's native PR→Issue closing relationship, and the Issue must still be open and `ready-for-agent`; branch names confer no authority.

### Trusted qualification zone

The seal job runs only after deterministic and security jobs succeed. It checks out the original canonical base, not candidate code, before entering the canonical Nix environment. It has OIDC solely to create the keyless Cosign signature.

### Trusted admission zone

Admission executes no candidate code. It verifies signed evidence, the exact recorded successful validation workflow run and required jobs, live GitHub state, ancestry, and protected paths, then performs one atomic fast-forward CAS.

## Credential separation

OPENCODE_API_KEY belongs only to the frontier job.

ADMISSION_TOKEN belongs only to the admission job.

GitHub OIDC signing authority belongs only to the trusted seal job.

Do not collapse these credentials into one job or one long-lived token.

## Model-job defense in depth

The model subprocess has GH_TOKEN and GITHUB_TOKEN removed; GitHub command-file environment variables redirected to decoys; strict CargoWall enforcement, offline policy mode, fail-on-unsupported, and sudo lockdown; OpenCode question/web network/external-directory permissions denied; a runtime plugin that blanks secret-like environment variables for shell tools and blocks direct GitHub/Git mutation commands; protected-path checks; HEAD/conflict checks; bounded runtime; and post-run process cleanup.

Privileged candidate publication and trajectory mutation are reconstructed in fresh temporary Git repositories rather than trusting model-controlled `.git` metadata. Immediately before candidate publication, the wrapper revalidates the live trajectory SHA, lease token, originating attempt/base, and expiry. These controls reduce model authority. They do not make model output trustworthy. Trust is conferred only by deterministic qualification plus admission.

## Supply-chain pins

Production templates pin third-party GitHub Actions to immutable commit SHAs. All self-references to Samwise-x/opencode-actions are rendered from the single immutable `release.json.runtime_sha`, eliminating independent hand-maintained runtime pins.

OpenCode is downloaded from a fixed release asset and SHA-256 verified before execution.

The target `flake.lock` owns the reproducible Dagger/project validation toolchain. Qualification and admission obtain Cosign from exact nixpkgs revision `2833a4f2f08058f980a143c9fb447953ef15f1cb`. Workflows use `--no-write-lock-file`; CI may not silently mutate project lock state.

## Network

CargoWall is authoritative around the probabilistic worker and trusted sign/admit phases.

Provider-specific hosts belong in OPENCODE_ALLOWED_HOSTS. Keep the set minimal. Do not wildcard broad public hosting domains merely to make a failing build green.

Candidate validation is intentionally isolated from provider/admission secrets. It may require broader package/build egress because it executes the project's Nix/Dagger graph.

## Protected policy

The default protected-path file prevents autonomous workers from changing the entire GitHub workflow tree plus their admission, Nix/Dagger, OpenCode, scanner, architecture, and ADR control plane.

Repository-specific control files should be added before production.

## Branch rules and admission identity

The dedicated admission identity may need a narrowly scoped ruleset bypass to fast-forward protected main. That exception belongs only to the admission identity.

A worker identity with the same bypass destroys the security model.

## Evidence

Worker evidence is diagnostic and attributable but not sufficient for admission.

Qualification is a separate document produced only after exact-SHA deterministic/security jobs succeed and is signed through GitHub OIDC with Cosign. It records the originating validation run and workflow reference. Admission verifies the expected signing workflow identity and OIDC issuer, then independently resolves that exact validation run and its required jobs before using the qualification.

## Self-healing boundary

Release drift detection is deterministic and intentionally weaker than canonical authority. It may prepare a `release.json` promotion commit and open/update a PR with narrowly scoped job credentials. It cannot merge that PR, bypass admission, or reinterpret failed validation as success. Bootstrap similarly self-heals known generated predecessor bytes but refuses unknown drift rather than overwriting human-owned state.
