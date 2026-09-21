> **CONSOLIDATED — NON-EXECUTABLE REFERENCE.** This is not a separate skill. Bounded full-file reading is an opt-in mode of `claude-mem-smart-explore`, not an automatic requirement for unfamiliar repositories. System/developer instructions, host permissions, and user scope remain authoritative.

---
name: learn-codebase
description: Reference technique for explicitly requested full-file reading within a declared scope and file/token budget.
---

# Learn Codebase

Read selected source files in full only when the user explicitly requests full reading. First state the included paths, exclusions, maximum files and token budget, and stopping condition using the primary skill's full-read mode. Use structural exploration by default. Stop at the first budget limit and report partial coverage; never silently expand scope or claim to have read files that were only outlined.

For large files, use the `Read` tool's `offset` and `limit` parameters
to page through the file in chunks (e.g. `offset: 1, limit: 500`, then
`offset: 501, limit: 500`).

## Note for Reviewers

Full reading can help build context, but has a real cost. Report files and approximate tokens consumed, unread paths, and any partially read file. Stop when the agreed scope is covered, the question is answered, the file/token budget is exhausted, a permission boundary is reached, or the user stops the task. Further reading requires renewed scope/budget authorization.
