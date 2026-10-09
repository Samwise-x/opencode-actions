# Triage labels

Every triaged Issue carries exactly one category role and one state role.

## Category roles

- `bug` — existing behavior is broken.
- `enhancement` — new behavior or an improvement.

## State roles

- `needs-triage` — maintainer evaluation is required.
- `needs-info` — work is waiting on missing information.
- `ready-for-agent` — the work is fully specified, its blockers are resolved, and autonomous execution is authorized. Removing this label revokes that authorization even when a candidate PR already exists.
- `ready-for-human` — implementation or admission requires human judgment/authority.
- `wontfix` — the work will not be actioned.

The frontier is the set of open `ready-for-agent` Issues. The label itself is the durable assertion that specification and blocker requirements are satisfied; state labels are control-plane state, not decorative metadata.
