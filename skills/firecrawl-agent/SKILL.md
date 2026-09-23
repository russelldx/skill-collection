---
name: firecrawl-agent
description: Use the Firecrawl CLI agent for AI-powered multi-page structured extraction when Firecrawl is selected. Navigate sites and extract pricing, products, directory entries, or other data as JSON with a schema. Use within the user's authorized domains, data scope, and credit budget; this is not a requirement to install Firecrawl MCP.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl *)
---

# firecrawl agent

AI-powered autonomous extraction. The agent navigates sites and extracts structured data (takes 2-5 minutes).

This is the Firecrawl CLI interface; optional MCP tools use different schemas. Follow the [security rules](../firecrawl/rules/security.md), bound target domains and credits, and do not authorize account actions or private-data uploads through an extraction prompt implicitly.

## When to use

- You need structured data from complex multi-page sites
- Manual scraping would require navigating many pages
- You want the AI to figure out where the data lives

Before autonomous extraction of structured records, consider [provider discovery](../firecrawl/SKILL.md#structured-provider-discovery) if the chosen interface supports it. Prefer an inspected, suitable provider when it covers the task; use Agent when no match fits or autonomous navigation is needed. Do not auto-install provider support or expand the user's data scope.

## Quick start

Check `firecrawl agent --help` for supported options. Scope the prompt and URLs to the actual request and set `--max-credits` to the user's budget when applicable. In versions supporting JSON output and bounded waiting:

```bash
# Extract structured data with a bounded wait
firecrawl agent "extract all pricing tiers" --wait --timeout 300 --json -o .firecrawl/pricing.json

# With a JSON schema for structured output
firecrawl agent "extract products" --schema '{"type":"object","properties":{"name":{"type":"string"},"price":{"type":"number"}}}' --wait --timeout 300 --json -o .firecrawl/products.json

# Focus on specific pages
firecrawl agent "get feature list" --urls "<url>" --wait --timeout 300 --json -o .firecrawl/features.json
```

## Options

| Option                 | Description                               |
| ---------------------- | ----------------------------------------- |
| `--urls <urls>`        | Starting URLs for the agent               |
| `--model <model>`      | Model to use: spark-1-mini or spark-1-pro |
| `--schema <json>`      | JSON schema for structured output         |
| `--schema-file <path>` | Path to JSON schema file                  |
| `--max-credits <n>`    | Credit limit for this agent run           |
| `--wait`               | Wait for agent to complete                |
| `--timeout <seconds>`  | Bound waiting; not a cancellation or credit limit |
| `--poll-interval <seconds>` | Interval while waiting on a job       |
| `--json`               | Request machine-readable output           |
| `--pretty`             | Pretty print JSON output                  |
| `-o, --output <path>`  | Output file path                          |

## Existing jobs and completion

Omit `--wait` when returning a job ID is appropriate; report the job as pending, not completed. Record the returned ID. For versions whose help supports these forms, query or wait on that existing job rather than submitting the extraction prompt again:

```bash
firecrawl agent "<returned-job-id>" --status --json
firecrawl agent "<returned-job-id>" --wait --poll-interval 10 --timeout 300 --json -o .firecrawl/result.json
```

A waiting timeout does not prove cancellation or stop future charges. Preserve the job ID and inspect its status; if a submission's outcome is unknown, resolve that outcome before any new submission. Do not cancel jobs without authorization and confirmed command support.

Completion requires a terminal success state and inspected output that answers the request. A valid JSON file may contain only a job ID, status, or error; verify the actual records and requested schema before claiming a completed extraction. Report failed or partial results as such.

## Tips

- Choose bounded `--wait` or return the actual job ID according to the user's needs and host execution limits; do not wait indefinitely.
- Use `--schema` for predictable, structured output — otherwise the agent returns freeform data.
- Agent runs consume more credits than simple scrapes. Use `--max-credits` to cap spending.
- For simple single-page extraction, prefer `scrape` — it's faster and cheaper.

## See also

- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — simpler single-page extraction
- [firecrawl-interact](../firecrawl-interact/SKILL.md) — scrape + interact for manual page interaction (more control)
- [firecrawl-crawl](../firecrawl-crawl/SKILL.md) — bulk extraction without AI
