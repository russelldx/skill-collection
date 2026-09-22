---
name: firecrawl-download
description: Save a website or documentation section as local markdown, screenshots, or other files using the Firecrawl CLI when Firecrawl is selected. Combines remote mapping and scraping for offline copies; authorize site scope and output location before bulk work. This is not an offline-only fetcher or a Firecrawl MCP requirement.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl download

> **Experimental.** Convenience command that combines `map` + `scrape` to save an entire site as local files.

Maps the site first to discover pages, then scrapes each one into nested directories under `.firecrawl/`. All scrape options work with download. Follow the [security rules](../firecrawl/rules/security.md). Confirm the site scope, page limit, credit budget, and output destination before bulk work; use `-y` in non-interactive execution only after that authorization. It is not a substitute for user consent.

## When to use

- You want to save an entire site (or section) to local files
- You need offline access to documentation or content
- Bulk content extraction with organized file structure

## Quick start

```bash
# Interactive wizard (picks format, screenshots, paths for you)
firecrawl download https://docs.example.com

# With screenshots
firecrawl download https://docs.example.com --screenshot --limit 20 -y

# Multiple formats (each saved as its own file per page)
firecrawl download https://docs.example.com --format markdown,links --screenshot --limit 20 -y
# Creates per page: index.md + links.txt + screenshot.png

# Filter to specific sections
firecrawl download https://docs.example.com --include-paths "/features,/sdks"

# Skip translations
firecrawl download https://docs.example.com --exclude-paths "/zh,/ja,/fr,/es,/pt-BR"

# Full combo
firecrawl download https://docs.example.com \
  --include-paths "/features,/sdks" \
  --exclude-paths "/zh,/ja" \
  --only-main-content \
  --screenshot \
  -y
```

## Download options

| Option                    | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `--limit <n>`             | Max pages to download                                    |
| `--search <query>`        | Filter URLs by search query                              |
| `--include-paths <paths>` | Only download matching paths                             |
| `--exclude-paths <paths>` | Skip matching paths                                      |
| `--allow-subdomains`      | Include subdomain pages                                  |
| `-y`                      | Skip CLI prompt only after user authorization covers the operation |

## Scrape options (all work with download)

`-f <formats>`, `-H`, `-S`, `--screenshot`, `--full-page-screenshot`, `--only-main-content`, `--include-tags`, `--exclude-tags`, `--wait-for`, `--max-age`, `--country`, `--languages`

## See also

- [firecrawl-map](../firecrawl-map/SKILL.md) — just discover URLs without downloading
- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — scrape individual pages
- [firecrawl-crawl](../firecrawl-crawl/SKILL.md) — bulk extract as JSON (not local files)
