---
name: firecrawl
description: Search, scrape, crawl, download, and interact with websites via the Firecrawl CLI when Firecrawl is selected for the task. Provides CLI workflows for web search and extraction; does not require replacing other suitable search, fetch, or browser tools. Local document parsing requires explicit Firecrawl/cloud-upload authorization. Do not trigger merely for local file operations, git commands, deployments, or unrelated code editing.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# Firecrawl CLI

Search, scrape, and interact with the web when Firecrawl is selected. Returns clean markdown optimized for LLM context windows.

These are **CLI workflows**, not requirements to install or use Firecrawl MCP. MCP is an optional, separate interface: use its exposed tool schemas and limits, not CLI flags. For the user's existing local browser session, prefer an authorized local browser tool or web-access; Firecrawl hosted sessions/profiles do not inherit local Chrome/Edge login state.

Run `firecrawl --help` or `firecrawl <command> --help` for full option details. Read [security rules](rules/security.md) before sending private data, uploading files, or performing account actions. Tool availability and credentials do not grant permission for login, submission, or upload.

For application integration, start with [firecrawl-build-onboarding](../firecrawl-build-onboarding/SKILL.md) and its language-specific official documentation links. For product browser actions, use [firecrawl-build-interact](../firecrawl-build-interact/SKILL.md).

## Prerequisites

Start with `firecrawl --version` and `firecrawl --help`. Confirm that a command appears in the installed command list and that its own help documents the required options. An unknown command printing the general help is not evidence that the command exists.

Provider discovery and execution require support for the relevant `search`, `list`, and `scrape --options` forms. Do not assume an older CLI supports them because current upstream documentation does. If unsupported, report the limitation and use the ordinary page workflow where it still answers the request; changing interfaces or upgrading dependencies needs appropriate authorization. For a selected MCP or SDK interface, check its actual schema or versioned documentation instead of translating CLI flags.

When service access is authorized, `firecrawl --status` checks authentication, concurrency, and remaining credits. Bound parallel work by both the reported concurrency and the user's scope/budget. If setup is missing, see [rules/install.md](rules/install.md); do not automatically install, upgrade, or log in.

Status is not end-to-end verification. If the user authorizes a live smoke test, use one small in-scope request and report the actual result; do not fetch an unrelated site automatically or install/authenticate as a side effect of diagnosis.

## Search

Use `search` when Firecrawl is selected and no exact URL is known. Quote the query, keep the limit small, and inspect results before expanding scope:

```bash
mkdir -p .firecrawl
firecrawl search "query" --limit 3 --json -o .firecrawl/search.json
# Include page content when needed; avoid re-scraping these results
firecrawl search "query" --scrape --limit 3 -o .firecrawl/search-content.json
```

Use `firecrawl search --help` for the installed CLI's options. For code integration rather than CLI use, see [onboarding endpoint selection](../firecrawl-build-onboarding/SKILL.md#endpoint-selection).

### Structured provider discovery

For structured records across several entities or pages, first check whether the selected interface can discover a suitable provider or workflow. In CLI versions that support this path, normal search can return web results and tool matches; `firecrawl search alexandria "<data needed>"` searches the tool catalogue. Do not use that form when the installed help does not document it.

If the returned contract is incomplete, inspect only the selected provider/capability with the supported `list` command. Discovery is not execution or authorization. Compare the contract's coverage, inputs, costs, and side effects with the request; a domain match alone is insufficient. See [provider execution](../firecrawl-scrape/SKILL.md#structured-provider-execution) for the next step. Reuse an already inspected contract rather than repeating discovery.

If plain web results already answer the question, use them. For a known page, scrape directly. If provider discovery is unavailable or no match fits, say so and continue with the applicable ordinary page or agent workflow within the original scope.

## Workflow

Follow this escalation pattern:

1. **Search** - No specific URL yet. Find pages, answer questions, discover sources; inspect suitable provider contracts for structured data when supported.
2. **Scrape** - Have a URL. Extract its content directly. A selected provider capability uses the separate, supported execution form after contract and authorization checks.
3. **Map + Scrape** - Large site or need a specific subpage. Use `map --search` to find the right URL, then scrape it.
4. **Crawl** - Need bulk content from an entire site section (e.g., all /docs/).
5. **Interact** - Scrape first, then interact with the page (pagination, modals, form submissions, multi-step navigation).

