import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, rm, writeFile, access } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve as resolvePath, basename } from 'node:path';
import { pathToFileURL } from 'node:url';
import { WINDOW_CONTROL, arrangeAndVerify, processWindows, workArea } from './win32.js';

const execFileAsync = promisify(execFile);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Edge first: it ships with Windows, so the usual machine has it even when the
// user never installed Chrome. An explicit browser choice never falls back.
const BROWSERS = [
  { name: 'edge', label: 'Microsoft Edge', exe: 'msedge.exe', vendor: 'Microsoft', product: 'Edge' },
  { name: 'chrome', label: 'Google Chrome', exe: 'chrome.exe', vendor: 'Google', product: 'Chrome' },
];

function installRoots() {
  return [process.env['ProgramFiles(x86)'], process.env.ProgramFiles, process.env.LOCALAPPDATA].filter(Boolean);
}

export function detectBrowsers() {
  const found = [];
  for (const browser of BROWSERS) {
    const path = installRoots()
      .map((root) => join(root, browser.vendor, browser.product, 'Application', browser.exe))
      .find((candidate) => existsSync(candidate));
    if (path) found.push({ name: browser.name, label: browser.label, path });
  }
  return found;
}

function pickBrowser(requested) {
  const found = detectBrowsers();
  if (requested && requested !== 'auto') {
    const match = found.find((browser) => browser.name === requested);
    if (match) return match;
    const label = BROWSERS.find((browser) => browser.name === requested)?.label ?? requested;
    throw new Error(
      `${label} was not found in the usual install locations. Install it, or pass browser:"auto" to use whichever of Edge or Chrome is present.`,
    );
  }
  if (!found.length) {
    throw new Error(
      'No Chromium browser (Edge or Chrome) was found for snip_view. Install one, or capture the target window directly with target:"window".',
    );
  }
  return found[0];
}

async function pageUrl({ file, url, html }, dir) {
  const given = [file, url, html].filter((value) => value !== undefined && value !== null && value !== '');
  if (given.length !== 1) throw new Error('snip_view takes exactly one of file, url, or html.');
  if (given[0] === html) {
    const target = join(dir, 'page.html');
    await writeFile(target, html, 'utf8');
    return pathToFileURL(target).href;
  }
  if (given[0] === file) {
    const absolute = resolvePath(file);
    await access(absolute);
    return pathToFileURL(absolute).href;
  }
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`url is not a valid absolute URL: ${url}`);
  }
  if (!['http:', 'https:', 'file:'].includes(parsed.protocol)) {
    throw new Error(`snip_view opens http, https, and file URLs only (got ${parsed.protocol}).`);
  }
  return parsed.href;
}

// A browser process owns several visible helper windows (tooltips, message
// windows). The page window is the one with a title and the largest area.
function mainWindow(windows) {
  const usable = windows.filter((win) => !win.minimized && win.width > 0 && win.height > 0);
  const titled = usable.filter((win) => win.title);
  const pool = titled.length ? titled : usable;
  return pool.sort((a, b) => b.width * b.height - a.width * a.height)[0] ?? null;
}

async function waitForWindow(marker, image, exitOf, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let previous = null;
  let stable = 0;
  let seenPids = [];
  while (Date.now() < deadline) {
    const owner = await processWindows({ marker, image });
    seenPids = owner.pids;
    const win = mainWindow(owner.windows);
    if (win) {
      const same =
        previous &&
        previous.hwnd === win.hwnd &&
        previous.left === win.left &&
        previous.top === win.top &&
        previous.width === win.width &&
        previous.height === win.height;
      if (same) {
        stable += 1;
        if (stable >= 1) return win;
      } else {
        stable = 0;
      }
      previous = win;
    } else {
      previous = null;
      stable = 0;
    }
    await sleep(200);
  }
  const exit = exitOf();
  const why = exit && !seenPids.length ? ` The launcher exited with code ${exit.code ?? exit.signal}.` : '';
  throw new Error(
    `The viewer window did not appear within ${timeoutMs} ms.${why} The browser took too long to start; retry with a larger wait_ms.`,
  );
}

