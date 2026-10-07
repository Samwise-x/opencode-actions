# Agent execution contract

Work only inside the checked-out repository. Read repository context and ADRs when present.

Never push, merge, force-update, or mutate the canonical branch. Produce candidate state only.

Run deterministic validation before completion. Do not weaken, skip, delete, or reinterpret a failing check.

Do not read secret files, external directories, or credentials. Do not print environment secrets.

Prefer existing structure and dependencies. Do not create parallel state files, handoff journals, or speculative abstractions.

A successful attempt ends with coherent candidate state. Canonical admission belongs to deterministic repository machinery, not the model.
