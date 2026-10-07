# Failure model

Canonical state fails closed.

| Failure | Result |
| --- | --- |
| Worker dies before publish | no canonical change; lease expires |
| OpenCode exits non-zero | diagnostic evidence only |
| Model changes Git HEAD | attempt rejected |
| Model leaves merge conflicts | attempt rejected |
| Model alters protected control plane | rejected before publication |
| Pre-publish validation fails | candidate is not published |
| Evidence upload fails | trajectory does not become qualified |
| Candidate CI pending | redundant frontier work is suppressed |
| Candidate CI fails | next fresh worker resumes persistent issue branch |
| PR head moves after evidence | seal/admission exact-SHA checks reject |
| Canonical base moves | admission rejects stale base |
| Two workers race | trajectory force-with-lease chooses one owner |
| Two admissions race | canonical force-with-lease chooses one writer |
| GitHub/API/network partial failure | no success inferred; next pass rereads canonical state |
| OpenCode session disappears | expected; session is not recovery state |
| Runner disappears | expected; Git/GitHub remain the recovery substrate |

A stale worker may still possess local files, but it cannot finalize a moved trajectory ref or land a stale canonical transition because both are compare-and-swap operations.
