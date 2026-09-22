---
name: firecrawl-interact
description: Interact with a Firecrawl-hosted browser session via the CLI when Firecrawl is selected for clicks, form fills, pagination, or post-scrape navigation. Supports persistent Firecrawl profiles, not the user's local browser login state. Account login, uploads, and submissions require explicit authorization; a failed scrape alone does not authorize them.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl interact

Interact with scraped pages in a live browser session. Scrape a page first, then use natural language prompts or code to click, fill forms, navigate, and extract data.

## When to use

- Content requires interaction: clicks, form fills, pagination, login
- `scrape` failed because content is behind JavaScript interaction
- You need to navigate a multi-step flow
- Last resort in the [Firecrawl CLI workflow](../firecrawl/SKILL.md#workflow): search → scrape → map → crawl → **interact**
- **Never use interact for web searches** — use `search` instead

## Authorization and session boundary

Use this workflow only when Firecrawl interaction is selected. It controls a hosted browser, not the user's existing local Chrome/Edge session; use authorized local browser tooling when that session is required. MCP is optional and exposes a different interface, so consult its actual schema rather than translating CLI flags blindly.

Before account login/authorization, file upload, form submission, posting, purchasing, or deletion, require explicit user authorization covering the destination and data/action. A scrape request or an available profile does not authorize these actions. Stop before an unapproved submission; read the [security rules](../firecrawl/rules/security.md).

## Quick start

```bash
# 1. Scrape a page for this authorized task (keep the scrape ID returned for this task)
firecrawl scrape "<url>"

# 2. Interact with the page using natural language
firecrawl interact --prompt "Click the login button"
firecrawl interact --prompt "Fill in the email field with test@example.com"
firecrawl interact --prompt "Extract the pricing table"

# 3. Or use code for precise control
firecrawl interact --code "agent-browser click @e5" --language bash
firecrawl interact --code "agent-browser snapshot -i" --language bash

# 4. Stop this task's session when done, passing the scrape ID owned by this task
firecrawl interact stop --scrape-id "<scrape-id>"
```

## Options

| Option                | Description                                       |
| --------------------- | ------------------------------------------------- |
| `--prompt <text>`     | Natural language instruction (use this OR --code) |
| `--code <code>`       | Code to execute in the browser session            |
| `--language <lang>`   | Language for code: bash, python, node             |
| `--timeout <seconds>` | Execution timeout (default: 30, max: 300)         |
| `--scrape-id <id>`    | Target a specific scrape. Prefer the ID returned for this authorized task; the remembered "last scrape" is not task-isolated |
| `-o, --output <path>` | Output file path                                  |

## Profiles

With authorization to persist hosted authentication state, use `--profile` on the scrape to retain cookies and localStorage across scrapes. This is a Firecrawl profile, not an import of the local user's browser profile. The login example below requires separate authorization for the account/login action:

```bash
# Session 1: Login and save state
firecrawl scrape "https://app.example.com/login" --profile my-app
firecrawl interact --prompt "Fill in email with user@example.com and click login"

# Session 2: Come back authenticated
firecrawl scrape "https://app.example.com/dashboard" --profile my-app
firecrawl interact --prompt "Extract the dashboard data"
```

Reconnect without saving profile changes (this does **not** make website actions read-only or prevent a form submission):

```bash
firecrawl scrape "https://app.example.com" --profile my-app --no-save-changes
```

## Tips

- Always scrape first — `interact` requires a scrape ID from a previous `firecrawl scrape` call
- Keep the scrape ID returned for this authorized task and pass it explicitly with `--scrape-id` on continuation, extraction, and stop calls; do not rely on the remembered last session, which is not isolated from concurrent or shared use
- Use `firecrawl interact stop --scrape-id "<scrape-id>"` to end only this task's session and free its resources; do not stop sessions you cannot attribute to this task
- For parallel work, scrape multiple pages and interact with each using its explicit `--scrape-id`

## See also

- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — try scrape first, escalate to interact only when needed
- [Firecrawl CLI search](../firecrawl/SKILL.md#search) — for web searches (never use interact for searching)
- [firecrawl-agent](../firecrawl-agent/SKILL.md) — AI-powered extraction (less manual control)
