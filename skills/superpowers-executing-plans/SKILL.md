---
name: executing-plans
description: Execute an approved implementation plan in the current or a new session, in bounded batches with review checkpoints.
---

# Executing Plans

## Overview

Load the approved plan, review critically, execute in batches, and report evidence at checkpoints. This works in the current session or a new session; a new session is optional, not required.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

Honor the user's chosen execution mode. Subagent-driven development is an option only when requested/appropriate and permitted, not a prerequisite. System/developer instructions, host permissions, scope, and stop requests always take precedence. Planning or implementation approval is not authorization to commit, merge, push, delete work, or change configuration.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns and implementation is approved, proceed without another signoff. Track tasks with a permitted host tool or an inline checklist; no particular task tool is required.

### Step 2: Execute Batches with Checkpoints

Use the plan's batch size, or up to 3 tasks per batch by default. For each task:
1. Mark as in progress
2. Follow the authorized steps, stopping if they conflict with scope or permissions
3. Run verifications as specified and retain the actual results
4. Mark completed only after verification

After each batch, report completed tasks, commands/results, remaining work, and blockers. A checkpoint is informational: continue an explicitly approved plan without asking "may I continue?" unless the user requested approval per batch, a new sensitive action needs authorization, or a blocker/material plan change arises. In a new session, load the same plan and recorded checkpoint before continuing; do not recreate already completed work.

### Step 3: Complete Development

After all tasks complete and verified, report the changes, test evidence, and current workspace/branch. Preserve work by default. If integration is requested, obtain or honor the user's explicit choice (keep as-is, commit, merge, push/PR, or cleanup), then use permitted host tools for only that action. Never automatically merge, push, or delete branches/worktrees. No archived completion skill is required.

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