| Need                        | Command               | When                                                      |
| --------------------------- | --------------------- | --------------------------------------------------------- |
| Find pages on a topic       | `search`              | No specific URL yet                                       |
| Structured provider data   | `search` → `list` → `scrape` | Only with supported commands and an inspected matching contract |
| Get a page's content        | `scrape`              | Have a URL, page is static or JS-rendered                 |
| Find URLs within a site     | `map`                 | Need to locate a specific subpage                         |
| Bulk extract a site section | `crawl`               | Need many pages (e.g., all /docs/)                        |
| AI-powered data extraction  | `agent`               | Need structured data from complex sites                   |
| Interact with a page        | `scrape` + `interact` | Content requires clicks, form fills, pagination, or login |
| Download a site to files    | `download`            | Save an entire site as local files                        |
| Parse a local file          | `parse`               | Only after explicit authorization to upload the selected file to Firecrawl |

For detailed command reference, run `firecrawl <command> --help`.

**Scrape vs interact:**

- Use `scrape` first. It handles static pages and JS-rendered SPAs.
- Use `scrape` + `interact` when you need to interact with a page, such as clicking buttons, filling out forms, navigating through a complex site, infinite scroll, or when scrape fails to grab all the content you need.
- Never use interact for web searches - use `search` instead.

**Avoid redundant fetches:**

- `search --scrape` already fetches full page content. Don't re-scrape those URLs.
- Check `.firecrawl/` for existing data before fetching again.

## When to Load References

- **Searching the web or finding sources first** -> [Search](#search) (`firecrawl search`)
- **Scraping a known URL** -> [firecrawl-scrape](../firecrawl-scrape/SKILL.md)
- **Finding URLs on a known site** -> [firecrawl-map](../firecrawl-map/SKILL.md)
- **Bulk extraction from a docs section or site** -> [firecrawl-crawl](../firecrawl-crawl/SKILL.md)
- **AI-powered structured extraction from complex sites** -> [firecrawl-agent](../firecrawl-agent/SKILL.md)
- **Clicks, forms, login, pagination, or post-scrape browser actions** -> [firecrawl-interact](../firecrawl-interact/SKILL.md)
- **Downloading a site to local files** -> [firecrawl-download](../firecrawl-download/SKILL.md)
- **Parsing a local file after explicit cloud-upload authorization** -> [firecrawl-parse](../firecrawl-parse/SKILL.md); otherwise prefer local document tools
- **Install, auth, or setup problems** -> [rules/install.md](rules/install.md)
- **Output handling and safe file-reading patterns** -> [rules/security.md](rules/security.md)
- **Application credentials, SDK setup, or endpoint selection** -> [firecrawl-build-onboarding](../firecrawl-build-onboarding/SKILL.md)
- **Product code needing post-scrape actions** -> [firecrawl-build-interact](../firecrawl-build-interact/SKILL.md)

## Output & Organization

Unless the user specifies to return in context, write results to `.firecrawl/` with `-o`. If `.firecrawl/` is not already ignored, check the ignore rules first and get user approval before editing `.gitignore`; fetched content must stay out of version control. Always quote URLs - shell interprets `?` and `&` as special characters.

```bash
firecrawl search "react hooks" -o .firecrawl/search-react-hooks.json --json
firecrawl scrape "<url>" -o .firecrawl/page.md
```

Naming conventions:

```
.firecrawl/search-{query}.json
.firecrawl/search-{query}-scraped.json
.firecrawl/{site}-{path}.md
```

Prefer bounded reads (`grep`, `head`, incremental reads); read a whole output file only when the authorized task requires it, in chunks:

```bash
wc -l .firecrawl/file.md && head -50 .firecrawl/file.md
grep -n "keyword" .firecrawl/file.md
```

Single format outputs raw content. Multiple formats (e.g., `--format markdown,links`) output JSON.

## Working with Results

These patterns are useful when working with file-based output (`-o` flag) for complex tasks:

```bash
# Extract URLs from search
jq -r '.data.web[].url' .firecrawl/search.json

# Get titles and URLs
jq -r '.data.web[] | "\(.title): \(.url)"' .firecrawl/search.json
```

## Parallelization

Run independent operations in parallel. Check `firecrawl --status` for concurrency limit:

```bash
firecrawl scrape "<url-1>" -o .firecrawl/1.md &
firecrawl scrape "<url-2>" -o .firecrawl/2.md &
firecrawl scrape "<url-3>" -o .firecrawl/3.md &
wait
```

For interact, scrape multiple pages and interact with each independently using their scrape IDs.

## Credit Usage

```bash
firecrawl credit-usage
firecrawl credit-usage --json --pretty -o .firecrawl/credits.json
```
