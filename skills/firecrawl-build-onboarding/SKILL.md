---
name: firecrawl-build-onboarding
description: Get Firecrawl credentials and SDK setup into a project. Use when an application needs `FIRECRAWL_API_KEY`, when an agent should add Firecrawl to `.env`, when the user wants to authenticate Firecrawl for app code, or when choosing the first SDK and docs for a new Firecrawl integration. This skill includes its own browser auth flow, so it does not depend on the website onboarding skill.
license: ISC
metadata:
  author: firecrawl
  version: "0.1.0"
  homepage: https://www.firecrawl.dev
  source: https://github.com/firecrawl/skills
inputs:
  - name: FIRECRAWL_API_KEY
    description: Firecrawl API key used for hosted Firecrawl API requests.
    required: true
  - name: FIRECRAWL_API_URL
    description: Optional base URL for self-hosted Firecrawl deployments.
    required: false
references:
  - references/auth-flow.md
  - references/sdk-installation.md
  - references/project-setup.md
---

# Firecrawl Build Onboarding

Use this skill for the application-integration path from Firecrawl's onboarding flow.

## Setup boundary

Inspect the project's existing SDK and credential setup first. Reuse what is available; app integration does not require installing CLI skills or MCP. Install a project SDK only within the authorized dependency scope. Do not automatically run all-in-one initialization, global installs/updates, browser login, or account creation.

Before starting an account auth flow, get explicit authorization and let the human complete sign-in/consent. Before saving credentials, confirm the project/environment and secret destination; do not print keys or place them in source control. A live smoke test, private-file upload, or form submission needs authorization covering that action and data.

## Use This When

- a project needs `FIRECRAWL_API_KEY`
- the user wants Firecrawl wired into `.env`
- you are adding Firecrawl to an app for the first time
- you need to choose the first SDK or REST path

If the human still needs to sign up, sign in, or authorize access in the browser, use the auth flow reference in this skill.

## Quick Start

If the user already has an API key, place it in `.env`:

```dotenv
FIRECRAWL_API_KEY=fc-...
```

If the project is self-hosted, also set:

```dotenv
FIRECRAWL_API_URL=https://your-firecrawl-instance.example.com
```

Then decide which integration path applies:

- **Fresh project** -> choose the target stack, install the SDK, add the first Firecrawl call, and run a smoke test
- **Existing project** -> inspect the repo first, then integrate Firecrawl where the project already handles third-party APIs and env vars

## What Do You Need?

| Task | Reference |
|---|---|
| **Run the browser auth flow and save `FIRECRAWL_API_KEY`** | [references/auth-flow.md](references/auth-flow.md) |
| **Install the right SDK** | [references/sdk-installation.md](references/sdk-installation.md) |
| **Put credentials into `.env` or project config** | [references/project-setup.md](references/project-setup.md) |
| **Choose the right endpoint after setup** | [Endpoint selection](#endpoint-selection) |
| **Need live web tooling during this task** | [Firecrawl CLI](../firecrawl/SKILL.md), if installed and authorized |
| **Start implementation from a known URL** | `/scrape` in the [official language docs](#docs-source-of-truth) |
| **Start implementation from a query** | `/search` in the [official language docs](#docs-source-of-truth) |

## Endpoint selection

- A query without a URL: `/search` to discover sources.
- A known page: `/scrape` to extract its content directly; provider discovery is not required for ordinary page reading.
- Structured records across multiple entities: when the installed SDK/API supports provider discovery, inspect a matching contract before implementing execution. Follow its required inputs, result field, and pagination; do not assume a generic `records` response. If unsupported or no suitable provider exists, choose the existing page or agent workflow that fits the authorized task.
- Find URLs within one site: `/map`; bulk content from a scoped section: `/crawl`.
- Clicks or pagination after extraction: `/interact`; use [firecrawl-build-interact](../firecrawl-build-interact/SKILL.md) for product action boundaries.

Use the official language documentation below for SDK method names, request schemas, and responses. CLI flags and optional MCP tool parameters are different interfaces, not SDK signatures. Verify provider support in the project's installed SDK before writing code; a newer CLI example is not a reason to upgrade it silently. The bundled CLI [search](../firecrawl/SKILL.md#search) and [scrape](../firecrawl-scrape/SKILL.md) guides are usable for one-off web work, not substitute SDK references.

## Docs (Source of Truth)

Read the source-of-truth page for your project language for SDK usage, schemas, and examples:

- **Node / TypeScript**: [docs.firecrawl.dev/agent-source-of-truth/node](https://docs.firecrawl.dev/agent-source-of-truth/node)
- **Python**: [docs.firecrawl.dev/agent-source-of-truth/python](https://docs.firecrawl.dev/agent-source-of-truth/python)
- **Rust**: [docs.firecrawl.dev/agent-source-of-truth/rust](https://docs.firecrawl.dev/agent-source-of-truth/rust)
- **Java**: [docs.firecrawl.dev/agent-source-of-truth/java](https://docs.firecrawl.dev/agent-source-of-truth/java)
- **Elixir**: [docs.firecrawl.dev/agent-source-of-truth/elixir](https://docs.firecrawl.dev/agent-source-of-truth/elixir)
- **cURL / REST**: [docs.firecrawl.dev/agent-source-of-truth/curl](https://docs.firecrawl.dev/agent-source-of-truth/curl)

## After Setup

Once the key is present:

1. decide whether this is a fresh project or an existing codebase
2. ask what Firecrawl should do in the product
3. pick the narrowest endpoint that matches that behavior
4. read the source-of-truth page for the project language before writing code
5. add the SDK or REST call in code
6. run a small in-scope live smoke test only if authorized; otherwise report that live access is unverified
7. use the [official language docs](#docs-source-of-truth) and [build-interact](../firecrawl-build-interact/SKILL.md) when applicable
8. for one-off web work, use the existing [Firecrawl CLI guide](../firecrawl/SKILL.md) if the CLI is available; do not auto-install tools
