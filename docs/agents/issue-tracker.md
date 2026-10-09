# Issue tracker

GitHub Issues in this repository are the durable work surface.

- A unit of implementation starts from an Issue, not from conversation state.
- Work the **frontier** only when the Issue is open and labeled `ready-for-agent`. That label is the executable authorization predicate; applying it asserts specification and blocker readiness, and removing it revokes autonomous continuation.
- Read the full Issue, comments, labels, linked PRs, and relevant Git history before changing code.
- Branches and PRs carry candidate implementation state; Issues carry work intent and completion criteria.
- An open PR linked by a closing reference owns active candidate work for its Issue regardless of branch name, but only while that Issue remains open and `ready-for-agent`; otherwise autonomous work stops.
- A model-authored handoff, STATUS file, or private todo list is not work state.
- Pull requests are not a separate request surface for triage by default.
- If there is no unblocked `ready-for-agent` Issue, do not invent implementation work. Reconstruct repository state and stop at the absence of an authorized frontier.

Completion is durable only when the Issue's acceptance criteria are satisfied by repository evidence and the canonical transition has occurred.
