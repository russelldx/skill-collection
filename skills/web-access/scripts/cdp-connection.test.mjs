import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { setImmediate as nextTurn } from 'node:timers/promises';
import test from 'node:test';
import { createCdpConnection } from './cdp-connection.mjs';

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

// 用两种真实事件接口替换网络传输；从公共工厂观察状态与结果。
function socketModel(model) {
  const sockets = [];
  const control = { constructorError: null };
  const Base = model === 'EventTarget' ? EventTarget : EventEmitter;
  class FakeWebSocket extends Base {
    static OPEN = 1;
    constructor(url) {
      super();
      if (control.constructorError) throw control.constructorError;
      this.url = url;
      this.readyState = 0;
      this.sent = [];
      this.closeCalls = 0;
      this.sendError = null;
      sockets.push(this);
    }
    emitSocket(type, payload, reason) {
      if (model === 'EventEmitter') return this.emit(type, payload, reason);
      if (type === 'message') return this.dispatchEvent(new MessageEvent(type, { data: payload }));
      const event = new Event(type);
      if (type === 'error') Object.defineProperty(event, 'error', { value: payload });
      if (type === 'close') Object.defineProperty(event, 'reason', { value: reason || '' });
      return this.dispatchEvent(event);
    }
    open() { this.readyState = 1; this.emitSocket('open'); }
    fail(error = new Error('handshake failed')) { this.emitSocket('error', error); }
    remoteClose() { this.readyState = 3; this.emitSocket('close', 1006, 'remote closed'); }
    close() { this.closeCalls++; this.remoteClose(); }
    send(data) {
      if (this.sendError) throw this.sendError;
      this.sent.push(JSON.parse(data));
    }
    message(message, asString = false) {
      const text = JSON.stringify(message);
      this.emitSocket('message', model === 'EventEmitter' && !asString ? Buffer.from(text) : text);
    }
  }
  return { WebSocketImpl: FakeWebSocket, sockets, control };
}

function fixture(t, model, options = {}) {
  const transport = socketModel(model);
  const connection = createCdpConnection({
    ...transport,
    discoverUrl: () => 'ws://fake/browser',
    ...options,
  });
  t.after(() => connection.close());
  return { ...transport, connection };
}

async function establish(f) {
  const flight = f.connection.connect();
  await nextTurn();
  const socket = f.sockets.at(-1);
  assert.ok(socket, '发现完成后应创建一个 socket');
  socket.open();
  await flight;
  return socket;
}

