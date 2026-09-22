---
name: firecrawl-crawl
description: Bulk extract a website or scoped site section with the Firecrawl CLI when Firecrawl crawling is selected. Use for docs sections or many linked pages, with depth limits, path filters, and concurrency controls. Do not expand the requested site scope or treat this CLI workflow as a Firecrawl MCP requirement.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl crawl

Bulk extract content from a website. Crawls pages following links up to a depth/limit.

## When to use

- You need content from many pages on a site (e.g., all `/docs/`)
- You want to extract an entire site section
- Step 4 in the [Firecrawl CLI workflow](../firecrawl/SKILL.md#workflow): search → scrape → map → **crawl** → interact

This is a selected Firecrawl CLI workflow; MCP is optional and uses a different schema. Follow the [security rules](../firecrawl/rules/security.md) and keep crawl scope within the user's request.

## Quick start

```bash
# Crawl a docs section
firecrawl crawl "<url>" --include-paths /docs --limit 50 --wait -o .firecrawl/crawl.json

# Full crawl with depth limit
firecrawl crawl "<url>" --max-depth 3 --wait --progress -o .firecrawl/crawl.json

# Check status of a running crawl
firecrawl crawl <job-id>
```

## Options

| Option                    | Description                                 |
| ------------------------- | ------------------------------------------- |
| `--wait`                  | Wait for crawl to complete before returning |
| `--progress`              | Show progress while waiting                 |
| `--limit <n>`             | Max pages to crawl                          |
| `--max-depth <n>`         | Max link depth to follow                    |
| `--include-paths <paths>` | Only crawl URLs matching these paths        |
| `--exclude-paths <paths>` | Skip URLs matching these paths              |
| `--delay <ms>`            | Delay between requests                      |
| `--max-concurrency <n>`   | Max parallel crawl workers                  |
| `--pretty`                | Pretty print JSON output                    |
| `-o, --output <path>`     | Output file path                            |

## Tips

- Always use `--wait` when you need the results immediately. Without it, crawl returns a job ID for async polling.
- Use `--include-paths` to scope the crawl — don't crawl an entire site when you only need one section.
- Crawl consumes credits per page. Check `firecrawl credit-usage` before large crawls.

## See also

- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — scrape individual pages
- [firecrawl-map](../firecrawl-map/SKILL.md) — discover URLs before deciding to crawl
- [firecrawl-download](../firecrawl-download/SKILL.md) — download site to local files (uses map + scrape)
