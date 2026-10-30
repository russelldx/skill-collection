# snipaste-mcp

MCP server that drives [Snipaste](https://www.snipaste.com/)'s command line to take screenshots and read text off the screen — without ever capturing the desktop or other private windows.

## Privacy: captures never include the desktop

`snip_capture` never screenshots the whole desktop by default. A capture always targets one application window:

1. The window is located by `app` / `title` / `pid` (`snip_windows` lists candidates), recorded, and — by default — maximized so it fills the screen.
2. Only that window's visible rectangle is captured with Snipaste's `--area`, never the rest of the monitor.
3. While the window is still in place, sample points across the rectangle are hit-tested: every point must belong to the target window (its own popups and menus pass). If anything else covers it, no image is returned.
4. The window is restored to its previous size and position.

If verification fails the PNG is deleted and the call returns an error naming the overlapping window. `fullscreen`, `active_screen` and `last` are refused unless `allow_desktop: true` is passed, and that flag is meant only for the case where the user explicitly asked for a desktop screenshot. `snip_ocr` follows the same flow: recognized text is only returned after the same verification.

When no suitable application window exists (render HTML, an image, a PDF, or a URL), use `snip_view`: it opens the content in a temporary Edge/Chrome window with a throwaway profile, captures that window, and closes the browser again. The user's own browser windows, tabs and logins are never touched.

## Tools

| Tool | What it does |
|---|---|
| `snip_capture` | Screenshot one window (default), a rectangle inside one window, or — with `allow_desktop` — the desktop. Returns the PNG as an MCP image block plus the saved path and size. |
| `snip_view` | Render a file, URL or HTML page in a dedicated temporary browser window and screenshot it. |
| `snip_windows` | Read-only list of visible top-level windows (app, title, pid, rectangle, maximized, foreground) to pick a capture target. |
| `snip_ocr` | Snipaste text extraction from one verified window. **PRO only** — see below. |
| `snip_status` | Where Snipaste was found, version, running state, window-control support, detected browsers, foreground window. |

### `snip_capture` parameters

| Parameter | Type / default | Meaning |
|---|---|---|
| `target` | `'window' \| 'area' \| 'fullscreen' \| 'active_screen' \| 'last'`, default `'window'` | `window`: one verified window. `area`: a rectangle inside one window. The last three capture the desktop and are refused unless `allow_desktop: true`. |
| `app` | string?, process name without `.exe` | Pick the window by process. |
| `title` | string?, regular expression | Pick one window when the process owns several. |
| `pid` | number? | Pick by process id; most reliable with several instances. |
| `mode` | `'maximize' \| 'keep'`, default `'maximize'` | `maximize` fills the screen before the capture; `keep` leaves the window where it is and refuses when anything covers it. `area` always keeps. |
| `settle_ms` | number, default 500 | Wait after moving the window before the coverage check, so the app can repaint. |
| `restore` | boolean, default true | Put the window back (and un-maximize it) after the capture. |
| `allow_desktop` | boolean, default false | Explicit opt-in for `fullscreen` / `active_screen` / `last`. |
| `x` `y` `width` `height` | numbers, for `area` | Screen-pixel rectangle. It must lie fully inside the window's visible rectangle. |
| `delay` | number, default 0 | Seconds to wait before capturing. |
| `shadow` | boolean, default false | PRO-only, ignored by the free build, and ignored for window/area captures. |
| `save_path` | string? | Absolute PNG path. Defaults to a unique file in the OS temp directory. Missing directories are created; non-ASCII names are fine. |
| `overwrite` | boolean, default true | `false` makes the call fail instead of replacing an existing file. |
| `include_image` | boolean, default true | `false` returns only the path and dimensions. |
| `timeout_ms` | number, default 8000 | How long to wait for Snipaste to finish writing the file. |

### `snip_view` parameters

| Parameter | Type / default | Meaning |
|---|---|---|
| `file` / `url` / `html` | exactly one | Local file, http(s)/file URL, or HTML source (written to a temp file first). |
| `browser` | `'auto' \| 'edge' \| 'chrome'`, default `auto` | `auto` picks the first of Edge then Chrome that is installed; an explicit choice never falls back. |
| `width` / `height` | numbers | Window size; defaults to the primary monitor work area. |
| `kiosk` | boolean, default false | `true` uses browser kiosk mode instead of an app-style window. |
| `wait_ms` | number, default 1200 | Wait after the window appears, so the page can render. |
| `save_path` / `overwrite` / `include_image` / `timeout_ms` | as above | Same semantics as `snip_capture`. |

### `snip_windows` parameters

`app`, `title`, `pid` (all optional filters), `limit` (default 20, max 100). Read-only.

### Choosing a tool

- Content lives in an app window the user can name → `snip_capture` with `target: 'window'` (default flow).
- Content is a file, URL or HTML, or the app window can't be captured cleanly → `snip_view`.
- Unsure which window → `snip_windows` first, then capture by `app` / `title` / `pid`.
- Desktop capture → only with the user's explicit request and `allow_desktop: true`.

## How a window capture stays private

- **Rectangle**: the DWM extended frame (the pixels the user actually sees, excluding Windows' invisible resize borders), intersected with the monitor work area. `keep` mode additionally insets 8 px per side to hide the rounded-corner pixels where the window behind would otherwise show through.
- **Coverage check**: a grid of up to ~400 sample points across the rectangle is hit-tested; every root window under a point must be the target (windows owned by the same process pass). Cloaked and fully transparent windows are skipped because they paint nothing.
- **Transient overlays**: if a notification toast slides over one edge between the capture and the check, the covered edge is cut away when a clean rectangle of at least 320x200 and 60% of the original remains; that rectangle is re-captured and re-verified. Otherwise the call refuses. The caller only ever receives pixels that passed the post-capture check.
- **Restore**: the original size, position and maximized state are restored with `SetWindowPos`; a window the app had hidden is shown again.

## Requirements

- Snipaste 2.x. Portable installs are fine; it does not have to be on `PATH`.
- Node.js 18+.
- **Window capture and `snip_view` are Windows-only** in this build. On other platforms `snip_capture` refuses unless `allow_desktop: true` is passed after the user consents, and the other window tools report "Windows-only".
- `snip_view` needs Microsoft Edge (ships with Windows) or Google Chrome.
- On Windows the clipboard (needed for OCR) is read through PowerShell.

## Setup

```bash
npm install
npm test          # end-to-end test against the local Snipaste install
```

`npm test` talks to the real Snipaste on this machine: it opens dedicated WinForms test windows (it never uses Notepad or any of the user's documents), takes small verified screenshots, writes them to a temp directory and removes them afterwards. On a free build the OCR case is expected to fail with the PRO error.

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

The ignored `--active-window` is why this server carries its own window control: it reads the window rectangle
with Win32 and captures exactly that rectangle with `--area`. An unparseable `--area` argument is likewise
silently ignored, so the coordinates are computed carefully and verified by the before/after checks.

Two Snipaste behaviours shaped the design:

- `-o ocr_clipboard` on the free build does not merely produce nothing: the app stays alive but stops answering
  later `snip` commands, so every capture after a failed OCR times out. `snip_ocr` detects the timeout, restarts
  Snipaste to restore capture, and returns an error naming the PRO requirement.
- `--block` is never used. On Snipaste 2.9.2 it suppresses file output entirely; completion is detected by polling
  for the output file to stop growing, or for the clipboard to change.

## Limitations

- Each window capture adds two PowerShell round-trips for the window control: about +1.5 s cold, ~+1 s warm.
- A foreground lock can keep a maximized window from actually coming to the front; the coverage check then fails
  and the call refuses. Click the target window once and retry — the server never degrades to a desktop capture.
- Topmost widgets (music mini-players, notification banners) that cover a window edge are trimmed away when a
  large clean rectangle remains, and refused otherwise. That is intentional.
- Multimonitor: only the target window's own rectangle is captured; other monitors are never included.
- If the Node process is killed mid-capture, the window stays maximized — there is no chance to restore it.
- `keep` mode insets the rectangle by 8 px per side; the outermost ring of a rounded window is not captured.

## Notes

- Screenshots default to a unique file under the OS temp directory (`snipaste-mcp/`). Pass `save_path` to keep them elsewhere.
- `snip_ocr` overwrites the system clipboard, and Snipaste clears it when recognition finds nothing.
- A capture timeout can also mean a Snipaste selection window is open and waiting for a click; close it and retry.
- Coordinates are physical screen pixels (per-monitor DPI aware), the same units Snipaste's `--area` uses.
