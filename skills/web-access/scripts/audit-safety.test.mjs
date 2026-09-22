import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

// Copy sources into an isolated fixture. Never import executable entry points:
// check-deps would create config/start a proxy; cdp-proxy would listen on a port.
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'web-access-audit-'));
after(() => fs.rmSync(fixture, { recursive: true, force: true }));
const sourceDir = path.dirname(fileURLToPath(import.meta.url));
const sources = {};
for (const file of ['check-deps.mjs', 'cdp-proxy.mjs', 'browser-discovery.mjs']) {
  const target = path.join(fixture, file);
  fs.copyFileSync(path.join(sourceDir, file), target);
  sources[file] = fs.readFileSync(target, 'utf8');
}

function section(file, start, end) {
  const source = sources[file];
  const from = source.indexOf(start);
  const to = source.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `Function boundaries changed in ${file}`);
  return source.slice(from, to);
}

const reportSource = section('check-deps.mjs', 'async function resolveAndReport(', '// --- main ---');
const ensureSource = section('check-deps.mjs', 'async function ensureProxy(', '// --- 输出浏览器选择结果');
const discoverSource = section('cdp-proxy.mjs', 'async function discoverChromePort(', 'function getWebSocketUrl(');

function sandbox(source, name, bindings) {
  const logs = [];
  const context = vm.createContext({
    console: { log: (...parts) => logs.push(parts.join(' ')) },
    ...bindings,
  });
  return { run: vm.runInContext(`${source}\n${name}`, context), logs };
}

function reporter(result, fallback = () => assert.fail('Unexpected fallback probe')) {
  return sandbox(reportSource, 'resolveAndReport', {
    selectBrowser: async () => result,
    knownBrowsers: () => [{ id: 'edge', label: 'Microsoft Edge' }],
    printAvailableHint: () => {},
    findFallbackPort: fallback,
  });
}

function discoverer(result, pinned = null) {
  return sandbox(discoverSource, 'discoverChromePort', {
    selectBrowser: async () => result,
    findFallbackPort: () => assert.fail('Explicit/pinned selection must not probe fallback'),
    BROWSER_OVERRIDE: 'edge',
    pinnedBrowserId: pinned,
    connectedBrowser: null,
    process: { pid: 43210 },
  });
}

test('checker keeps explicit mismatch strict even if a separate port could be available', async () => {
  const { run, logs } = reporter({ kind: 'mismatch', source: 'override', override: 'edge', detected: [] });
  const result = await run('edge');
  assert.equal(result.proceed, false);
  assert.equal(result.exitCode, 1);
  assert.match(logs.join('\n'), /用户已授权/);
  assert.match(logs.join('\n'), /相同 --browser 参数/);
  assert.match(logs.join('\n'), /不擅自修改浏览器配置/);
});

test('checker asks before persistence and leaves temporary selection available', async () => {
  const { run, logs } = reporter({ kind: 'ambiguous', detected: [] });
  assert.equal((await run(null)).exitCode, 2);
  assert.match(logs.join('\n'), /只有用户明确要求保存默认偏好/);
  assert.match(logs.join('\n'), /--browser <id>/);
});

test('checker preserves empty-discovery fallback without opening any real port', async () => {
  let calls = 0;
  const { run } = reporter({ kind: 'empty' }, async () => { calls++; return 9222; });
  assert.equal((await run(null)).proceed, true);
  assert.equal(calls, 1);
});

test('wrong-browser proxy reuse refuses without spawning or killing a process', async () => {
  const { run, logs } = sandbox(ensureSource, 'ensureProxy', {
    PROXY_PORT: 3456,
    httpGetJson: async () => ({ status: 'ok', connected: true, browser: { id: 'chrome', label: 'Chrome' } }),
    startProxyDetached: () => assert.fail('Must not spawn when another browser is connected'),
  });
  assert.equal(await run('edge', 'edge'), false);
  assert.match(logs.join('\n'), /脚本绝对路径和 PID/);
  assert.match(logs.join('\n'), /用户授权/);
  assert.match(logs.join('\n'), /勿按进程名批量终止/);
});

test('matching proxy reuse remains available', async () => {
  const { run } = sandbox(ensureSource, 'ensureProxy', {
    PROXY_PORT: 3456,
    httpGetJson: async () => ({ status: 'ok', connected: true, browser: { id: 'edge', label: 'Edge' } }),
    startProxyDetached: () => assert.fail('No restart needed'),
  });
  assert.equal(await run('edge', 'edge'), true);
});

test('proxy explicit mismatch does not fall back or claim a proven toggle failure', async () => {
  const { run } = discoverer({ kind: 'mismatch', source: 'override', override: 'edge' });
  await assert.rejects(run(), error => {
    assert.match(error.message, /用户已授权/);
    assert.match(error.message, /可能是远程调试未启用或 profile 不同/);
    return true;
  });
});

test('proxy rejects a changed pinned browser with precise, permission-bound guidance', async () => {
  const { run } = discoverer({ kind: 'ok', browser: { id: 'chrome' } }, 'edge');
  await assert.rejects(run(), error => {
    assert.match(error.message, /PID 43210/);
    assert.match(error.message, /用户授权且确认不影响其他会话/);
    return true;
  });
});

test('proxy retains its pin when browser disappears', async () => {
  const { run } = discoverer({ kind: 'empty' }, 'edge');
  await assert.rejects(run(), error => {
    assert.match(error.message, /PID 43210/);
    assert.match(error.message, /不擅自修改浏览器配置/);
    return true;
  });
});

test('safe diagnostics replace batch-kill and global-install advice in both entry points', () => {
  for (const file of ['check-deps.mjs', 'cdp-proxy.mjs']) {
    assert.doesNotMatch(sources[file], /pkill\s+-f/);
    assert.doesNotMatch(sources[file], /npm install -g ws/);
  }
});

test('explicit selection refuses reuse when browser identity is unknown', async () => {
  for (const id of [undefined, 'unknown']) {
    const { run } = sandbox(ensureSource, 'ensureProxy', {
      PROXY_PORT: 3456,
      httpGetJson: async () => ({ status: 'ok', connected: true, browser: { id } }),
      startProxyDetached: () => assert.fail('An unidentified proxy must not be replaced'),
    });
    assert.equal(await run('edge', 'edge'), false);
  }
});

test('checker verifies browser identity again after proxy startup', async () => {
  let calls = 0;
  const responses = [null, [], { status: 'ok', connected: true, browser: { id: 'chrome' } }];
  const { run } = sandbox(ensureSource, 'ensureProxy', {
    PROXY_PORT: 3456,
    httpGetJson: async () => responses.shift(),
    startProxyDetached: () => { calls++; },
    setTimeout: callback => callback(),
  });
  assert.equal(await run('edge', 'edge'), false);
  assert.equal(calls, 1);
});

test('ambiguous browser selection never probes the fallback port', async () => {
  const { run } = sandbox(discoverSource, 'discoverChromePort', {
    selectBrowser: async () => ({ kind: 'ambiguous' }),
    findFallbackPort: () => assert.fail('Ambiguous selection must not probe fallback'),
    BROWSER_OVERRIDE: null,
    pinnedBrowserId: null,
    connectedBrowser: null,
  });
  await assert.rejects(run(), /请先选择浏览器/);
});
