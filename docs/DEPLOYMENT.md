# Deployment

This is a handoff substrate. Copy it into the target repository after replacing repository-specific validation and provider configuration.

## Required configuration

Protect the canonical branch. Agents must not push directly to it.

Configure provider credentials as GitHub secrets or approved workload identity. Never commit credentials.

Set OPENCODE_MODEL, OPENCODE_AGENT when used, and TRAJECTORY_ID as repository variables.

## OpenCode

Do not use anomalyco/opencode/github@latest as the production trust anchor. Pin OpenCode deliberately. The audited implementation target is v1.18.35; revalidate its release installation mechanism before unattended execution.

## CargoWall

Required posture:

    mode: enforce
    offline: true
    fail-on-unsupported: true
    sudo-lockdown: true

Allow only destinations required by the selected model provider and deterministic build graph.

## Acceptance tests

Before enabling recurrence, manually run a disposable objective; prove the worker cannot mutate main; prove candidate SHA evidence validates; move main and prove stale admission rejects; alter a candidate after evidence and prove rejection; overlap two attempts and prove one admission path; prove CargoWall fails closed; prove failed deterministic checks cannot be overridden.

Failure may produce evidence. Failure may not become truth merely because an agent produced it.