for (const model of ['EventTarget', 'EventEmitter']) {
  test(`${model}: 并发发现与并发握手共享同一个 flight，已连接直接复用`, async t => {
    const discovery = deferred();
    let discoveries = 0;
    let opens = 0;
    const f = fixture(t, model, {
      discoverUrl: () => { discoveries++; return discovery.promise; },
      onConnect: () => { opens++; },
    });
    const first = f.connection.connect();
    assert.equal(f.connection.connect(), first);
    assert.equal(f.connection.state, 'discovering');
    assert.equal(f.connection.connected, false);
    assert.equal(f.connection.attemptCount, 1);
    await nextTurn();
    assert.equal(discoveries, 1);
    assert.equal(f.sockets.length, 0);
    discovery.resolve('ws://fake/one');
    await nextTurn();
    assert.equal(f.connection.state, 'connecting');
    assert.equal(f.sockets.length, 1);
    assert.equal(f.connection.connect(), first);
    f.sockets[0].open();
    assert.equal(await first, undefined);
    await f.connection.connect();
    assert.equal(f.connection.connected, true);
    assert.equal(f.connection.state, 'connected');
    assert.equal(f.connection.attemptCount, 1);
    assert.equal(discoveries, 1);
    assert.equal(opens, 1);
  });

  test(`${model}: discoverUrl 同步重入也只能取得已经发布的 flight`, async t => {
    let nested;
    let f;
    f = fixture(t, model, { discoverUrl: () => { nested = f.connection.connect(); return 'ws://fake/reentrant'; } });
    const first = f.connection.connect();
    await nextTurn();
    assert.equal(nested, first);
    assert.equal(f.sockets.length, 1);
    f.sockets[0].open();
    await first;
  });

  for (const failure of ['discovery', 'constructor', 'handshake error', 'close before open']) {
    test(`${model}: ${failure} 释放 flight 后允许重新发现与连接`, async t => {
      const discovery = deferred();
      const disconnections = [];
      let firstDiscovery = true;
      const f = fixture(t, model, {
        discoverUrl: () => {
          if (failure === 'discovery' && firstDiscovery) { firstDiscovery = false; return discovery.promise; }
          return 'ws://fake/retry';
        },
        onDisconnect: error => disconnections.push(error),
      });
      if (failure === 'constructor') f.control.constructorError = new Error('constructor failed');
      const first = f.connection.connect();
      const rejected = assert.rejects(first, /failed|关闭|closed/);
      assert.equal(f.connection.connect(), first);
      await nextTurn();
      if (failure === 'discovery') discovery.reject(new Error('discovery failed'));
      if (failure === 'handshake error') f.sockets[0].fail();
      if (failure === 'close before open') f.sockets[0].remoteClose();
      await rejected;
      assert.equal(f.connection.state, 'disconnected');
      assert.equal(f.connection.connected, false);
      assert.equal(f.connection.pendingCount, 0);
      assert.equal(disconnections.length, 1);
      f.control.constructorError = null;
      await establish(f);
      assert.equal(f.connection.attemptCount, 2);
      assert.equal(f.connection.connected, true);
    });
  }

  test(`${model}: send 不隐式连接，原样返回 response 并转发 CDP 事件`, async t => {
    const events = [];
    const f = fixture(t, model, { onEvent: message => events.push(message) });
    await assert.rejects(f.connection.send('Browser.getVersion'), /未连接/);
    assert.equal(f.connection.attemptCount, 0);
    const socket = await establish(f);
    const command = f.connection.send('Runtime.evaluate', { expression: '1 + 1' }, 'session-1');
    assert.equal(f.connection.pendingCount, 1);
    assert.deepEqual(socket.sent[0], { id: 1, method: 'Runtime.evaluate', params: { expression: '1 + 1' }, sessionId: 'session-1' });
    const event = { method: 'Target.attachedToTarget', params: { sessionId: 's' } };
    socket.message(event);
    assert.deepEqual(events, [event]);
    const response = { id: 1, result: { value: 2 }, sessionId: 'session-1' };
    socket.message(response);
    assert.deepEqual(await command, response);
    assert.equal(f.connection.pendingCount, 0);
    const errorCommand = f.connection.send('Unsupported.method');
    const errorResponse = { id: 2, error: { code: -32601, message: 'method not found' } };
    socket.message(errorResponse, true);
    assert.deepEqual(await errorCommand, errorResponse);
  });

  test(`${model}: 断开立即拒绝全部命令并清除 pending`, async t => {
    const timerCleanup = t.mock.method(globalThis, 'clearTimeout');
    const f = fixture(t, model);
    const socket = await establish(f);
    const first = assert.rejects(f.connection.send('First.method'), /断开/);
    const second = assert.rejects(f.connection.send('Second.method'), /断开/);
    assert.equal(f.connection.pendingCount, 2);
    socket.remoteClose();
    assert.equal(f.connection.pendingCount, 0);
    assert.equal(f.connection.state, 'disconnected');
    assert.equal(timerCleanup.mock.callCount(), 2, '断开时立即清理两条命令的计时器');
    await Promise.all([first, second]);
  });

  test(`${model}: 旧 socket 的全部迟到事件不能影响新连接或新命令`, async t => {
    const events = [];
    const disconnections = [];
    const f = fixture(t, model, { onEvent: message => events.push(message), onDisconnect: error => disconnections.push(error) });
    const old = await establish(f);
    const oldCommand = assert.rejects(f.connection.send('Old.method'), /断开/);
    old.remoteClose();
    await oldCommand;
    const next = f.connection.connect();
    old.open();
    old.fail();
    old.remoteClose();
    assert.equal(f.connection.state, 'discovering');
    await nextTurn();
    const socket = f.sockets[1];
    old.open();
    old.fail();
    old.remoteClose();
    assert.equal(f.connection.state, 'connecting');
    assert.equal(f.connection.connect(), next);
    socket.open();
    await next;
    const command = f.connection.send('New.method');
    const id = socket.sent[0].id;
    old.message({ id, result: { wrong: true } });
    old.message({ method: 'Target.attachedToTarget', params: { old: true } });
    old.open();
    old.fail();
    old.remoteClose();
    assert.equal(f.connection.pendingCount, 1);
    assert.equal(f.connection.connected, true);
    assert.equal(disconnections.length, 1);
    assert.deepEqual(events, []);
    socket.message({ id, result: { correct: true } });
    assert.deepEqual(await command, { id, result: { correct: true } });
  });

  test(`${model}: 在发现阶段 close 立即结算，迟到发现结果不得创建 socket`, async t => {
    const discovery = deferred();
    let calls = 0;
    const f = fixture(t, model, { discoverUrl: () => ++calls === 1 ? discovery.promise : 'ws://fake/retry' });
    const rejected = assert.rejects(f.connection.connect(), /主动关闭/);
    await nextTurn();
    f.connection.close();
    assert.equal(f.connection.state, 'disconnected');
    await rejected;
    discovery.resolve('ws://fake/obsolete');
    await nextTurn();
    assert.equal(f.sockets.length, 0);
    await establish(f);
    assert.equal(f.connection.attemptCount, 2);
  });

  test(`${model}: 握手与已连接阶段 close 均立即结算并允许后续连接`, async t => {
    const timerCleanup = t.mock.method(globalThis, 'clearTimeout');
    const f = fixture(t, model);
    const rejected = assert.rejects(f.connection.connect(), /主动关闭/);
    await nextTurn();
    const old = f.sockets[0];
    f.connection.close();
    assert.equal(old.closeCalls, 1);
    await rejected;
    old.open();
    assert.equal(f.connection.connected, false);
    const socket = await establish(f);
    const command = assert.rejects(f.connection.send('Pending.method'), /主动关闭/);
    f.connection.close();
    assert.equal(f.connection.pendingCount, 0);
    assert.equal(f.connection.state, 'disconnected');
    assert.equal(socket.closeCalls, 1);
    assert.equal(timerCleanup.mock.callCount(), 1, '主动关闭时清理命令计时器');
    await command;
    f.connection.close();
    assert.equal(socket.closeCalls, 1);
  });

  test(`${model}: 命令超时清除自身 pending，连接仍可使用`, async t => {
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const f = fixture(t, model, { commandTimeoutMs: 30 });
    const socket = await establish(f);
    const rejected = assert.rejects(f.connection.send('Slow.method'), /CDP 命令超时: Slow.method/);
    t.mock.timers.tick(29);
    assert.equal(f.connection.pendingCount, 1);
    t.mock.timers.tick(1);
    await rejected;
    assert.equal(f.connection.pendingCount, 0);
    assert.equal(f.connection.connected, true);
    const command = f.connection.send('Next.method');
    const id = socket.sent.at(-1).id;
    socket.message({ id, result: {} });
    await command;
    t.mock.timers.tick(100);
    assert.equal(f.connection.pendingCount, 0);
  });

  test(`${model}: 同步 send 与编码失败只拒绝自身命令并清除 pending`, async t => {
    const timerCleanup = t.mock.method(globalThis, 'clearTimeout');
    const f = fixture(t, model);
    const socket = await establish(f);
    socket.sendError = new Error('send failed');
    await assert.rejects(f.connection.send('Broken.method'), /send failed/);
    assert.equal(f.connection.pendingCount, 0);
    assert.equal(timerCleanup.mock.callCount(), 1, '同步发送失败时清理已经创建的命令计时器');
    socket.sendError = null;
    const circular = {};
    circular.self = circular;
    await assert.rejects(f.connection.send('Circular.method', circular), /circular/i);
    assert.equal(f.connection.pendingCount, 0);
    const command = f.connection.send('Working.method');
    const id = socket.sent.at(-1).id;
    socket.message({ id, result: {} });
    await command;
    assert.equal(f.connection.connected, true);
  });

  test(`${model}: 非法响应与事件回调异常提供诊断，保留可用连接`, async t => {
    const diagnostics = [];
    const f = fixture(t, model, {
      onDiagnostic: error => diagnostics.push(error),
      onEvent: () => { throw new Error('event hook failed'); },
    });
    const socket = await establish(f);
    socket.emitSocket('message', '{broken json');
    socket.message({ method: 'Test.event' });
    assert.equal(diagnostics.length, 2);
    assert.match(diagnostics[1].message, /event hook failed/);
    assert.equal(f.connection.connected, true);
  });
}
