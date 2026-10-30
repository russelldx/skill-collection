#!/usr/bin/env node
import { rm } from 'node:fs/promises';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { capture, captureWithPreparedArea, ocr, status } from './snipaste.js';
import {
  WINDOW_CONTROL,
  arrangeAndVerify,
  foregroundWindow,
  listWindows,
  trimRect,
  verifyAndRestore,
} from './win32.js';
import { detectBrowsers, openViewer } from './viewer.js';

const server = new McpServer({ name: 'snipaste', version: '0.2.0' });

const DESKTOP_TARGETS = new Set(['fullscreen', 'active_screen', 'last']);

const asError = (error) => ({
  isError: true,
  content: [{ type: 'text', text: error instanceof Error ? error.message : String(error) }],
});

const truncate = (text, max) => (text.length > max ? `${text.slice(0, max)}...` : text);

const formatRect = (rect) => `${rect.width}x${rect.height} at ${rect.left},${rect.top}`;

const shotLine = (shot) => `${shot.width}x${shot.height} (${Math.round(shot.bytes / 1024)} KB) in ${shot.elapsedMs} ms`;

const unsupported = () =>
  new Error(
    'Safe window capture is Windows-only in this build. Pass allow_desktop:true after the user consents to a full-screen ' +
      'capture, or run this MCP server on Windows.',
  );

function desktopRefusal(kind) {
  return new Error(
    `Refused: a "${kind}" capture includes the desktop and every private window on it. ` +
      'Use target:"window" with app, title, or pid (call snip_windows to list windows): the window is maximized and only ' +
      'its verified rectangle is captured. Use snip_view to render a file, URL, or HTML page in a dedicated window. ' +
      'Pass allow_desktop:true only if the user explicitly asked for a desktop screenshot.',
  );
}

function requireSelector(kind, { app, title, pid }) {
  if (app || title || pid) return;
  throw new Error(
    `target "${kind}" needs app, title, or pid so it is clear which window to capture. ` +
      'Call snip_windows to list the visible windows and pick one.',
  );
}

function resolveMode(kind, mode) {
  if (kind === 'area') {
    if (mode && mode !== 'keep') {
      throw new Error('target "area" captures the window where it is, so it only works with mode "keep"; remove mode or pass mode:"keep".');
    }
    return 'keep';
  }
  return mode ?? 'maximize';
}

function areaRect({ x, y, width, height }) {
  const missing = Object.entries({ x, y, width, height })
    .filter(([, value]) => value === undefined)
    .map(([key]) => key);
  if (missing.length) throw new Error(`target "area" requires ${missing.join(', ')} in screen pixels.`);
  if (width <= 0 || height <= 0) throw new Error('target "area" needs a positive width and height.');
  return { left: x, top: y, width, height };
}

function coverageRefusal({ app, title }, check, consequence) {
  const name = title ? `${app} window ("${truncate(title, 120)}")` : `${app} window`;
  const offender = check.offender ?? 'another window';
  return new Error(
    `Refused: the ${name} was not fully visible while it was captured; ${offender} overlaps it at ` +
      `${check.bad} of ${check.samples} sample points. ${consequence} Close or move the overlapping window, ` +
      'activate the target window, or use snip_view.',
  );
}

const finishArea = (arranged, restore) =>
  verifyAndRestore({
    hwnd: arranged.hwnd,
    pid: arranged.pid,
    capture: arranged.capture,
    placement: arranged.placement,
    restore: restore !== false,
  });

// Coverage only: keeps the arrangement (and its temporary topmost flag) intact,
// so a retry still sees the same pixels the first attempt asked for.
const checkCoverage = (arranged) =>
  verifyAndRestore({ hwnd: arranged.hwnd, pid: arranged.pid, capture: arranged.capture, restore: false });

// The only path that returns a window image: locate and arrange the window,
// verify coverage, capture exactly that rectangle, verify again while the window
// is still in place, then restore. Any failed check deletes the file.
// A notification toast can slide in between the two checks. When that happens
// the newly covered edge is cut away if a large clean rectangle is left, and the
// second image is verified like the first; the caller only ever sees pixels that
// passed the post-check.
async function captureArranged(opts, arranged) {
  const captureOpts = {
    delay: opts.delay ?? 0,
    savePath: opts.savePath,
    overwrite: opts.overwrite ?? true,
    timeoutMs: opts.timeoutMs ?? 8000,
  };
  let current = arranged;
  let shot = await captureWithPreparedArea(current.capture, captureOpts);
  let check = await checkCoverage(current);
  if (check.ok) return { shot, check, arranged: current };
  await rm(shot.path, { force: true }).catch(() => {});
  await new Promise((resolve) => setTimeout(resolve, 250));
  const trimmed = await trimRect({ hwnd: current.hwnd, pid: current.pid, capture: current.capture }).catch(() => null);
  if (trimmed?.ok && trimmed.trimmed) {
    current = {
      ...current,
      capture: trimmed.capture,
      original: current.original ?? current.capture,
      trimmed: true,
      trimmedBy: trimmed.offender,
    };
  }
  shot = await captureWithPreparedArea(current.capture, captureOpts);
  return { shot, check: await checkCoverage(current), arranged: current, retried: true };
}

