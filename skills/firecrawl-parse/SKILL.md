---
name: firecrawl-parse
description: Parse local PDF, DOCX, DOC, ODT, RTF, XLSX, XLS, or HTML files through the Firecrawl CLI only when the user explicitly chooses Firecrawl and authorizes uploading the selected files for cloud processing. Supports markdown, summaries, and document questions. A local path or request to read/summarize a file alone is not authorization; prefer local document tools for sensitive files or ordinary local reading.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl parse

Turn a local document into clean markdown on disk. Supports **PDF, DOCX, DOC, ODT, RTF, XLSX, XLS, HTML/HTM/XHTML**.

## When to use

- The user has selected Firecrawl for a local file and authorized that file's cloud upload and processing.
- For ordinary local reading or sensitive files, prefer local DOCX/PDF/XLSX tools (such as python-docx, pypdf, or openpyxl when available); do not upload merely because a path was supplied.
- Use [firecrawl-scrape](../firecrawl-scrape/SKILL.md) for URLs when Firecrawl extraction is selected.

## Upload boundary

This is a **CLI cloud-processing workflow**, not an offline parser. Before any `firecrawl parse` call, disclose that the file leaves the machine and confirm the exact file(s) and destination are authorized. Keep private documents local if permission is absent; do not install tools or authenticate automatically to bypass that boundary. Firecrawl MCP, if available, is a separate optional interface with its own schema, upload flow, and limits; CLI flags do not transfer to it. See [security rules](../firecrawl/rules/security.md).

## Quick start

Always save to `.firecrawl/` with `-o` — parsed docs can be hundreds of KB and blow up context if streamed to stdout. If `.firecrawl/` is not already ignored, check the ignore rules and get user approval before editing `.gitignore`; extracted content stays out of version control.

```bash
mkdir -p .firecrawl

# File → markdown
firecrawl parse ./paper.pdf -o .firecrawl/paper.md

# AI summary
firecrawl parse ./paper.pdf -S -o .firecrawl/paper-summary.md

# Ask a question about the doc
firecrawl parse ./paper.pdf -Q "What are the main conclusions?" \
  -o .firecrawl/paper-qa.md
```

Then `head`, `grep`, `rg` etc., or incrementally read the file - don't load the whole thing at once.

## Options

| Option                 | Description                             |
| ---------------------- | --------------------------------------- |
| `-S, --summary`        | AI-generated summary                    |
| `-Q, --query <prompt>` | Ask a question about the parsed content |
| `-o, --output <path>`  | Output file path — **always use this**  |
| `-f, --format <fmt>`   | `markdown` (default), `html`, `summary` |
| `--timeout <ms>`       | Timeout for the parse job               |
| `--timing`             | Show request duration                   |

## Tips

- Quote paths with spaces: `firecrawl parse "./My Doc.pdf" -o .firecrawl/mydoc.md`.
- The size and credit figures below come from Firecrawl's service documentation and may change; they are not verified by this repository.
- Max upload size: **50 MB** per file.
- Credits: ~1 per PDF page; HTML is 1 flat.
- Check `.firecrawl/` before re-parsing the same file.
- To check your credit balance (recommended for batch processing and similar workflows), use the `firecrawl credit-usage` command.

## See also

- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — same idea for URLs
