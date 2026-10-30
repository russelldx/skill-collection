import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, rm, readdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { WINDOW_CONTROL, workArea } from '../src/win32.js';
import { restartSnipaste } from '../src/snipaste.js';

const execFileAsync = promisify(execFile);
const root = fileURLToPath(new URL('..', import.meta.url));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const results = [];

if (!WINDOW_CONTROL) {
  console.log('SKIP: safe window capture is Windows-only in this build');
  process.exit(0);
}

function check(name, condition, detail = '') {
  results.push({ name, ok: Boolean(condition), detail });
  console.log(`${condition ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function textOf(result) {
  return (result.content ?? []).filter((block) => block.type === 'text').map((block) => block.text).join('\n');
}

function imageOf(result) {
  return (result.content ?? []).find((block) => block.type === 'image');
}

function pngSize(buffer) {
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function captureRectOf(text) {
  const match = text.match(/Capture rect (\d+)x(\d+) at (-?\d+),(-?\d+)/);
  if (!match) return null;
  return { width: Number(match[1]), height: Number(match[2]), left: Number(match[3]), top: Number(match[4]) };
}

const FORM_SCRIPT = String.raw`param(
  [Parameter(Mandatory = $true)][string]$Title,
  [int]$Left = 160,
  [int]$Top = 160,
  [int]$Width = 700,
  [int]$Height = 500,
  [switch]$Topmost
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class SnipTestDpi {
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    public static void Init() { try { SetProcessDpiAwarenessContext(new IntPtr(-4)); } catch { } }
}
"@
[SnipTestDpi]::Init()

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.AutoScaleMode = [System.Windows.Forms.AutoScaleMode]::None
$form.Text = $Title
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Location = New-Object System.Drawing.Point($Left, $Top)
$form.Size = New-Object System.Drawing.Size($Width, $Height)
$form.BackColor = [System.Drawing.Color]::FromArgb(18, 32, 54)
$form.ForeColor = [System.Drawing.Color]::White
$label = New-Object System.Windows.Forms.Label
$label.Text = $Title
$label.Dock = [System.Windows.Forms.DockStyle]::Fill
$label.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$label.Font = New-Object System.Drawing.Font('Segoe UI', 20)
$form.Controls.Add($label)

if ($Topmost) {
  $form.TopMost = $true
  $timer = New-Object System.Windows.Forms.Timer
  $timer.Interval = 50
  $timer.Add_Tick({
    $form.TopMost = $false
    $form.TopMost = $true
  })
  $timer.Start()
}

[void]$form.ShowDialog()
`;

const workDir = await mkdtemp(join(tmpdir(), 'snipaste-mcp-test-'));
const formScript = join(workDir, 'form.ps1');
await writeFile(formScript, FORM_SCRIPT, 'utf8');

const children = new Set();

function startForm({ title, left, top, width, height, topmost = false }) {
  const args = [
    '-NoProfile',
    '-STA',
    // windowsHide stays false: STARTUPINFO's SW_HIDE would also hide the form.
    '-WindowStyle',
    'Hidden',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    formScript,
    '-Title',
    title,
    '-Left',
    String(left),
    '-Top',
    String(top),
    '-Width',
    String(width),
    '-Height',
    String(height),
  ];
  if (topmost) args.push('-Topmost');
  const child = spawn('powershell', args, { stdio: 'ignore', windowsHide: false });
  child.on('error', () => {});
  children.add(child.pid);
  return child;
}

async function killTree(pid) {
  if (!pid) return;
  children.delete(pid);
  await execFileAsync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true }).catch(() => {});
}

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [join(root, 'src', 'server.js')],
  cwd: root,
  env: { ...process.env },
  stderr: 'inherit',
});
const client = new Client({ name: 'snipaste-mcp-e2e', version: '0.0.0' });

const call = (name, args = {}) => client.callTool({ name, arguments: args });

async function windowsMatching(title) {
  const result = await call('snip_windows', { app: 'powershell', title, limit: 20 });
  if (result.isError) throw new Error(textOf(result));
  return JSON.parse(textOf(result)).windows ?? [];
}

async function waitForWindow(title, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const windows = await windowsMatching(title);
    if (windows.length) return windows[0];
    await sleep(250);
  }
  throw new Error(`test window "${title}" did not appear within ${timeoutMs} ms`);
}

async function viewerProcesses() {
  const script =
    "@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" | " +
    "Where-Object { $_.CommandLine -like '*snipaste-mcp-view-*' }).Count";
  const { stdout } = await execFileAsync('powershell', ['-NoProfile', '-NonInteractive', '-Command', script], {
    windowsHide: true,
    timeout: 20000,
  });
  return Number(stdout.trim()) || 0;
}

async function viewerTempDirs() {
  const entries = await readdir(tmpdir()).catch(() => []);
  return new Set(entries.filter((entry) => entry.startsWith('snipaste-mcp-view-')));
}

const stamp = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const titleB = `SNIPTEST-B-${stamp}`;
const titleA = `SNIPTEST-A-${stamp}`;
const area = await workArea();
console.log(`   work area: ${area.width}x${area.height} at ${area.left},${area.top}`);
const formLeft = area.left + 160;
const formTop = area.top + 160;

let childB = null;
let childA = null;

try {
  await client.connect(transport);

  const tools = await client.listTools();
  const names = tools.tools.map((tool) => tool.name).sort();
  check(
    'tools/list returns capture, ocr, status, view, windows',
    names.join(',') === 'snip_capture,snip_ocr,snip_status,snip_view,snip_windows',
    names.join(','),
  );
  const captureTool = tools.tools.find((tool) => tool.name === 'snip_capture');
  check(
    'snip_capture defaults to target=window with allow_desktop=false',
    captureTool?.inputSchema?.properties?.target?.default === 'window' &&
      captureTool?.inputSchema?.properties?.allow_desktop?.default === false,
  );

  // Case 7 comes first so Snipaste is provably not needed for a refusal.
  const runningBefore = JSON.parse(textOf(await call('snip_status'))).running;
  let started = Date.now();
  const ocrDesktop = await call('snip_ocr', { target: 'fullscreen', timeout_ms: 6000 });
  const ocrDesktopElapsed = Date.now() - started;
  check(
    'snip_ocr fullscreen without allow_desktop is refused without waiting for OCR',
    ocrDesktop.isError === true && /Refused/.test(textOf(ocrDesktop)) && ocrDesktopElapsed < 3000,
    `${ocrDesktopElapsed} ms: ${textOf(ocrDesktop).slice(0, 90)}`,
  );
  const runningAfter = JSON.parse(textOf(await call('snip_status'))).running;
  check(
    'the refusal did not start Snipaste',
    runningBefore || !runningAfter,
    `running before=${runningBefore} after=${runningAfter}`,
  );

  const captureDesktop = await call('snip_capture', { target: 'fullscreen' });
  check(
    'snip_capture fullscreen without allow_desktop is refused',
    captureDesktop.isError === true && /allow_desktop:true/.test(textOf(captureDesktop)) && /snip_windows/.test(textOf(captureDesktop)),
    textOf(captureDesktop).slice(0, 90),
  );

  const noSelector = await call('snip_capture', {});
  check(
    'snip_capture window without a selector is refused',
    noSelector.isError === true && /app, title, or pid/.test(textOf(noSelector)),
    textOf(noSelector).slice(0, 90),
  );

  const status = JSON.parse(textOf(await call('snip_status')));
  check('snip_status reports window_control=windows', status.window_control === 'windows', String(status.window_control));
  check('snip_status reports the detected browsers', Array.isArray(status.browsers) && status.browsers.length > 0, JSON.stringify(status.browsers));
  check(
    'snip_status reports the foreground window',
    Boolean(status.foreground?.app),
    JSON.stringify(status.foreground),
  );

  // Case 1: the test window is listed and its pid matches the launcher.
  // A Snipaste left behind by an interrupted run can silently drop the next
  // snip, so start the capture cases from a freshly launched instance.
  await restartSnipaste().catch(() => {});
  childB = startForm({ title: titleB, left: formLeft, top: formTop, width: 700, height: 500 });
  const before = await waitForWindow(titleB);
  check(
    'snip_windows lists the test window',
    before.title === titleB && before.pid === childB.pid,
    `${before.app} "${before.title}" pid=${before.pid}`,
  );
  console.log(`   window rect before: ${before.rect.width}x${before.rect.height} at ${before.rect.left},${before.rect.top}`);

  // Case 2: maximize, capture exactly the work area, then restore.
  started = Date.now();
  const maximized = await call('snip_capture', {
    app: 'powershell',
    title: titleB,
    mode: 'maximize',
    include_image: true,
  });
  const maximizeElapsed = Date.now() - started;
  const maxImage = imageOf(maximized);
  const maxText = textOf(maximized);
  check('window maximize capture returns an image', Boolean(maxImage), `${maximizeElapsed} ms ${maxText.split('\n')[0]}`);
  if (maxImage) {
    const size = pngSize(Buffer.from(maxImage.data, 'base64'));
    const rect = captureRectOf(maxText);
    if (/Trimmed from /.test(maxText)) {
      // A notification banner can take a corner while the test runs; the tool
      // then returns the largest verified sub-rectangle instead of the banner.
      check(
        'a trimmed maximize capture stays inside the work area',
        Boolean(rect) &&
          rect.left >= area.left &&
          rect.top >= area.top &&
          rect.left + rect.width <= area.left + area.width &&
          rect.top + rect.height <= area.top + area.height &&
          rect.width * rect.height >= area.width * area.height * 0.6,
        `${rect?.width}x${rect?.height} at ${rect?.left},${rect?.top} of ${area.width}x${area.height}`,
      );
    } else {
      check(
        'maximized window captures the work area exactly',
        Math.abs(size.width - area.width) <= 1 && Math.abs(size.height - area.height) <= 1,
        `${size.width}x${size.height} vs ${area.width}x${area.height}`,
      );
    }
    check(
      'image size matches the verified capture rectangle',
      rect && rect.width === size.width && rect.height === size.height,
      rect ? `${rect.width}x${rect.height}` : 'no capture rect in text',
    );
  }
  check('maximize capture reports the window was restored', /Window restored: yes/.test(maxText), maxText.split('\n')[2] ?? '');

  const afterMaximize = (await windowsMatching(titleB))[0];
  check(
    'the window is restored to its original rectangle',
    Boolean(afterMaximize) &&
      !afterMaximize.maximized &&
      Math.abs(afterMaximize.rect.left - before.rect.left) <= 3 &&
      Math.abs(afterMaximize.rect.top - before.rect.top) <= 3 &&
      Math.abs(afterMaximize.rect.width - before.rect.width) <= 3 &&
      Math.abs(afterMaximize.rect.height - before.rect.height) <= 3,
    afterMaximize ? `${afterMaximize.rect.width}x${afterMaximize.rect.height} at ${afterMaximize.rect.left},${afterMaximize.rect.top}, maximized=${afterMaximize.maximized}` : 'missing',
  );

  // Case 3: keep mode insets the visible frame by 8px per side (rounded corners).
  const kept = await call('snip_capture', { app: 'powershell', title: titleB, mode: 'keep', include_image: true });
  const keepImage = imageOf(kept);
  const keepText = textOf(kept);
  check('window keep capture returns an image', Boolean(keepImage), keepText.split('\n')[0]);
  const keepRect = captureRectOf(keepText);
  if (keepImage && keepRect) {
    const size = pngSize(Buffer.from(keepImage.data, 'base64'));
    check('keep image size matches the verified capture rectangle', size.width === keepRect.width && size.height === keepRect.height, `${size.width}x${size.height}`);
    const shrinkX = before.rect.width - keepRect.width;
    const shrinkY = before.rect.height - keepRect.height;
    if (/Trimmed from /.test(keepText)) {
      check(
        'a trimmed keep capture stays inside the window rectangle',
        keepRect.left >= before.rect.left &&
          keepRect.top >= before.rect.top &&
          keepRect.left + keepRect.width <= before.rect.left + before.rect.width &&
          keepRect.top + keepRect.height <= before.rect.top + before.rect.height &&
          keepRect.width >= 320 &&
          keepRect.height >= 200,
        `${keepRect.width}x${keepRect.height} at ${keepRect.left},${keepRect.top}`,
      );
    } else {
      check(
        'keep mode trims at least the 8px rounded-corner inset',
        shrinkX >= 16 && shrinkY >= 16 && shrinkX <= 96 && shrinkY <= 96,
        `shrunk by ${shrinkX}/${shrinkY} px`,
      );
    }
    check(
      'keep capture rectangle stays inside the window rectangle',
      keepRect.left >= before.rect.left &&
        keepRect.top >= before.rect.top &&
        keepRect.left + keepRect.width <= before.rect.left + before.rect.width &&
        keepRect.top + keepRect.height <= before.rect.top + before.rect.height,
      `${keepRect.width}x${keepRect.height} at ${keepRect.left},${keepRect.top}`,
    );
  }

  // Case 4: area inside the window works, area outside is refused, maximize is refused.
  const inside = {
    x: before.rect.left + 120,
    y: before.rect.top + 120,
    width: 320,
    height: 200,
  };
  const savedPath = join(workDir, 'area.png');
  const areaShot = await call('snip_capture', {
    target: 'area',
    app: 'powershell',
    title: titleB,
    ...inside,
    save_path: savedPath,
    include_image: true,
  });
  const areaImage = imageOf(areaShot);
  const areaText = textOf(areaShot);
  if (/Trimmed from /.test(areaText)) {
    const areaSize = areaImage ? pngSize(Buffer.from(areaImage.data, 'base64')) : null;
    check(
      'a trimmed area capture stays inside the requested area',
      Boolean(areaImage) &&
        areaSize.width >= 320 &&
        areaSize.height >= 200 &&
        areaSize.width * areaSize.height >= 320 * 200 * 0.6 &&
        areaText.includes('Capture rect'),
      areaText.split('\n')[0],
    );
  } else {
    check(
      'area capture inside the window returns exactly 320x200',
      Boolean(areaImage) && pngSize(Buffer.from(areaImage.data, 'base64')).width === 320 && pngSize(Buffer.from(areaImage.data, 'base64')).height === 200,
      areaText.split('\n')[0],
    );
  }
  const areaAgain = await call('snip_capture', {
    target: 'area',
    app: 'powershell',
    title: titleB,
    ...inside,
    save_path: savedPath,
    overwrite: false,
    include_image: false,
  });
  check('overwrite=false protects an existing save_path', areaAgain.isError === true && /already exists/.test(textOf(areaAgain)), textOf(areaAgain).slice(0, 80));

  const outside = await call('snip_capture', {
    target: 'area',
    app: 'powershell',
    title: titleB,
    x: before.rect.left - 400,
    y: before.rect.top + 20,
    width: 200,
    height: 100,
  });
  check(
    'area outside the window is refused and names the window',
    outside.isError === true && /not fully inside/.test(textOf(outside)) && /powershell/.test(textOf(outside)),
    textOf(outside).slice(0, 100),
  );

  const areaMaximize = await call('snip_capture', {
    target: 'area',
    app: 'powershell',
    title: titleB,
    ...inside,
    mode: 'maximize',
  });
  check(
    'area with mode=maximize is refused',
    areaMaximize.isError === true && /only works with mode "keep"/.test(textOf(areaMaximize)),
    textOf(areaMaximize).slice(0, 90),
  );

  // Case 5: a topmost window over the target makes keep mode refuse and name it.
  childA = startForm({
    title: titleA,
    left: before.rect.left + 30,
    top: before.rect.top + 30,
    width: 620,
    height: 420,
    topmost: true,
  });
  await waitForWindow(titleA);
  const covered = await call('snip_capture', {
    app: 'powershell',
    title: titleB,
    mode: 'keep',
    settle_ms: 1500,
  });
  const coveredText = textOf(covered);
  check(
    'a covered window is refused and the overlay is named',
    covered.isError === true && /not fully visible/.test(coveredText) && coveredText.includes(titleA) && !imageOf(covered),
    coveredText.slice(0, 140),
  );
  await killTree(childA.pid);
  childA = null;
  await sleep(500);

  // Case 6: snip_view renders HTML in a dedicated browser window and cleans up.
  const dirsBefore = await viewerTempDirs();
  const html =
    '<!doctype html><meta charset="utf-8"><title>sniptest</title>' +
    '<body style="margin:0;background:#123;color:#fff;font:48px Segoe UI">snip_view test</body>';
  started = Date.now();
  const viewed = await call('snip_view', { html, wait_ms: 1500, include_image: true });
  const viewImage = imageOf(viewed);
  const viewText = textOf(viewed);
  const viewElapsed = Date.now() - started;
  check('snip_view returns an image', Boolean(viewImage), `${viewElapsed} ms ${viewText.split('\n')[0]}`);
  check(
    'snip_view reports that the temporary browser was closed',
    /temporary browser is closed/.test(viewText),
    viewText.split('\n')[0],
  );
  const viewRect = captureRectOf(viewText);
  if (viewImage && viewRect) {
    const size = pngSize(Buffer.from(viewImage.data, 'base64'));
    check('snip_view image size matches the verified capture rectangle', size.width === viewRect.width && size.height === viewRect.height, `${size.width}x${size.height}`);
    if (/Trimmed from /.test(viewText)) {
      check(
        'a trimmed snip_view capture stays inside the work area',
        viewRect.left >= area.left &&
          viewRect.top >= area.top &&
          viewRect.left + viewRect.width <= area.left + area.width &&
          viewRect.top + viewRect.height <= area.top + area.height &&
          viewRect.width >= area.width * 0.6 &&
          viewRect.height >= area.height * 0.6,
        `${viewRect.width}x${viewRect.height} at ${viewRect.left},${viewRect.top} of ${area.width}x${area.height}`,
      );
    } else {
      check(
        'snip_view fills most of the work area',
        viewRect.width >= area.width * 0.95 && viewRect.height >= area.height * 0.9,
        `${viewRect.width}x${viewRect.height} of ${area.width}x${area.height}`,
      );
    }
  }
  await sleep(500);
  const dirsAfter = await viewerTempDirs();
  const leakedDirs = [...dirsAfter].filter((dir) => !dirsBefore.has(dir));
  check('snip_view leaves no temporary profile directory', leakedDirs.length === 0, leakedDirs.join(', '));
  check('no temporary viewer browser is left running', (await viewerProcesses()) === 0);
} finally {
  for (const pid of [...children]) await killTree(pid).catch(() => {});
  await client.close().catch(() => {});
  await rm(workDir, { recursive: true, force: true }).catch(() => {});
}

const failed = results.filter((result) => !result.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
