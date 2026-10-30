import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import { stat, unlink, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

const execFileAsync = promisify(execFile);
const IS_WIN = process.platform === 'win32';
const IS_MAC = process.platform === 'darwin';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let exeCache = null;
let versionCache = null;

const EXE_NAME = IS_WIN ? 'Snipaste.exe' : 'Snipaste';

function pathCandidates() {
  const list = [];
  if (process.env.SNIPASTE_PATH) list.push(process.env.SNIPASTE_PATH);
  if (IS_WIN) {
    const { ProgramFiles, LOCALAPPDATA } = process.env;
    const pf86 = process.env['ProgramFiles(x86)'];
    if (ProgramFiles) list.push(join(ProgramFiles, 'Snipaste', 'Snipaste.exe'));
    if (pf86) list.push(join(pf86, 'Snipaste', 'Snipaste.exe'));
    if (LOCALAPPDATA) list.push(join(LOCALAPPDATA, 'Programs', 'Snipaste', 'Snipaste.exe'));
  } else if (IS_MAC) {
    list.push('/Applications/Snipaste.app/Contents/MacOS/Snipaste');
  }
  return list;
}

function cacheFile() {
  if (IS_WIN && process.env.LOCALAPPDATA) return join(process.env.LOCALAPPDATA, 'snipaste-mcp', 'config.json');
  if (IS_MAC) return join(homedir(), 'Library', 'Application Support', 'snipaste-mcp', 'config.json');
  const base = process.env.XDG_CONFIG_HOME || join(homedir(), '.config');
  return join(base, 'snipaste-mcp', 'config.json');
}

async function readCachedExe() {
  try {
    const parsed = JSON.parse(await readFile(cacheFile(), 'utf8'));
    const stored = typeof parsed?.executablePath === 'string' ? parsed.executablePath : null;
    return stored && existsSync(stored) ? stored : null;
  } catch {
    return null;
  }
}

async function remember(exe) {
  exeCache = exe;
  try {
    const file = cacheFile();
    await mkdir(dirname(file), { recursive: true });
    await writeFile(file, `${JSON.stringify({ executablePath: exe }, null, 2)}\n`);
  } catch {
    // best effort: the cache only saves a lookup, never blocks a capture
  }
  return exe;
}

const SCAN_SKIP = new Set(['node_modules', 'appdata', '$recycle.bin', 'windows', 'system volume information']);

// Portable Snipaste has no registry entry and may live anywhere, so a cold start
// (process not running) cannot be resolved by asking the running process. Search
// the usual download spots, bounded by depth/time/entry budgets.
async function scanForExe(maxDepth = 3, budgetMs = 2500, maxEntries = 4000) {
  if (!IS_WIN) return null;
  const roots = ['Desktop', 'Downloads', 'Documents'].map((name) => join(homedir(), name));
  if (process.env.LOCALAPPDATA) roots.push(join(process.env.LOCALAPPDATA, 'Programs'));
  const queue = roots.filter((root) => existsSync(root)).map((dir) => ({ dir, depth: 0 }));
  const deadline = Date.now() + budgetMs;
  let visited = 0;
  while (queue.length) {
    if (Date.now() > deadline || visited >= maxEntries) return null;
    const { dir, depth } = queue.shift();
    visited += 1;
    let entries;
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.isFile() && entry.name.toLowerCase() === EXE_NAME.toLowerCase()) return join(dir, entry.name);
      if (!entry.isDirectory() || depth >= maxDepth) continue;
      const lower = entry.name.toLowerCase();
      if (lower.startsWith('.') || SCAN_SKIP.has(lower)) continue;
      queue.push({ dir: join(dir, entry.name), depth: depth + 1 });
    }
  }
  return null;
}

