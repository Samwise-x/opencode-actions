# Triage labels

Every triaged Issue carries exactly one category role and one state role.

## Category roles

- `bug` — existing behavior is broken.
- `enhancement` — new behavior or an improvement.

## State roles

- `needs-triage` — maintainer evaluation is required.
- `needs-info` — work is waiting on missing information.
- `ready-for-agent` — the work is fully specified and may be executed by a fresh agent.
- `ready-for-human` — implementation or admission requires human judgment/authority.
- `wontfix` — the work will not be actioned.

The frontier is the set of `ready-for-agent` Issues whose blockers are complete. State labels are control-plane state, not decorative metadata.