async function runSafeCapture(opts) {
  if (!WINDOW_CONTROL) throw unsupported();
  let arranged = await arrangeAndVerify({
    app: opts.app,
    title: opts.title,
    pid: opts.pid,
    hwnd: opts.hwnd,
    mode: opts.mode,
    settleMs: opts.settleMs,
    area: opts.area,
  });
  let shot = null;
  let check;
  try {
    const captured = await captureArranged(opts, arranged);
    shot = captured.shot;
    check = captured.check;
    arranged = captured.arranged;
    if (!check.ok) throw coverageRefusal(arranged, check, 'The image was deleted and nothing was returned.');
    check = await finishArea(arranged, opts.restore);
  } catch (error) {
    if (shot) await rm(shot.path, { force: true }).catch(() => {});
    await finishArea(arranged, opts.restore).catch(() => {});
    throw error;
  }
  if (!check.ok) {
    await rm(shot.path, { force: true }).catch(() => {});
    throw coverageRefusal(arranged, check, 'The image was deleted and nothing was returned.');
  }
  return { shot, arranged, check };
}

async function runSafeOcr(opts) {
  if (!WINDOW_CONTROL) throw unsupported();
  const arranged = await arrangeAndVerify({
    app: opts.app,
    title: opts.title,
    pid: opts.pid,
    mode: opts.mode,
    settleMs: opts.settleMs,
    area: opts.area,
  });
  const area = {
    x: arranged.capture.left,
    y: arranged.capture.top,
    width: arranged.capture.width,
    height: arranged.capture.height,
  };
  try {
    let result = await ocr({ target: 'area', area, delay: opts.delay ?? 0, timeoutMs: opts.timeoutMs ?? 6000 });
    let check = await checkCoverage(arranged);
    if (!check.ok) {
      result = await ocr({ target: 'area', area, delay: 0, timeoutMs: opts.timeoutMs ?? 6000 });
      check = await checkCoverage(arranged);
    }
    if (!check.ok) throw coverageRefusal(arranged, check, 'The recognized text was discarded and nothing was returned.');
    await finishArea(arranged, opts.restore).catch(() => {});
    return { result, arranged, check };
  } catch (error) {
    await finishArea(arranged, opts.restore).catch(() => {});
    throw error;
  }
}

function imageResult(shot, summary, includeImage) {
  const content = [{ type: 'text', text: `${summary}\nSaved to: ${shot.path}` }];
  if (includeImage) {
    content.push({ type: 'image', data: shot.buffer.toString('base64'), mimeType: 'image/png' });
  }
  return { content };
}

function ocrResult(result, timeoutMs) {
  if (!result.changed) {
    return asError(
      new Error(
        `Snipaste wrote nothing to the clipboard within ${timeoutMs} ms. Text extraction ("-o ocr_clipboard") ` +
          'is a Snipaste PRO feature; the free build ignores it silently and also stops answering later ' +
          'capture requests. ' +
          (result.recovered ? 'Snipaste has been restarted so captures work again. ' : '') +
          'Use an external OCR tool on a screenshot from snip_capture instead.' +
          (result.text ? `\nClipboard still contains: ${result.text.slice(0, 200)}` : ''),
      ),
    );
  }
  const text = result.text.trim();
  return {
    content: [
      {
        type: 'text',
        text: text || '(no text recognized - Snipaste clears the clipboard when OCR finds nothing)',
      },
    ],
  };
}

function describeWindowShot({ arranged, check, shot }) {
  const title = arranged.title ? ` "${truncate(arranged.title, 120)}"` : '';
  const trimmed = arranged.trimmed
    ? `\nTrimmed from ${formatRect(arranged.original)} to keep ${arranged.trimmedBy} out of the image.`
    : '';
  return (
    `Captured the ${arranged.app} window${title}: ${shotLine(shot)}.\n` +
    `Capture rect ${formatRect(arranged.capture)} of window ${formatRect(arranged.window)}; ` +
    `${check.samples} sample points confirmed it was unobstructed.\n` +
    `Window restored: ${check.restored ? 'yes' : 'no'}.${trimmed}`
  );
}

