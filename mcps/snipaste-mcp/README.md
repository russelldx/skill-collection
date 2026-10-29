# snipaste-mcp

MCP server that drives [Snipaste](https://www.snipaste.com/)'s command line to take screenshots and read text off the screen.

## Tools

| Tool | What it does |
|---|---|
| `snip_capture` | Screenshot the desktop, a screen, a window, the previous selection, or an explicit rectangle. Returns the PNG as an MCP image block plus the saved path and size. |
| `snip_ocr` | Snipaste text extraction on a region. **PRO only** — see below. |
| `snip_status` | Where Snipaste was found, its version, whether it is running. Call it when a capture fails. |

`snip_capture` arguments: `target` (`fullscreen` \| `active_screen` \| `active_window` \| `last` \| `area`),
`x`/`y`/`width`/`height` (for `area`), `delay`, `shadow`, `save_path`, `overwrite`, `include_image`, `timeout_ms`.

Saving under a chosen name is just `save_path`: the server creates missing directories, accepts non-ASCII names,
refuses to replace an existing file unless `overwrite: true`, and reports the final path back.

## Requirements

- Snipaste 2.x. Portable installs are fine; it does not have to be on `PATH`.
- Node.js 18+.
- Windows or macOS. On Windows the clipboard (needed for OCR) is read through PowerShell.

## Setup

```bash
npm install
npm test          # end-to-end test against the local Snipaste install
```

`npm test` talks to the real Snipaste on this machine: it takes a few small screenshots, writes them to a temp
directory and removes them afterwards. On a free build the OCR case is expected to fail with the PRO error.

Register it with an MCP client:

```json
{
  "mcpServers": {
    "snipaste": {
      "command": "node",
      "args": ["<path-to>/snipaste-mcp/src/server.js"]
    }
  }
}
```

How the executable is located, in order: `SNIPASTE_PATH` if set, the usual install directories
(`Program Files`, `%LOCALAPPDATA%\Programs`, `/Applications`), `PATH`, the path cached from a previous run,
the path of the running process, and finally a bounded scan of `Desktop`, `Downloads`, `Documents` and
`%LOCALAPPDATA%\Programs`. The first hit is cached in the user config directory, so a portable install that is
neither running nor on `PATH` is found once and resolved instantly afterwards.

If Snipaste is not running it is started detached, and the first capture waits for it: expect roughly 2.5 s for
that call and ~0.3 s for the ones after it.

## Free vs PRO

Snipaste's own comparison table decides what works here. On the free build:

- Works: region / fullscreen / active-screen capture, repeat-last, `--delay`, save to file, copy to clipboard.
- Silently ignored: `--active-window`, `--shadow`, `-o ocr_clipboard`, `--block`, and combining multiple `-o` outputs.

Two Snipaste behaviours shaped the design:

- `-o ocr_clipboard` on the free build does not merely produce nothing: the app stays alive but stops answering
  later `snip` commands, so every capture after a failed OCR times out. `snip_ocr` detects the timeout, restarts
  Snipaste to restore capture, and returns an error naming the PRO requirement.
- `--block` is never used. On Snipaste 2.9.2 it suppresses file output entirely; completion is detected by polling
  for the output file to stop growing, or for the clipboard to change.

## Notes

- Screenshots default to a unique file under the OS temp directory (`snipaste-mcp/`). Pass `save_path` to keep them elsewhere.
- `snip_ocr` overwrites the system clipboard, and Snipaste clears it when recognition finds nothing.
- A capture timeout can also mean a Snipaste selection window is open and waiting for a click; close it and retry.
- Coordinates are Snipaste's, i.e. physical pixels of the virtual desktop — on a 2560x1600 screen, `fullscreen` reports 2560x1600 even when Windows reports a DPI-scaled size.
