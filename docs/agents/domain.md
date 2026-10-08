# Domain docs

This repository uses a **single-context** domain layout.

- `CONTEXT.md` is the canonical domain vocabulary. Keep implementation details, work logs, and specifications out of it.
- `docs/adr/` is reserved for architectural decisions that are expensive to reverse, surprising without history, and the result of a real tradeoff. Do not create an ADR when those conditions are absent.
- Code, configuration, tests, Git history, and executable help are environment truth. Rediscover cheap facts from those sources instead of caching them in prose.
- Read only ADRs relevant to the area being changed.

When terminology is ambiguous, resolve the term before implementation and update `CONTEXT.md` when the resolved vocabulary affects execution.