async function fromPath() {
  try {
    const cmd = IS_WIN ? 'where' : 'which';
    const args = IS_WIN ? ['Snipaste.exe'] : ['snipaste'];
    const { stdout } = await execFileAsync(cmd, args, { windowsHide: true });
    return stdout.split(/\r?\n/).map((s) => s.trim()).find(Boolean) ?? null;
  } catch {
    return null;
  }
}

async function fromRunningProcess() {
  try {
    if (IS_WIN) {
      const { stdout } = await execFileAsync('powershell', [
        '-NoProfile',
        '-NonInteractive',
        '-Command',
        'Get-Process Snipaste -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Path',
      ], { windowsHide: true, timeout: 15000 });
      return stdout.trim() || null;
    }
    if (IS_MAC) {
      const { stdout } = await execFileAsync('pgrep', ['-f', 'Snipaste.app/Contents/MacOS/Snipaste']);
      const pid = stdout.split(/\s+/).find(Boolean);
      if (pid) {
        const ps = await execFileAsync('ps', ['-o', 'comm=', '-p', pid]);
        return ps.stdout.trim() || null;
      }
    }
  } catch {
    // swallow: not running or lookup unavailable
  }
  return null;
}

export async function resolveExecutable() {
  if (exeCache) return exeCache;
  for (const candidate of pathCandidates()) {
    if (existsSync(candidate)) return remember(candidate);
  }
  const onPath = await fromPath();
  if (onPath && existsSync(onPath)) return remember(onPath);
  const cached = await readCachedExe();
  if (cached) return remember(cached);
  const running = await fromRunningProcess();
  if (running && existsSync(running)) return remember(running);
  const scanned = await scanForExe();
  if (scanned) return remember(scanned);
  throw new Error(
    'Snipaste executable not found. Set SNIPASTE_PATH to Snipaste.exe, or install Snipaste / add it to PATH.',
  );
}

export async function isRunning() {
  try {
    if (IS_WIN) {
      const { stdout } = await execFileAsync('tasklist', [
        '/FI', 'IMAGENAME eq Snipaste.exe', '/NH',
      ], { windowsHide: true, timeout: 15000 });
      return /snipaste\.exe/i.test(stdout);
    }
    await execFileAsync('pgrep', ['-x', 'Snipaste']);
    return true;
  } catch {
    return false;
  }
}

let ensuredAt = 0;

async function ensureRunning(exe) {
  if (Date.now() - ensuredAt < 5000) return;
  if (!(await isRunning())) {
    const child = spawn(exe, [], { detached: true, stdio: 'ignore', windowsHide: true });
    child.unref();
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      if (await isRunning()) break;
      await sleep(150);
    }
    if (!(await isRunning())) {
      throw new Error('Snipaste is not running and could not be started. Start it manually, then retry.');
    }
    // The process shows up in tasklist before its snip handler is ready; a
    // command sent during that gap is dropped without any error.
    await sleep(1200);
  }
  ensuredAt = Date.now();
}

function targetArgs({ target, area }) {
  switch (target) {
    case 'fullscreen':
      return ['--full'];
    case 'active_screen':
      return ['--active-screen'];
    case 'active_window':
      return ['--active-window'];
    case 'last':
      return ['--last'];
    case 'area':
      // Snipaste silently ignores an area it cannot parse, so a typo here would look
      // like an 8s timeout instead of a bug. Reject it loudly instead.
      for (const key of ['x', 'y', 'width', 'height']) {
        if (!Number.isFinite(area?.[key])) throw new Error(`area.${key} must be a finite number, got ${area?.[key]}`);
      }
      return ['--area', String(area.x), String(area.y), String(area.width), String(area.height)];
    default:
      throw new Error(`Unknown target: ${target}`);
  }
}

function defaultOutputPath() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 23);
  return join(tmpdir(), 'snipaste-mcp', `snap-${stamp}-${randomUUID().slice(0, 8)}.png`);
}

