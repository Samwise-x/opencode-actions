# Agent execution contract

Work only inside the checked-out repository. Read repository context and ADRs when present.

Never push, merge, force-update, or mutate the canonical branch. Produce candidate state only.

Run deterministic validation before completion. Do not weaken, skip, delete, or reinterpret a failing check.

Do not read secret files, external directories, or credentials. Do not print environment secrets.

Prefer existing structure and dependencies. Do not create parallel state files, handoff journals, or speculative abstractions.

A successful attempt ends with coherent candidate state. Canonical admission belongs to deterministic repository machinery, not the model.

## Agent skills

### Issue tracker

GitHub Issues are the durable work surface; work only the current unblocked `ready-for-agent` frontier. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical category/state roles and exactly one state role for triaged work. See `docs/agents/triage-labels.md`.

### Domain docs

This repository is single-context: domain vocabulary lives in root `CONTEXT.md`; rare architectural decisions live under `docs/adr/`. See `docs/agents/domain.md`.

### Engineering workflow

For implementation, review, or bootstrap work, follow the tracer-bullet lifecycle and completion gates in `docs/agents/engineering.md`.
