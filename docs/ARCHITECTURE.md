# Architecture

## Ownership

OpenCode owns model execution, tool execution, delegation, compaction, and runtime event emission.

GitHub owns triggers, identities, Issues, pull requests, refs, commit history, checks, and workflow artifacts.

Repository policy owns trajectory selection, cross-run single-writer coordination, evidence qualification, protected paths, and canonical admission.

## Core invariant

OpenCode may mutate candidate state. OpenCode must never decide that candidate state became canonical truth.

The model process therefore never receives the credential used for final admission.

## Reconstructable trajectory

A fresh worker reconstructs from canonical main, open GitHub Issues, open candidate PRs, candidate refs, and current CI state. The trusted wrapper selects one frontier before model execution and injects that issue/PR context into the prompt. An Issue is autonomous work only while it is open and labeled `ready-for-agent`; removing that label revokes continuation even when a linked PR already exists.

OpenCode session IDs remain useful evidence but are not recovery dependencies.

## Single writer

opencode/trajectory contains a tiny JSON coordination record. Acquisition and finalization update the ref with Git force-with-lease. An unexpired lease blocks another frontier worker.

The state also records the last base/candidate/issue/PR. If the previous candidate is still validating, or has passed checks and is waiting for admission, a new worker does not create competing progress. Failed qualification or a moved canonical base permits reconstruction.

This branch is coordination metadata, not system truth. Canonical truth remains protected main.

## Candidate continuity

A new autonomous Issue receives the conventional persistent branch:

    opencode/issue-<issue-number>

Branch naming is not identity. GitHub's native closing-Issue relationship binds an existing open PR to its Issue, so a successor resumes that linked candidate regardless of branch name. A successor fetches the linked branch, merges current canonical main without committing, and lets the fresh model resolve any conflict and continue the same work. Publication first revalidates the live trajectory lease and then uses force-with-lease against the branch head observed before model execution, so a stale worker cannot publish after losing single-writer authority or overwrite a newer candidate.

## Evidence chain

The worker uploads evidence.json plus raw OpenCode NDJSON, stderr, diff, status, and lightweight validation output. Final worker evidence binds attempt, issue, base SHA, candidate SHA, model/agent, OpenCode session IDs, and hashes of raw evidence.

Independent candidate jobs run the canonical Nix/Dagger graph and security checks. Autonomous candidates must also prove the live PR still closes the same open `ready-for-agent` Issue identified by their commit evidence. Only after both jobs succeed does a trusted job create qualification.json, bind it to the worker evidence hash, exact candidate/base/PR, validation workflow run, and required jobs, then keylessly sign it with Cosign.

Admission verifies the Sigstore workflow identity, the exact recorded successful validation run and required jobs, and the current GitHub state again.

## Admission serialization point

The final transition is:

    qualification is authentic
    AND candidate == PR head
    AND exact qualified validation run(candidate, PR, workflow) == success
    AND current main == qualified base
    AND candidate descends from qualified base
    AND candidate changes no protected path
    THEN
        git push --force-with-lease=main:<qualified-base> <candidate>:main
    ELSE
        reject

Because candidate ancestry is required, the resulting canonical update is a fast-forward. Force-with-lease supplies the compare-and-swap guard against concurrent movement of main.

## Runtime containment

OpenCode permissions are tool policy, not operating-system isolation. The model job therefore layers:

- no GitHub mutation token in the OpenCode environment;
- strict CargoWall with sudo lockdown;
- decoy GitHub Actions command files;
- protected file policy;
- repository-owned OpenCode permission rules and runtime guard plugin;
- action-byte hash before/after model execution;
- HEAD/conflict checks;
- process cleanup after the model exits;
- complete Git config replacement before privileged Git operations;
- absolute trusted executable paths in privileged phases.

The deterministic wrapper, not the model, performs GitHub mutation.

## Model/provider replaceability

The durable contract names only the OpenCode model identifier and provider credentials. A worker can use a different frontier model without changing trajectory, evidence, CI, or admission semantics.

## Release identity and compounding

`release.json` names one immutable runtime commit for every distributed self-reference. Bootstrap renders managed workflows from that identity, upgrades byte-identical known generated predecessors, and refuses unknown drift. Runtime-bearing changes on canonical main are detected deterministically; the self-heal workflow may propose a release-promotion PR, but canonical truth still requires normal review and merge authority.
