# Engineering workflow

A fresh agent reconstructs the trajectory from repository and GitHub state. Previous model context is never required.

## Entry

Before a substantive change:

1. Read `AGENTS.md` and `CONTEXT.md`.
2. Read the full current `ready-for-agent` Issue and confirm its blockers are complete.
3. Read only applicable ADRs and the relevant Git history.
4. Trace the real execution path and search for existing capability before designing anything new.
5. Pin the current canonical `main` SHA as the fixed point.

Entry is complete when the agent can name the authorized work item, fixed point, affected execution path, existing validation surface, and observable completion criterion.

## Implementation

Implement one narrow, complete **tracer bullet** per Issue. Prefer existing repository capability and native platform behavior over new abstractions.

Use focused tests while working and run the complete deterministic validation surface before completion. A failure is evidence to fix or report; it is never reinterpreted as success.

## Review

Review the final diff against the pinned fixed point on two independent axes:

- **Standards** — repository instructions, domain vocabulary, applicable ADRs, and established conventions.
- **Spec** — the originating Issue's requirements, scope, and acceptance criteria.

Do not mix unrelated refactors into the feature diff. If review finds a defect, fix the root cause and rerun validation.

## Candidate transition

Commit coherent candidate state to one implementation branch and open one PR referencing the originating Issue. The worker stops at candidate state; canonical merge/admission belongs to the trusted repository boundary.

## Bootstrap invariant

The distribution has one public setup interface: plain `make`.

Any bootstrap capability must remain reachable through the default Make target. Do not introduce a second required setup command, installer state database, or parallel setup path.

The invariant is behavioral:

- a greenfield run creates the minimum substrate but leaves validation deliberately fail-closed until the repository defines real behavior in its Dagger `Validate` graph;
- every document referenced by the installed `AGENTS.md` exists after that first reconciliation;
- after the real validation graph is supplied, rerunning the same `make` completes reconciliation and an immediate repeat is a semantic no-op;
- valid brownfield repository-owned state is preserved;
- conflicts and missing authority fail closed.

`tests/test-bootstrap.py` is the executable regression boundary for this contract. A bootstrap change is incomplete until that test and the repository's full CI are green.
