# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes and delegation is permitted.** Otherwise perform a disclosed separate review pass.

Use [the bundled review template](../superpowers-requesting-code-review/code-reviewer.md), adapting its commit-range instructions to the captured scope below. Never create a commit merely to review uncommitted work.

```
Available permitted review tool:
  DESCRIPTION: [task summary, from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan source]
  REVIEW_MODE: [WIP or committed]
  BASE_SHA: [immutable base commit]
  HEAD_SHA: [pinned commit for committed mode; not a WIP snapshot]
  SNAPSHOT: [same captured diff, contextual files, exclusions, and WIP untracked
             contents used for spec review; include pre-task content when shared
             WIP already existed so only this task's changes are attributed to it]
```

For WIP capture `git diff HEAD` plus `git status --short`, explicitly read in-scope untracked files, and check for changes before reporting. For committed mode use pinned `base...HEAD` and commit content; exclude local WIP. Do not substitute an empty commit diff for uncommitted edits.

**In addition to standard code quality concerns, the reviewer should check:**
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files? (Don't flag pre-existing file sizes — focus on what this change contributed.)

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