// Only the temporary browser tree is killed: every process is selected by the
// unique profile directory on its command line, so the user's own browser
// windows (different profile) are never touched.
async function killMarked(marker, image) {
  const { pids } = await processWindows({ marker, image });
  for (const pid of pids) {
    try {
      await execFileAsync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, timeout: 15000 });
    } catch {
      // already gone
    }
  }
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const { pids: remaining } = await processWindows({ marker, image });
    if (!remaining.length) return;
    for (const pid of remaining) {
      try {
        await execFileAsync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, timeout: 15000 });
      } catch {
        // already gone
      }
    }
    await sleep(200);
  }
}

async function stopViewer({ marker, image, dir, childPid }) {
  await killMarked(marker, image);
  if (childPid) {
    try {
      await execFileAsync('taskkill', ['/PID', String(childPid), '/T', '/F'], { windowsHide: true, timeout: 15000 });
    } catch {
      // already gone
    }
  }
  await rm(dir, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
}

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export async function openViewer({
  file,
  url,
  html,
  browser = 'auto',
  kiosk = false,
  waitMs = 1200,
  width,
  height,
} = {}) {
  if (!WINDOW_CONTROL) {
    throw new Error(
      'snip_view is Windows-only in this build. Pass target:"window" on Windows, or allow_desktop:true after the user consents to a desktop capture.',
    );
  }
  const chosen = pickBrowser(browser);
  const image = basename(chosen.path).toLowerCase();
  const dir = await mkdtemp(join(tmpdir(), 'snipaste-mcp-view-'));
  let child = null;
  try {
    const targetUrl = await pageUrl({ file, url, html }, dir);
    const area = await workArea();
    if (!area || !area.width || !area.height) throw new Error('Could not read the primary monitor work area.');

    const outerWidth = clamp(Math.round(width ?? area.width), 320, area.width);
    const outerHeight = clamp(Math.round(height ?? area.height), 240, area.height);
    const x = area.left + Math.max(0, Math.floor((area.width - outerWidth) / 2));
    const y = area.top + Math.max(0, Math.floor((area.height - outerHeight) / 2));

    const args = [
      `--user-data-dir=${join(dir, 'profile')}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-sync',
      '--disable-extensions',
    ];
    if (kiosk) {
      args.push('--kiosk', targetUrl);
    } else {
      args.push(`--app=${targetUrl}`, `--window-position=${x},${y}`, `--window-size=${outerWidth},${outerHeight}`);
    }

    let exitInfo = null;
    // windowsHide makes Chromium's first ShowWindow honor SW_HIDE, so the
    // browser starts without ever showing its window. It is a GUI process and
    // opens no console of its own, so there is nothing to hide.
    child = spawn(chosen.path, args, { stdio: 'ignore', windowsHide: false });
    child.once('exit', (code, signal) => {
      exitInfo = { code, signal };
    });
    child.once('error', (error) => {
      exitInfo = { error };
    });

    const win = await waitForWindow(dir, image, () => exitInfo, 20000);

    const placed = await arrangeAndVerify({
      hwnd: win.hwnd,
      mode: kiosk ? 'maximize' : 'keep',
      settleMs: waitMs,
    });

    return {
      pid: placed.pid,
      browser: chosen,
      url: targetUrl,
      hwnd: placed.hwnd,
      title: placed.title,
      rect: placed.capture,
      original: placed.original ?? placed.capture,
      samples: placed.samples,
      trimmed: placed.trimmed,
      placement: placed.placement,
      tempDir: dir,
      async close() {
        await stopViewer({ marker: dir, image, dir, childPid: child.pid });
      },
    };
  } catch (error) {
    try {
      await stopViewer({ marker: dir, image, dir, childPid: child?.pid });
    } catch {
      // best effort: the original error is the one worth reporting
    }
    throw error;
  }
}
