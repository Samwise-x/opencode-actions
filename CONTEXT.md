# Domain language

**trajectory**: one logical development objective carried across disposable workers.

**attempt**: one bounded worker execution against a trajectory.

**base SHA**: canonical commit observed before an attempt begins.

**candidate SHA**: exact commit containing an attempt's proposed state transition.

**evidence**: machine-readable record binding an attempt, base SHA, candidate SHA, execution result, validation result, and GitHub run identity.

**qualified candidate**: candidate whose exact SHA passed deterministic repository validation.

**admission**: model-free transition that makes a qualified candidate canonical.

**lease**: exclusive, expiring trajectory ownership represented on a dedicated Git ref and updated with force-with-lease compare-and-swap.

**stale worker**: worker whose expected trajectory version or canonical base no longer matches current state.

**canonical state**: state reachable from the protected canonical branch. Model output alone is never canonical.

**reconstruction**: deriving the next worker's starting state from Git/GitHub state and SHA-bound evidence instead of preserving prior model context.
