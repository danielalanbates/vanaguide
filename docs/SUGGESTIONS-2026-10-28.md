# Server-Safe suggestions: validation and automation

Copyright © 2026 Daniel Bates / Bates LLC. All rights reserved.
[batesai.org](https://batesai.org) · help@batesai.org

The suggestion importer was present in PR #22 (`suggested-changes`), not in the guide's
`master` or current `gear-guide` working copy. The folder currently contains its README only;
there are no player submissions to apply in this checkout. Do not describe an unmerged
workflow as active on the default branch.

## Fixes

| Previous behavior | Corrected behavior |
| --- | --- |
| Any matching area/id could attach a giver | The exported quest/mission title must also match |
| Only literal `zone =` / `npc =` protected existing data | Any spacing is protected, including a partially located entry |
| First conflicting filename won | Conflicting proposals are skipped for review; identical duplicates are allowed |
| Location text could be confused with string contents | Quoted text is masked before reading fields; only static export strings are decoded |
| Workflow ran only when suggestions changed | It also rechecks regenerated quest/mission files and importer changes |
| PR validation requested write permissions | Validation is read-only; only the trusted `master` proposal job requests writes |

The importer never executes Lua. It adds only `zone` and `npc`, never overwrites existing
location fields, and leaves the data byte-identical when no additions are needed. Existing
NPC/zone data is preserved even if a proposed correction disagrees; corrections need a
separate reviewed edit. Names, known locations and conflicting suggestions are not guessed.

## Verification

- 12 Python regression tests pass, including quest/mission namespace separation, stale ids,
  escaped apostrophes, invalid values, conflicting proposals and repeated application.
- Running those fixtures against the preceding importer produces 9 failures, confirming
  they catch the reported behavior rather than only reproducing the new implementation.
- `luajit tools/test_offline.lua`: 1,240 assertions pass, zero failures, on the PR #22 base.
  This count is for this branch; the newer gear branch has additional assertions.
- `actionlint` passes the workflow (shellcheck/pyflakes integrations disabled).
- GitHub Actions validation also passed on [PR #24](https://github.com/danielalanbates/vanaguide/pull/24)
  ([run](https://github.com/danielalanbates/vanaguide/actions/runs/40805631146)); the proposal
  job correctly skipped for the PR event.
- Running the importer on the actual folder reports zero proposals and leaves data unchanged.
- No game app, hosted server, user character or installed addon was used for these checks.

## Activation and continuation

Merge the validated importer/workflow changes with PR #22 before expecting default-branch
automation. Keep data proposals as reviewable PRs; this workflow never merges them or
publishes an application release. A source-data improvement reaches shipped guide snapshots
only when the beta app is rebuilt and later passes the public release gates.

The repository's Actions settings currently report `can_approve_pull_request_reviews=false`,
which also prevents `GITHUB_TOKEN` from creating proposal PRs. Enabling the repository setting
“Allow GitHub Actions to create and approve pull requests” is required for automatic proposals;
keep default token permissions read-only and grant writes only in the proposal job. No secret
or personal token needs to be committed. See [GitHub's setting documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#preventing-github-actions-from-creating-or-approving-pull-requests).

The trusted push trigger is limited to `master`, so the generated `apply-suggestions` branch
cannot create a push loop. PR runs only validate. A manual run also proposes changes only
when its selected ref is `master`. After activation, check the workflow result; a successful
no-change run proves neither a real proposal creation nor new quest coverage.