function pngSize(buffer) {
  if (buffer.length < 24 || buffer.readUInt32BE(0) !== 0x89504e47) {
    throw new Error('Snipaste produced a file that is not a PNG');
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

async function waitForFile(file, timeoutMs, hasFailed) {
  const deadline = Date.now() + timeoutMs;
  let previousSize = -1;
  while (Date.now() < deadline) {
    const failure = hasFailed?.();
    if (failure) throw failure;
    try {
      const info = await stat(file);
      if (info.size > 0) {
        if (info.size === previousSize) return;
        previousSize = info.size;
      }
    } catch {
      // file not written yet
    }
    await sleep(40);
  }
  try {
    const info = await stat(file);
    if (info.size > 0) return;
  } catch {
    // fall through
  }
  throw new Error(
    `Snipaste did not finish writing ${file} within ${timeoutMs}ms. Check that no Snipaste selection window ` +
      'is waiting for input, and note that PRO-only options (active_window, shadow) are silently ignored by the free build.',
  );
}

// The free build does not reject PRO-only -o modes, it just never finishes the
// request and stops answering later snip commands, so the only recovery is a restart.
export async function restartSnipaste(exe) {
  const target = exe ?? (await resolveExecutable());
  try {
    if (IS_WIN) await execFileAsync('taskkill', ['/IM', 'Snipaste.exe', '/F'], { windowsHide: true });
    else await execFileAsync('pkill', ['-x', 'Snipaste']);
  } catch {
    // not running
  }
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline && (await isRunning())) await sleep(150);
  ensuredAt = 0;
  await ensureRunning(target);
  return target;
}

export async function capture({
  target = 'fullscreen',
  area,
  delay = 0,
  shadow = false,
  savePath,
  overwrite = true,
  timeoutMs = 8000,
}) {
  const exe = await resolveExecutable();
  await ensureRunning(exe);

  const out = savePath ?? defaultOutputPath();
  if (savePath) {
    await mkdir(dirname(savePath), { recursive: true }).catch(() => {});
    if (existsSync(savePath) && !overwrite) {
      throw new Error(`${savePath} already exists and overwrite is false; it was left untouched`);
    }
  } else {
    await mkdir(dirname(out), { recursive: true });
  }
  await unlink(out).catch(() => {});

  const args = ['snip', ...targetArgs({ target, area })];
  if (delay > 0) args.push('--delay', String(delay));
  if (shadow) args.push('--shadow');
  args.push('-o', out);

  const startedAt = Date.now();
  let exitState = null;
  const child = spawn(exe, args, { stdio: 'ignore', windowsHide: true });
  child.on('error', (error) => {
    exitState = { error };
  });
  child.on('exit', (code, signal) => {
    exitState = { code, signal };
  });

  const hasFailed = () => {
    if (exitState?.error) return exitState.error;
    if (exitState && exitState.code !== 0 && exitState.code !== null) {
      return new Error(`Snipaste exited with code ${exitState.code}`);
    }
    return null;
  };

  await waitForFile(out, delay * 1000 + timeoutMs, hasFailed);

  const buffer = await readFile(out);
  const { width, height } = pngSize(buffer);
  return { path: out, width, height, bytes: buffer.length, elapsedMs: Date.now() - startedAt, buffer };
}

// Window rects in this project are {left, top, width, height}; Snipaste's --area wants
// {x, y, width, height}. Funnel every verified-rect capture through here so the two
// shapes can never drift apart again.
export function captureWithPreparedArea(rect, { delay = 0, savePath, overwrite = true, timeoutMs = 8000 } = {}) {
  return capture({
    target: 'area',
    area: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
    delay,
    savePath,
    overwrite,
    timeoutMs,
  });
}

const PS_PREAMBLE = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8\n";

async function runPowerShell(script, env = {}, timeout = 20000) {
  const { stdout } = await execFileAsync('powershell', [
    '-NoProfile', '-NonInteractive', '-Command', script,
  ], { windowsHide: true, timeout, maxBuffer: 8 * 1024 * 1024, encoding: 'utf8', env: { ...process.env, ...env } });
  return stdout.replace(/^\uFEFF/, '');
}

async function readClipboardText() {
  if (IS_MAC) {
    try {
      const { stdout } = await execFileAsync('pbpaste', [], { maxBuffer: 8 * 1024 * 1024 });
      return stdout;
    } catch {
      return '';
    }
  }
  if (!IS_WIN) return '';
  const script = `${PS_PREAMBLE}try { $t = Get-Clipboard -Raw -ErrorAction Stop } catch { $t = '' }\nif ($null -eq $t) { $t = '' }\n[Console]::Write($t)\n`;
  try {
    return await runPowerShell(script);
  } catch {
    return '';
  }
}

function sha256(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

async function waitForClipboardChange(beforeHash, timeoutMs) {
  if (IS_MAC) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const text = await readClipboardText();
      if (sha256(text) !== beforeHash) return { text, changed: true };
      await sleep(120);
    }
    return { text: await readClipboardText(), changed: false };
  }
  // One PowerShell process polls internally, so the ~0.7s startup is paid once.
  const script = `${PS_PREAMBLE}
$deadline = (Get-Date).AddMilliseconds([int]$env:SNIP_WAIT_MS)
while ((Get-Date) -lt $deadline) {
  $t = ''
  try { $t = Get-Clipboard -Raw -ErrorAction Stop } catch { }
  if ($null -eq $t) { $t = '' }
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $hash = -join ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($t)) | ForEach-Object { $_.ToString('x2') })
  if ($hash -ne $env:SNIP_BEFORE_HASH) { [Console]::Write($t); exit 0 }
  Start-Sleep -Milliseconds 100
}
exit 3
`;
  try {
    const text = await runPowerShell(script, {
      SNIP_WAIT_MS: String(Math.max(500, timeoutMs)),
      SNIP_BEFORE_HASH: beforeHash,
    }, timeoutMs + 20000);
    return { text, changed: true };
  } catch (error) {
    if (error.code === 3) {
      return { text: await readClipboardText(), changed: false };
    }
    throw error;
  }
}

