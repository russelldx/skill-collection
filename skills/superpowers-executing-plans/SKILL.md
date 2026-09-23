---
name: executing-plans
description: Execute an approved implementation plan in the current or a new session, in bounded batches with review checkpoints.
---

# Executing Plans

## Overview

Execute the approved plan directly, task by task, without dispatching a new implementer and reviewer for every task. Review critically, execute in batches, and report evidence at checkpoints. This works in the current session or a new session; a new session is optional, not required.

Direct execution avoids repeated context setup and suits tightly connected tasks or work where delegation is unnecessary or unavailable. It does not remove testing or final review. If the user chose subagent-driven execution and it is supported, honor that choice rather than silently switching modes.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

Honor the user's chosen execution mode. Subagent-driven development is an option only when requested/appropriate and permitted, not a prerequisite. System/developer instructions, host permissions, scope, and stop requests always take precedence. Planning or implementation approval is not authorization to commit, merge, push, delete work, or change configuration.

## The Process

### Step 1: Load and Review Plan
1. Read the approved plan and its existing requirements source. Report unavailable material instead of inventing a spec or treating a summary as the exact requirement.
2. Review global constraints, shared files, and producer/consumer interfaces; identify contradictions before starting dependent tasks.
3. Resolve implementation details within the approved scope. Raise material requirements changes, missing information, or authorization conflicts with the user rather than making a unilateral ruling.
4. If implementation is approved and no blocker remains, proceed without another signoff. Track tasks with a permitted host tool or an inline checklist; no particular tool or ledger file is required.
5. On resumption, use the existing checkpoint and inspect relevant file/test evidence before repeating work. Do not recreate completed tasks merely because the conversation was compacted; write recovery notes only where authorized.

### Step 2: Execute Batches with Checkpoints

Use the plan's batch size, or up to 3 tasks per batch by default. For each task:
1. Mark as in progress and load its exact requirements, interfaces, and acceptance criteria.
2. Follow the authorized steps, stopping if they conflict with scope or permissions.
3. Run the specified verification and compare actual output with expected behavior. Keep the command, result, and any missing coverage; a clean diff or an exit code alone does not prove the feature works.
4. Diagnose failures before changing the code or plan. Record any in-scope deviation with its reason; obtain approval for changes outside that scope.
5. Mark completed only after verification; failed checks, unknown results, and unresolved requirements remain incomplete.

After each batch, report completed tasks, commands/results, remaining work, and blockers. A checkpoint is informational: continue an explicitly approved plan without asking "may I continue?" unless the user requested approval per batch, a new sensitive action needs authorization, or a blocker/material plan change arises. In a new session, load the same plan and recorded checkpoint before continuing; do not recreate already completed work.

### Step 3: Review the Integrated Result

Review the whole implementation against the requirements, global constraints, shared interfaces, and Review Focus, not only the last task. When an independent reviewer is available and delegation is permitted, provide the complete in-scope snapshot plus verification evidence. Otherwise perform a separate self-review pass and disclose that it was not independent.

For uncommitted work, include the in-scope staged and unstaged changes and relevant untracked files; `HEAD` alone does not contain the work. All review passes must cover the same snapshot. Do not create a commit, ledger, or review package merely to satisfy a tool that assumes one exists; use the permitted review mechanism.

Verify any fixes and check that they did not invalidate other results. Keep review/fix cycles bounded to two rounds before escalating unresolved issues to the user. Do not mark unresolved correctness or authorization issues complete or use a passing test to justify silently dropping a requirement.

### Step 4: Complete Development

After all tasks complete and verified, report the changes, test evidence, review coverage, and current workspace/branch. Preserve work by default. If integration is requested, obtain or honor the user's explicit choice (keep as-is, commit, merge, push/PR, or cleanup), then use permitted host tools for only that action. Never automatically merge, push, or delete branches/worktrees. No archived completion skill is required.

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Related workflows (not additional authorization gates):**
- **superpowers:using-git-worktrees** - Optional, user-authorized isolation; in-place execution is valid
- **superpowers:writing-plans** - Creates the plan this skill executes
- Completion uses the explicit user choice and host tools described in Step 3; no automatic merge/push/delete
