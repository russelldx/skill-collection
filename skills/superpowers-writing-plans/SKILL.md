---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Commits only when explicitly requested.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** Execution may stay in the current session or use a new session; neither requires a worktree. Honor the user's workspace preference and host permissions. Use `superpowers:using-git-worktrees` only when isolation is wanted and authorized.

**Save plans only when a file is requested:** default `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`; user location preferences override it. Otherwise provide the plan inline. An already detailed approved plan need not be rewritten or signed off again. Skill guidance never overrides system/developer instructions or grants permission for commits, publishing, deletion, or configuration changes.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

Make a task the smallest independently verifiable deliverable, not every small edit or shell command. Include the setup, documentation, and tests needed by that deliverable in the same task. Split where one result can meaningfully pass acceptance while another fails. Group small same-shape changes when they share a test/review boundary; keep work requiring different judgments or interfaces separate.

Name producer/consumer interfaces and file overlap explicitly so execution can respect dependencies instead of assuming all tasks are parallel-safe. Steps inside each task can remain bite-sized.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Review diff; commit only if requested" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** Honor the approved execution mode: superpowers:executing-plans in this or a new session, or permitted subagent-driven development. Use the plan's batch size (default up to 3 tasks), report evidence at checkpoints, and do not require repeat signoff after explicit approval. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Requirements source:** [Existing spec path or the approved requirements in the conversation; do not invent a spec file]

---
```

## Global Constraints and Review Focus

Carry binding requirements into the plan: exact values and formats, shared interfaces, data boundaries, permitted files/actions, and explicit non-goals. Distinguish required behavior from implementation suggestions. A requirement to implement a feature does not authorize a new dependency, permission change, or external action outside the approved scope.

For each task that consumes an earlier result, state what is produced and what the consumer expects, including names, types, and failure behavior. Resolve contradictions before dependent work starts; ask the user when the resolution changes requirements or authorization.

List up to five highest-impact input classes or failure modes that the current tests would miss. Link each to its owning task and concrete verification, adding the needed tests to that task. An empty Review Focus means coverage was checked and no gaps were found, not that review was skipped. Keep this in the existing plan or conversation; do not create extra documents unless requested.

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Review changes; commit only if explicitly requested**

```bash
git diff HEAD -- tests/path/test.py src/path/file.py
git status --short
```

Read in-scope untracked files separately. If the user asked for a commit, use the host's commit workflow without bypassing hooks/signing; otherwise leave changes uncommitted.
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD; commit only on explicit request

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

**4. Review Focus:** Does each listed failure mode have a concrete verification in its owning task? Check that global constraints and cross-task interfaces also have coverage; do not leave the list as risks with no acceptance check.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Execution Handoff

After preparing the plan, honor any execution choice and implementation approval already given. Do not force another signoff for an explicitly approved detailed spec/plan. For planning-only requests, return the plan and wait for implementation authorization.

If a choice is still needed, recommend an approach using the plan's interface coupling, task size, and the cost of a missed defect:
1. **Direct execution (current session or optional new session):** use `superpowers:executing-plans`, with the plan's batch size or up to 3 tasks per batch by default. Prefer this when context is shared heavily or delegation overhead exceeds its benefit.
2. **Subagent-driven:** use `superpowers:subagent-driven-development` only if delegation is permitted and suitable, with task-scoped spec and quality review plus final integrated review. Group small same-shape work rather than allocating a worker per mechanical step.

Honor a supplied choice without asking again. Both modes report completed tasks, test commands/results, remaining work, and blockers at batch checkpoints. Checkpoints are informational, not mandatory extra signoffs after explicit approval. Pause only for user-requested gates, blockers, material plan changes, new sensitive actions, or a stop request. A new session loads the same plan and last checkpoint; it is never required just to execute a plan.