const target = z
  .enum(['window', 'area', 'fullscreen', 'active_screen', 'last'])
  .default('window')
  .describe(
    "'window' (default) captures one application window: it is maximized (or kept in place) and only its verified " +
      "rectangle is captured. 'area' captures a rectangle inside one specified window. 'fullscreen', " +
      "'active_screen', and 'last' capture the desktop and are refused unless allow_desktop is true.",
  );

const selectorFields = {
  app: z
    .string()
    .optional()
    .describe('Process name of the window owner, case-insensitive and without .exe (for example "notepad"). Call snip_windows to list.'),
  title: z
    .string()
    .optional()
    .describe('Regular expression matched against the window title, case-insensitive. Use it to pick one window when the process owns several.'),
  pid: z.number().int().positive().optional().describe('Process id of the window owner. More reliable than app when several instances run.'),
};

const placementFields = {
  mode: z
    .enum(['maximize', 'keep'])
    .optional()
    .describe(
      "'maximize' (default) fills the screen with the target window. 'keep' leaves the window where it is and refuses " +
        "when anything covers it. target 'area' always keeps the window in place.",
    ),
  settle_ms: z
    .number()
    .int()
    .min(0)
    .max(10000)
    .default(500)
    .describe('How long to wait after moving the window before the coverage check, so the app can finish repainting.'),
  restore: z.boolean().default(true).describe('Put the window back where it was (and un-maximize it) after the capture.'),
  allow_desktop: z
    .boolean()
    .default(false)
    .describe('Allow fullscreen/active_screen/last desktop captures. Pass true only if the user explicitly asked for a desktop screenshot.'),
};

const areaFields = {
  x: z.number().int().describe('Left edge in screen pixels (negative allowed on multi-monitor setups). Required when target is "area".').optional(),
  y: z.number().int().describe('Top edge in screen pixels. Required when target is "area".').optional(),
  width: z.number().int().positive().describe('Capture width in pixels. Required when target is "area".').optional(),
  height: z.number().int().positive().describe('Capture height in pixels. Required when target is "area".').optional(),
};

const outputFields = {
  save_path: z.string().optional().describe('Absolute path to write the PNG to. Defaults to a unique file in the OS temp directory.'),
  overwrite: z.boolean().default(true).describe('Replace an existing file at save_path. Defaults to true; pass false to make the call fail instead of overwriting.'),
  include_image: z.boolean().default(true).describe('Return the screenshot itself in the response. Set false to get only the file path and dimensions.'),
};

// Kept as plain z.object schemas: the SDK's JSON Schema conversion skips ZodEffects,
// so a superRefine wrapper would advertise an empty parameter list to clients.
const captureSchema = z.object({
  target,
  ...selectorFields,
  ...placementFields,
  ...areaFields,
  delay: z.number().min(0).max(30).default(0).describe('Seconds to wait before capturing, for transient UI.'),
  shadow: z
    .boolean()
    .default(false)
    .describe('Add a drop shadow. PRO only, ignored by the free build, and ignored for window/area captures because a shadow adds pixels outside the verified rectangle.'),
  ...outputFields,
  timeout_ms: z.number().int().min(500).max(30000).default(8000).describe('How long to wait for Snipaste to finish writing the file.'),
});

const ocrSchema = z.object({
  target,
  ...selectorFields,
  ...placementFields,
  ...areaFields,
  delay: z.number().min(0).max(30).default(0).describe('Seconds to wait before capturing.'),
  timeout_ms: z.number().int().min(500).max(60000).default(6000).describe('How long to wait for OCR text to land in the clipboard.'),
});

const viewSchema = z.object({
  file: z.string().optional().describe('Absolute path to a local file to render (HTML, image, PDF, or anything the browser can open).'),
  url: z.string().optional().describe('http, https, or file URL to render.'),
  html: z.string().optional().describe('HTML source to render. It is written to a temporary file and opened there.'),
  browser: z.enum(['auto', 'edge', 'chrome']).default('auto').describe('Browser for the temporary viewer. auto picks the first of Edge then Chrome that is installed; an explicit choice never falls back.'),
  width: z.number().int().min(320).max(10000).optional().describe('Window width in pixels. Defaults to the primary monitor work area width.'),
  height: z.number().int().min(240).max(10000).optional().describe('Window height in pixels. Defaults to the primary monitor work area height.'),
  kiosk: z.boolean().default(false).describe('True opens the browser in kiosk mode instead of an app-style window.'),
  wait_ms: z.number().int().min(0).max(30000).default(1200).describe('How long to wait after the window appears, so the page can render.'),
  ...outputFields,
  timeout_ms: z.number().int().min(500).max(30000).default(8000).describe('How long to wait for Snipaste to finish writing the file.'),
});

