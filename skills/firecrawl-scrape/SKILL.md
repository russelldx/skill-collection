---
name: firecrawl-scrape
description: Extract clean markdown from known URLs, including JavaScript-rendered SPAs, when Firecrawl CLI extraction is selected. Supports single-page and concurrent URL scraping. Do not mandate Firecrawl for every URL or replace WebFetch and other suitable extraction tools solely because a user asks to read a webpage.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl scrape

Scrape one or more URLs. Returns clean, LLM-optimized markdown. Multiple URLs are scraped concurrently.

## When to use

- Firecrawl is selected for extracting a specific URL's content
- The page is static or JS-rendered (SPA)
- Step 2 in the [Firecrawl CLI workflow](../firecrawl/SKILL.md#workflow): search → **scrape** → map → crawl → interact

This is the CLI interface, not a mandate to replace WebFetch or install MCP. Firecrawl MCP is optional and uses its own schema. Follow the [security rules](../firecrawl/rules/security.md) before sending private URLs or data.

## Quick start

```bash
# Basic markdown extraction
firecrawl scrape "<url>" -o .firecrawl/page.md

# Main content only, no nav/footer
firecrawl scrape "<url>" --only-main-content -o .firecrawl/page.md

# Wait for JS to render, then scrape
firecrawl scrape "<url>" --wait-for 3000 -o .firecrawl/page.md

# Multiple URLs (separate files in .firecrawl/; use single-URL calls for -o or multiple formats)
firecrawl scrape "https://example.com" "https://example.com/blog" "https://example.com/docs"

# Get markdown and links together
firecrawl scrape "<url>" --format markdown,links -o .firecrawl/page.json

# Ask a question about the page
firecrawl scrape "https://example.com/pricing" --query "What is the enterprise plan price?"
```

## Options

| Option                   | Description                                                      |
| ------------------------ | ---------------------------------------------------------------- |
| `-f, --format <formats>` | Output formats: markdown, html, rawHtml, links, screenshot, json |
| `-Q, --query <prompt>`   | Ask a question about the page content; check current charges      |
| `-H, --html`             | Output HTML (shortcut for `--format html`), not HTTP headers       |
| `--only-main-content`    | Strip nav, footer, sidebar — main content only                   |
| `--wait-for <ms>`        | Wait for JS rendering before scraping                            |
| `--include-tags <tags>`  | Only include these HTML tags                                     |
| `--exclude-tags <tags>`  | Exclude these HTML tags                                          |
| `-o, --output <path>`    | Output file path                                                 |

Confirm options with `firecrawl scrape --help`; fees and supported formats depend on the service and installed version, not this table.

## Structured provider execution

Use this path only after the [capability check](../firecrawl/SKILL.md#prerequisites) confirms provider support and [discovery](../firecrawl/SKILL.md#structured-provider-discovery) returns a suitable provider and capability. A known URL can still be scraped without provider discovery.

For CLI versions supporting these forms, inspect the contract and then execute it:

```bash
firecrawl list "<provider-id>" "<capability-id>" --pretty
firecrawl scrape "<provider-id>/<capability-id>" --options '<JSON matching the selected contract>' --json -o .firecrawl/provider-result.json
```

Replace placeholders with returned identifiers and contract-valid inputs; do not infer them from a website name. Respect required fields and each `requiresOneOf` group. Read the declared response shape and `response.key` rather than assuming a `records` field. Provider pagination uses its own input/cursor mapping, not the catalogue's `next` value; preserve filters and stop at the declared end or user limit.

URL mode and provider mode are distinct. Check every provider item for errors, even when the outer response indicates success. Observe the [authorization and retry rules](../firecrawl/rules/security.md) before terms acceptance, side effects, or any retry. Do not copy CLI flags into an SDK or MCP request.

## Completion and large results

Inspect the saved result before claiming completion: page content or structured records must answer the request, not just return a success flag. Disclose partial output and retain source links. Use JSON output when metadata or a structured envelope is needed, keeping stderr separate from JSON stdout.

Read large output in bounded sections with local file tools. If display/context limits interrupt the response, execution may already have succeeded: keep returned request/scrape IDs and inspect saved or retained results using the selected interface's documented recovery mechanism. Do not resubmit solely because the client could not display the response.

For PDF URLs, check whether the installed CLI offers a page-budget option such as `--max-pages` before using it. Limit pages within the user's budget when supported; if no suitable bound is available for an unknown-size document, ask before proceeding. A page cap is per PDF, not a total cost ceiling. Inspect parsed/total page counts and credits when returned; do not represent a partial parse as the whole document. Local-file upload authorization remains separate.

## Tips

- **Prefer plain scrape over `--query`.** Save content and inspect it locally when the whole page is needed. Use `--query` for a targeted answer only when its current extra charges fit the authorized budget.
- **Try scrape before interact.** Scrape handles static pages and JS-rendered SPAs. Only escalate to `interact` when you need interaction (clicks, form fills, pagination).
- Multiple-URL mode saves separate files under `.firecrawl/` and does not provide one `-o` destination. The upstream CLI's batch path selects markdown when available and otherwise can write the JSON response into a `.md` file; it is not a way to preserve all requested formats. Use one URL per invocation for explicit output paths or multiple formats, and bound concurrency.
- Single format outputs raw content. Multiple formats (e.g., `--format markdown,links`) output JSON.
- Always quote URLs — shell interprets `?` and `&` as special characters.
- Naming convention: `.firecrawl/{site}-{path}.md`

## See also

- [Firecrawl CLI search](../firecrawl/SKILL.md#search) — find pages when you don't have a URL
- [firecrawl-interact](../firecrawl-interact/SKILL.md) — when scrape can't get the content, use `interact` to click, fill forms, etc.
- [firecrawl-download](../firecrawl-download/SKILL.md) — bulk download an entire site to local files
