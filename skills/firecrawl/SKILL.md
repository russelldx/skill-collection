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

Must be installed and authenticated. Check with `firecrawl --status`.

```
  🔥 firecrawl cli v1.8.0

  ● Authenticated via FIRECRAWL_API_KEY
  Concurrency: 0/100 jobs (parallel scrape limit)
  Credits: 500,000 remaining
```

- **Concurrency**: Max parallel jobs. Run parallel operations up to this limit.
- **Credits**: Remaining API credits. Each operation consumes credits.

If not ready, see [rules/install.md](rules/install.md). For output handling guidelines, see [rules/security.md](rules/security.md).

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

## Workflow

Follow this escalation pattern:

1. **Search** - No specific URL yet. Find pages, answer questions, discover sources.
2. **Scrape** - Have a URL. Extract its content directly.
3. **Map + Scrape** - Large site or need a specific subpage. Use `map --search` to find the right URL, then scrape it.
4. **Crawl** - Need bulk content from an entire site section (e.g., all /docs/).
5. **Interact** - Scrape first, then interact with the page (pagination, modals, form submissions, multi-step navigation).

| Need                        | Command               | When                                                      |
| --------------------------- | --------------------- | --------------------------------------------------------- |
| Find pages on a topic       | `search`              | No specific URL yet                                       |
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