server.registerTool(
  'snip_capture',
  {
    title: 'Screenshot one window with Snipaste',
    description:
      'Privacy rule: never capture the desktop or other private windows. The default flow is target:"window": pick the ' +
      'target with app/title/pid (snip_windows lists candidates), maximize it, verify that its rectangle is unobstructed, ' +
      'capture only that rectangle with Snipaste, then restore the window. If the window cannot be verified, the call ' +
      'fails and no image is returned. target "area" captures a rectangle inside one named window. ' +
      'fullscreen/active_screen/last are refused unless allow_desktop is true, and allow_desktop must only be used when ' +
      'the user explicitly asked for a desktop screenshot. Window and area captures are Windows-only. ' +
      'When the content is a file, URL, or HTML page, use snip_view instead: it renders the page in a dedicated window.',
    inputSchema: captureSchema,
    annotations: { readOnlyHint: false, openWorldHint: false },
  },
  async ({
    target: kind,
    app,
    title,
    pid,
    mode,
    settle_ms,
    restore,
    allow_desktop,
    x,
    y,
    width,
    height,
    delay,
    shadow,
    save_path,
    overwrite,
    include_image,
    timeout_ms,
  }) => {
    try {
      if (DESKTOP_TARGETS.has(kind)) {
        if (!allow_desktop) throw desktopRefusal(kind);
        const shot = await capture({
          target: kind,
          delay,
          shadow,
          savePath: save_path,
          overwrite,
          timeoutMs: timeout_ms,
        });
        return imageResult(shot, `${kind} desktop capture (allow_desktop was set): ${shotLine(shot)}.`, include_image);
      }
      requireSelector(kind, { app, title, pid });
      const rect = kind === 'area' ? areaRect({ x, y, width, height }) : undefined;
      const result = await runSafeCapture({
        app,
        title,
        pid,
        mode: resolveMode(kind, mode),
        settleMs: settle_ms,
        restore,
        area: rect,
        delay,
        savePath: save_path,
        overwrite,
        timeoutMs: timeout_ms,
      });
      return imageResult(result.shot, describeWindowShot(result), include_image);
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_view',
  {
    title: 'Render a page in a dedicated window and screenshot it',
    description:
      'Privacy rule: never capture the desktop or other private windows. This opens file, url, or html in a temporary ' +
      'Edge/Chrome window with its own throwaway profile (your normal browser windows and logins are untouched), sizes it ' +
      'to the screen, verifies that it is unobstructed, captures only that window with Snipaste, and closes the temporary ' +
      'browser. Use this for rendering HTML, images, PDFs, or a URL when no suitable application window exists. ' +
      'Windows-only in this build.',
    inputSchema: viewSchema,
    annotations: { readOnlyHint: false, openWorldHint: false },
  },
  async ({ file, url, html, browser, width, height, kiosk, wait_ms, save_path, overwrite, include_image, timeout_ms }) => {
    try {
      if (!WINDOW_CONTROL) throw unsupported();
      const session = await openViewer({ file, url, html, browser, kiosk, waitMs: wait_ms, width, height });
      try {
        // openViewer already placed and verified the window; the capture helper
        // below re-verifies before trusting its rectangle and cuts away any
        // toast that slid in afterwards.
        const arranged = {
          hwnd: session.hwnd,
          pid: session.pid,
          app: session.browser.label,
          title: session.title,
          window: session.rect,
          capture: session.rect,
          placement: session.placement,
          trimmed: session.trimmed,
          original: session.original,
        };
        const viewerOpts = { savePath: save_path, overwrite, timeoutMs: timeout_ms };
        let shot = null;
        let check = null;
        let finalArranged = arranged;
        try {
          const captured = await captureArranged(viewerOpts, arranged);
          shot = captured.shot;
          check = captured.check;
          finalArranged = captured.arranged;
          if (!check.ok) throw coverageRefusal(finalArranged, check, 'The image was deleted and nothing was returned.');
        } catch (error) {
          if (shot) await rm(shot.path, { force: true }).catch(() => {});
          throw error;
        }
        const trimmed = finalArranged.trimmed
          ? `\nTrimmed from ${formatRect(finalArranged.original)} to keep ${finalArranged.trimmedBy} out of the image.`
          : '';
        const summary =
          `Rendered ${session.url} in a temporary ${session.browser.label} window: ${shotLine(shot)}.\n` +
          `Capture rect ${formatRect(finalArranged.capture)}; ${check.samples} sample points confirmed the viewer was ` +
          `unobstructed. The temporary browser is closed and its temporary profile deleted.${trimmed}`;
        return imageResult(shot, summary, include_image);
      } finally {
        await session.close().catch(() => {});
      }
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_windows',
  {
    title: 'List visible windows',
    description:
      'List visible top-level windows with process name, title, pid, rectangle, maximized state, and whether each is in ' +
      'the foreground. Read-only. Call this first to find the app/title/pid to pass to snip_capture or snip_ocr. ' +
      'Windows-only in this build.',
    inputSchema: z.object({
      app: z.string().optional().describe('Only windows whose process name matches, case-insensitive and without .exe.'),
      title: z.string().optional().describe('Only windows whose title matches this regular expression, case-insensitive.'),
      pid: z.number().int().positive().optional().describe('Only windows owned by this process id.'),
      limit: z.number().int().min(1).max(100).default(20).describe('Maximum number of windows to return.'),
    }),
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  async ({ app, title, pid, limit }) => {
    try {
      if (!WINDOW_CONTROL) throw new Error('Listing windows is Windows-only in this build.');
      const { total, windows } = await listWindows({ app, title, pid, limit });
      const payload = {
        total,
        returned: windows.length,
        windows: windows.map((win) => ({
          hwnd: win.hwnd,
          app: win.app,
          title: win.title,
          pid: win.pid,
          rect: { left: win.left, top: win.top, width: win.width, height: win.height },
          maximized: win.maximized,
          minimized: win.minimized,
          foreground: win.foreground,
        })),
      };
      return { content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }] };
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_ocr',
  {
    title: 'OCR text off one window with Snipaste',
    description:
      'Privacy rule: never capture the desktop or other private windows. Uses the same safe flow as snip_capture ' +
      '(locate, maximize or keep, verify coverage, recognize text, verify again, restore) and returns the text Snipaste ' +
      'recognizes in the verified window rectangle. It overwrites the system clipboard, which is cleared when recognition ' +
      'finds nothing. Text extraction is a Snipaste PRO feature: on the free build the output is silently ignored and ' +
      'Snipaste stops answering later captures, so this call fails with a clear error after restarting Snipaste. ' +
      'fullscreen/active_screen/last are refused unless allow_desktop is true.',
    inputSchema: ocrSchema,
    annotations: { readOnlyHint: false, openWorldHint: false },
  },
  async ({
    target: kind,
    app,
    title,
    pid,
    mode,
    settle_ms,
    restore,
    allow_desktop,
    x,
    y,
    width,
    height,
    delay,
    timeout_ms,
  }) => {
    try {
      if (DESKTOP_TARGETS.has(kind)) {
        if (!allow_desktop) throw desktopRefusal(kind);
        return ocrResult(await ocr({ target: kind, delay, timeoutMs: timeout_ms }), timeout_ms);
      }
      requireSelector(kind, { app, title, pid });
      const rect = kind === 'area' ? areaRect({ x, y, width, height }) : undefined;
      const { result } = await runSafeOcr({
        app,
        title,
        pid,
        mode: resolveMode(kind, mode),
        settleMs: settle_ms,
        restore,
        area: rect,
        delay,
        timeoutMs: timeout_ms,
      });
      return ocrResult(result, timeout_ms);
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_status',
  {
    title: 'Snipaste status',
    description:
      'Report whether the Snipaste executable was found, its path and version, whether it is running, whether safe ' +
      'window capture is supported on this platform (windows or unsupported), which of Edge/Chrome snip_view can use, ' +
      'and the current foreground window. Call this first when a capture fails or to verify SNIPASTE_PATH.',
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  async () => {
    try {
      const info = await status();
      let foreground = null;
      if (WINDOW_CONTROL) {
        const found = await foregroundWindow().catch(() => null);
        if (found?.found) foreground = { app: found.app, title: found.title, pid: found.pid };
      }
      const payload = {
        ...info,
        window_control: WINDOW_CONTROL ? 'windows' : 'unsupported',
        browsers: detectBrowsers().map((browser) => browser.name),
        foreground,
      };
      return { content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }] };
    } catch (error) {
      return asError(error);
    }
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write('snipaste-mcp ready\n');