export async function ocr({ target = 'fullscreen', area, delay = 0, timeoutMs = 8000 }) {
  if (!IS_WIN && !IS_MAC) throw new Error('OCR mode currently supports Windows and macOS only');
  const exe = await resolveExecutable();
  await ensureRunning(exe);

  const beforeHash = sha256(await readClipboardText());

  const args = ['snip', ...targetArgs({ target, area })];
  if (delay > 0) args.push('--delay', String(delay));
  args.push('-o', 'ocr_clipboard');

  const startedAt = Date.now();
  const child = spawn(exe, args, { stdio: 'ignore', windowsHide: true });
  const spawnFailure = new Promise((_, reject) => child.once('error', reject));

  const result = await Promise.race([
    waitForClipboardChange(beforeHash, delay * 1000 + timeoutMs),
    spawnFailure,
  ]);
  const elapsedMs = Date.now() - startedAt;
  if (result.changed) return { text: result.text, changed: true, elapsedMs };
  const recovered = await restartSnipaste(exe).then(
    () => true,
    () => false,
  );
  return { text: result.text, changed: false, elapsedMs, recovered };
}

export async function status() {
  const exe = await resolveExecutable().catch((error) => ({ error }));
  if (exe?.error) {
    return { found: false, running: false, error: exe.error.message, platform: process.platform };
  }
  const running = await isRunning();
  if (!versionCache) {
    try {
      versionCache = IS_WIN
        ? (await runPowerShell(`${PS_PREAMBLE}(Get-Item -LiteralPath $env:SNIP_EXE).VersionInfo.FileVersion`, { SNIP_EXE: exe })).trim()
        : null;
    } catch {
      versionCache = null;
    }
  }
  return { found: true, running, executable: exe, version: versionCache, platform: process.platform };
}
