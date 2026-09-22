---
name: code-review
description: Review committed changes since a pinned base or work-in-progress changes along two axes — repository Standards and originating Spec. Use parallel reviewers when permitted and available, otherwise disclosed separate passes over the same snapshot. Use for branch, PR, WIP, or "review since X" requests.
---

Two-axis review of an explicitly chosen change scope:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating issue / PRD / spec?

Both axes use the same captured input. Run independent parallel reviews only when delegation is permitted and tools are available; otherwise perform two separate passes and disclose that they were not independent agents. A review does not authorize commits, uploads, fixes, or changes to tracker/tool configuration.

Use `docs/agents/issue-tracker.md` if present. If absent, request the tracker/spec source or use a user-provided or verified local source. No setup command is bundled or required; never invoke a missing setup skill or invent tracker configuration.

## Process

### 1. Choose scope and pin immutable inputs

- **WIP / working-tree review:** use `git diff HEAD` to include staged plus unstaged tracked changes, and `git status --short` to identify untracked paths. Expand untracked directories and explicitly read each in-scope untracked file with the host's read tool; diff alone does not include them. Pin `BASE_SHA=$(git rev-parse --verify 'HEAD^{commit}')` and capture the equivalent `git diff "$BASE_SHA"` output once. Do not use three-dot for WIP. Report unreadable/binary/excluded files and staged/unstaged changes that cancel out in the net diff.
- **Committed branch / PR / "since X" review:** resolve `BASE_SHA=$(git rev-parse --verify '<base>^{commit}')`, `HEAD_SHA=$(git rev-parse --verify 'HEAD^{commit}')`, and `MERGE_BASE_SHA=$(git merge-base "$BASE_SHA" "$HEAD_SHA")`. The intended command is `git diff <base>...HEAD`; execute the pinned equivalent `git diff "$BASE_SHA"..."$HEAD_SHA"` and capture `git log "$BASE_SHA".."$HEAD_SHA" --oneline`. If the base is unknown, ask rather than assuming main/master.
- **Scope conflict:** untracked, staged, and unstaged files are not part of a committed comparison. Report their presence with `git status --short` but exclude them unless the user also requests WIP; in that case produce a separately labeled WIP review. Do not silently add local files to a PR review or drop them from WIP. If intent is ambiguous, state/confirm the chosen mode before reviewing.

Pass the same immutable base SHA, pinned head/merge-base where applicable, captured diff, commit list, and WIP untracked contents to both reviews. WIP is mutable: capture contents once, note the capture time, and check status/diff/content hashes again before reporting. If they changed, invalidate the affected review or label it stale; never mix snapshots. For committed mode read file context from the pinned commit, not a dirty working tree.

Validate refs and scope before dispatch. An empty tracked diff with in-scope untracked files is not an empty WIP review. If the entire selected scope is empty, report no changes rather than spawning reviews.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the selected commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.) — fetch using the verified tracker source and permitted host tools; use `docs/agents/issue-tracker.md` only if it exists.
2. A path the user passed as an argument.
3. A PRD/spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent will skip and report "no spec available".

### 3. Identify the standards sources

Anything in the repo that documents how code should be written, such as `CODING_STANDARDS.md` or `CONTRIBUTING.md`.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below — a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation — and, like any standard here, skip anything tooling already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name** — a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps** — the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches** — the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 4. Run both review axes

If the host permits delegation, send two parallel review calls using the available agent tools. Otherwise run separate Standards and Spec passes yourself. In either case use the identical captured inputs from step 1, not independently resolved moving refs.

**Standards sub-agent prompt** — include:

- The selected mode, immutable base SHA and any pinned head/merge-base SHA, captured diff and commit list, plus WIP untracked paths/contents and exclusions. Review this snapshot; do not rerun moving refs.
- The list of standards-source files you found in step 3, **plus the smell baseline from step 3** pasted in full — the sub-agent has no other access to it.
- The brief: "Report — per file/hunk where relevant — (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls — documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** — include:

- The identical selected mode, immutable SHA values, captured diff/commit list, and WIP untracked contents/exclusions supplied to the Standards review.
- The path or fetched contents of the spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note this in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings — the two axes are deliberately separate (see _Why two axes_).

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes — that's the reranking the separation exists to prevent.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
