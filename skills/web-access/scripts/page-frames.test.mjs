import assert from 'node:assert/strict';
import test from 'node:test';
import { createPageFrames, FrameError } from './page-frames.mjs';

// 进程内假浏览器：按 CDP 方法返回固定结构，记录每次调用（方法、参数、session），不连接任何浏览器。
// 页面 page-1 主文档里有三个 iframe：同进程 local-frame、跨进程 oopif-frame、尚未加载的第三个。
function fakeBrowser({ hit = null, errors = {} } = {}) {
  const calls = [];
  const attached = [];
  const ensureSession = async targetId => {
    attached.push(targetId);
    return targetId === 'page-1' ? 'page-session' : `${targetId}-session`;
  };
  const send = async (method, params = {}, sessionId = null) => {
    calls.push({ method, params, sessionId });
    if (errors[method]) return { error: { message: errors[method] } };
    switch (method) {
      case 'Runtime.evaluate':
        // 主环境里页面改写了 DOM API（返回空），只有隔离环境能看到真实结果
        if (params.expression.includes('querySelectorAll')) {
          return { result: { result: params.contextId ? { objectId: 'node-list' } : { type: 'object', subtype: 'null' } } };
        }
        if (params.expression.includes('elementFromPoint')) {
          return { result: { result: hit && params.contextId ? { objectId: hit } : { type: 'object', subtype: 'null' } } };
        }
        if (params.expression.includes('innerWidth')) return { result: { result: { value: [300, 250] } } };
        break;
      case 'Runtime.getProperties':
        // 故意乱序，并混入非下标属性
        return { result: { result: [
          { name: '2', value: { objectId: 'el-unloaded' } },
          { name: 'length', value: { value: 3 } },
          { name: '0', value: { objectId: 'el-local' } },
          { name: '1', value: { objectId: 'el-oopif' } },
        ] } };
      case 'Target.getTargets':
        return { result: { targetInfos: [
          { targetId: 'page-1', type: 'page', url: 'http://localhost/p' },
          { targetId: 'oopif-frame', type: 'iframe', url: 'http://127.0.0.1/child' },
          { targetId: 'page-2', type: 'page', url: 'http://other/' },
        ] } };
      case 'Page.getFrameTree':
        return { result: { frameTree: { frame: { id: 'page-1' }, childFrames: [
          { frame: { id: 'local-frame', url: 'http://localhost/same-now', name: 'kid' } },
        ] } } };
      case 'DOM.describeNode': {
        const nodes = {
          'el-local': { frameId: 'local-frame', attributes: ['name', 'kid', 'src', '/same'] },
          'el-oopif': { frameId: 'oopif-frame', attributes: ['id', 'pay', 'src', 'http://127.0.0.1/child', 'style', 'x'] },
          'el-unloaded': { attributes: ['src', 'about:blank#later'] },
          'el-button': { attributes: ['id', 'b'] },
        };
        return { result: { node: nodes[params.objectId] } };
      }
      case 'Page.createIsolatedWorld':
        return { result: { executionContextId: sessionId === 'page-session' ? 11 : 22 } };
      case 'Runtime.callFunctionOn':
        return { result: { result: { value: { x: 55, y: 65 } } } };
      case 'Page.captureScreenshot':
        return { result: { data: 'AA==' } };
    }
    return { result: {} };
  };
  return { frames: createPageFrames({ send, ensureSession }), calls, attached };
}

const methods = calls => calls.map(call => call.method);
// 释放的对象组：返回前缀，并断言每个被释放的组都是本次调用创建临时对象时用的那个（组名唯一）
const releasedGroups = calls => {
  const created = new Set(calls.map(call => call.params?.objectGroup).filter(group => group && calls.some(c => c.method !== 'Runtime.releaseObjectGroup' && c.params?.objectGroup === group)));
  const released = calls.filter(call => call.method === 'Runtime.releaseObjectGroup').map(call => call.params.objectGroup);
  for (const group of released) {
    assert.match(group, /^web-access-(frames|click)-[0-9a-f-]{36}$/);
    assert.ok(created.size === 0 || created.has(group), `释放了未创建的组 ${group}`);
  }
  return released.map(group => group.replace(/-[0-9a-f-]{36}$/, ''));
};

test('listFrames 按文档顺序列出主文档 iframe：跨进程标记、当前网址与定位线索，用完释放临时对象', async () => {
  const { frames, calls, attached } = fakeBrowser();
  assert.deepEqual(await frames.listFrames('page-1'), [
    { index: 0, frameId: 'local-frame', crossProcess: false, url: 'http://localhost/same-now', name: 'kid', src: '/same' },
    { index: 1, frameId: 'oopif-frame', crossProcess: true, url: 'http://127.0.0.1/child', id: 'pay', src: 'http://127.0.0.1/child' },
    { index: 2, frameId: null, crossProcess: false, url: 'about:blank#later', src: 'about:blank#later' },
  ]);
  assert.deepEqual(attached, ['page-1']);
  assert.ok(calls.filter(call => call.method !== 'Target.getTargets').every(call => call.sessionId === 'page-session'));
  assert.deepEqual(releasedGroups(calls), ['web-access-frames']);
});

test('页面没有 iframe 时返回空数组，不查询 iframe target', async () => {
  const calls = [];
  const frames = createPageFrames({
    ensureSession: async () => 'page-session',
    send: async (method, params, sessionId) => {
      calls.push({ method, params, sessionId });
      if (method === 'Runtime.evaluate') return { result: { result: { objectId: 'node-list' } } };
      if (method === 'Runtime.getProperties') return { result: { result: [{ name: 'length', value: { value: 0 } }] } };
      if (method === 'Page.getFrameTree') return { result: { frameTree: { frame: { id: 'page-1' } } } };
      if (method === 'Page.createIsolatedWorld') return { result: { executionContextId: 1 } };
      return { result: {} };
    },
  });
  assert.deepEqual(await frames.listFrames('page-1'), []);
  assert.ok(!methods(calls).includes('Target.getTargets'));
  assert.deepEqual(releasedGroups(calls), ['web-access-frames']);
});

test('frameContext：跨进程 iframe 在它的子 session 中建隔离环境，同进程 iframe 用页面 session', async () => {
  const oop = fakeBrowser();
  const remote = await oop.frames.frameContext('page-1', 'oopif-frame');
  assert.equal(remote.sessionId, 'oopif-frame-session');
  assert.equal(remote.contextId, 22);
  assert.equal(remote.frame.crossProcess, true);
  const world = oop.calls.find(call => call.method === 'Page.createIsolatedWorld' && call.params.frameId === 'oopif-frame');
  assert.deepEqual(world, { method: 'Page.createIsolatedWorld', params: { frameId: 'oopif-frame', worldName: 'web-access' }, sessionId: 'oopif-frame-session' });

  const same = fakeBrowser();
  const local = await same.frames.frameContext('page-1', 'local-frame');
  assert.equal(local.sessionId, 'page-session');
  assert.equal(local.contextId, 11);
  assert.ok(!same.attached.includes('local-frame'));
});

for (const [frameId, pattern] of [
  ['', /应为 \/frames 返回的 frameId/],
  ['#pay', /应为 \/frames 返回的 frameId/],
  ['a b', /应为 \/frames 返回的 frameId/],
  [undefined, /应为 \/frames 返回的 frameId/],
  ['page-2', /该页面没有 frameId 为 page-2/],
  ['page-1', /该页面没有 frameId 为 page-1/],
]) {
  test(`frameContext 拒绝 ${JSON.stringify(frameId)}：只接受本页面主文档里 iframe 的 frameId，不 attach 其他目标`, async () => {
    const { frames, attached, calls } = fakeBrowser();
    await assert.rejects(frames.frameContext('page-1', frameId), error => error instanceof FrameError && pattern.test(error.message));
    assert.ok(attached.every(id => id === 'page-1'), attached.join(','));
    // 只为页面根 frame 建过隔离环境（用于列举），没有进入任何其他 frame
    assert.ok(calls.filter(call => call.method === 'Page.createIsolatedWorld').every(call => call.params.frameId === 'page-1'));
  });
}

// routePoint 的假浏览器：按 frame 描述布局。每个 frame 记录它所在的 session、命中的元素、
// 元素指向的子 frame、子 frame 元素的内容框（session 根视口坐标）和子 frame 的视口尺寸。
function routeFake(layout, { oopifs = [] } = {}) {
  const calls = [];
  const sessionOf = frameId => (frameId === 'page-1' || !oopifs.includes(frameId) ? 'page-session' : `${frameId}-session`);
  const contextFrame = new Map(); // contextId → frameId
  let contextSeq = 0;
  const send = async (method, params = {}, sessionId = null) => {
    calls.push({ method, params, sessionId });
    switch (method) {
      case 'Page.getFrameTree': return { result: { frameTree: { frame: { id: 'page-1' } } } };
      case 'Page.createIsolatedWorld': {
        const id = ++contextSeq;
        contextFrame.set(id, params.frameId);
        return { result: { executionContextId: id } };
      }
      case 'Runtime.evaluate': {
        const frame = layout[contextFrame.get(params.contextId)] || {};
        if (params.expression.includes('elementFromPoint')) {
          return { result: { result: frame.hit ? { objectId: `${contextFrame.get(params.contextId)}:hit` } : { type: 'object', subtype: 'null' } } };
        }
        if (params.expression.includes('innerWidth')) return { result: { result: { value: frame.viewport } } };
        break;
      }
      case 'DOM.describeNode': {
        const frame = layout[params.objectId.split(':')[0]];
        return { result: { node: { attributes: [], ...(frame.child ? { frameId: frame.child } : {}) } } };
      }
      case 'DOM.getBoxModel': return { result: { model: { content: layout[params.objectId.split(':')[0]].content } } };
      case 'Target.getTargets': return { result: { targetInfos: oopifs.map(targetId => ({ targetId, type: 'iframe', url: 'x' })) } };
      case 'Page.captureScreenshot': return { result: { data: 'AA==' } };
    }
    return { result: {} };
  };
  const ensureSession = async targetId => sessionOf(targetId);
  return { frames: createPageFrames({ send, ensureSession }), calls };
}

const quad = (left, top, width, height) => [left, top, left + width, top, left + width, top + height, left, top + height];
const hitPoints = calls => calls.filter(call => call.method === 'Runtime.evaluate' && call.params.expression.includes('elementFromPoint'))
  .map(call => [call.sessionId, call.params.expression.match(/elementFromPoint\(([^,]+), ([^)]+)\)/).slice(1).map(Number)]);

test('routePoint：坐标不在页面视口内（没有命中任何元素）时抛 FrameError，不路由', async () => {
  const { frames, calls } = routeFake({ 'page-1': {} });
  await assert.rejects(frames.routePoint('page-1', 5000, 5000), error => error instanceof FrameError && /不在页面视口内/.test(error.message));
  assert.ok(!methods(calls).includes('DOM.describeNode'));
});

test('routePoint：命中普通元素时坐标不变发给页面', async () => {
  const { frames, calls } = routeFake({ 'page-1': { hit: true } });
  assert.deepEqual(await frames.routePoint('page-1', 12, 34), { sessionId: 'page-session', x: 12, y: 34 });
  assert.ok(!methods(calls).includes('Page.captureScreenshot'));
  assert.deepEqual(releasedGroups(calls), ['web-access-click']);
});

test('routePoint：跨进程 iframe 有边框与内边距时按内容框原点换算（审查 F2）', async () => {
  // iframe 边框盒在 (50,60)，5px 边框 + 20px 内边距 → 内容框原点 (75,85)，300×250，无缩放
  const { frames } = routeFake({
    'page-1': { hit: true, child: 'oopif-frame', content: quad(75, 85, 300, 250) },
    'oopif-frame': { hit: true, viewport: [300, 250] },
  }, { oopifs: ['oopif-frame'] });
  assert.deepEqual(await frames.routePoint('page-1', 135, 115), {
    sessionId: 'oopif-frame-session', x: 60, y: 30, frameId: 'oopif-frame', crossProcess: true, depth: 1,
  });
});

test('routePoint：iframe 被 transform / zoom 放大时按内容框与 iframe 视口的比例换算', async () => {
  // 内容框在视口中占 450×375，iframe 视口 300×250 → 缩放 1.5
  const { frames } = routeFake({
    'page-1': { hit: true, child: 'oopif-frame', content: quad(57.5, 67.5, 450, 375) },
    'oopif-frame': { hit: true, viewport: [300, 250] },
  }, { oopifs: ['oopif-frame'] });
  const route = await frames.routePoint('page-1', 57.5 + 90, 67.5 + 45);
  assert.equal(route.sessionId, 'oopif-frame-session');
  assert.deepEqual([route.x, route.y], [60, 30]);
});

test('routePoint：落在 iframe 边框或内边距上时留在当前 frame，不进入 iframe', async () => {
  const { frames, calls } = routeFake({
    'page-1': { hit: true, child: 'oopif-frame', content: quad(75, 85, 300, 250) },
    'oopif-frame': { hit: true, viewport: [300, 250] },
  }, { oopifs: ['oopif-frame'] });
  assert.deepEqual(await frames.routePoint('page-1', 60, 70), { sessionId: 'page-session', x: 60, y: 70 });
  assert.ok(!calls.some(call => call.sessionId === 'oopif-frame-session'));
});

test('routePoint：命中同进程 iframe 时鼠标事件仍发给页面原坐标，命中测试换算到 frame 内，并先触发一次绘制', async () => {
  const { frames, calls } = routeFake({
    'page-1': { hit: true, child: 'local-frame', content: quad(512, 72, 300, 250) },
    'local-frame': { hit: true, viewport: [300, 250] },
  });
  assert.deepEqual(await frames.routePoint('page-1', 572, 102), {
    sessionId: 'page-session', x: 572, y: 102, frameId: 'local-frame', crossProcess: false, depth: 1,
  });
  assert.deepEqual(hitPoints(calls), [['page-session', [572, 102]], ['page-session', [60, 30]]]);
  assert.equal(calls.filter(call => call.method === 'Page.captureScreenshot' && call.sessionId === 'page-session').length, 1);
});

test('routePoint：逐层进入嵌套的跨进程 iframe（审查 F3）', async () => {
  // 页面 → A（跨进程，内容框 (55,65)）→ B（A 内的跨进程 iframe，内容框在 A 视口 (30,90)）
  const { frames, calls } = routeFake({
    'page-1': { hit: true, child: 'frame-a', content: quad(55, 65, 300, 250) },
    'frame-a': { hit: true, child: 'frame-b', content: quad(30, 90, 200, 100), viewport: [300, 250] },
    'frame-b': { hit: true, viewport: [200, 100] },
  }, { oopifs: ['frame-a', 'frame-b'] });
  assert.deepEqual(await frames.routePoint('page-1', 55 + 30 + 60, 65 + 90 + 30), {
    sessionId: 'frame-b-session', x: 60, y: 30, frameId: 'frame-b', crossProcess: true, depth: 2,
  });
  assert.deepEqual(hitPoints(calls), [['page-session', [145, 185]], ['frame-a-session', [90, 120]], ['frame-b-session', [60, 30]]]);
  assert.deepEqual(releasedGroups(calls), ['web-access-click', 'web-access-click', 'web-access-click']);
  assert.ok(!methods(calls).includes('Page.captureScreenshot'));
});

test('routePoint：同进程 iframe 里嵌的跨进程 iframe 也能进入，坐标按页面根视口换算', async () => {
  // 同进程 frame 内容框 (512,72)；其中的跨进程 iframe 内容框（页面根视口坐标）(537,107)
  const { frames, calls } = routeFake({
    'page-1': { hit: true, child: 'local-frame', content: quad(512, 72, 300, 250) },
    'local-frame': { hit: true, child: 'inner-oopif', content: quad(537, 107, 250, 150), viewport: [300, 250] },
    'inner-oopif': { hit: true, viewport: [250, 150] },
  }, { oopifs: ['inner-oopif'] });
  assert.deepEqual(await frames.routePoint('page-1', 537 + 60, 107 + 30), {
    sessionId: 'inner-oopif-session', x: 60, y: 30, frameId: 'inner-oopif', crossProcess: true, depth: 2,
  });
  assert.deepEqual(hitPoints(calls)[1], ['page-session', [85, 65]]);
  assert.ok(!methods(calls).includes('Page.captureScreenshot'));
});

test('routePoint：嵌套层数有上限，最多进入 5 层', async () => {
  const layout = { 'page-1': { hit: true, child: 'f1', content: quad(0, 0, 100, 100) } };
  for (let i = 1; i <= 8; i++) layout[`f${i}`] = { hit: true, child: `f${i + 1}`, content: quad(0, 0, 100, 100), viewport: [100, 100] };
  const { frames } = routeFake(layout, { oopifs: Array.from({ length: 9 }, (_, i) => `f${i + 1}`) });
  const route = await frames.routePoint('page-1', 10, 10);
  assert.equal(route.depth, 5);
  assert.equal(route.sessionId, 'f5-session');
});

test('CDP 错误带方法名抛出，临时对象组仍被释放', async () => {
  const { frames, calls } = fakeBrowser({ errors: { 'Runtime.getProperties': 'Object reference chain is too long' } });
  await assert.rejects(frames.listFrames('page-1'), /Runtime\.getProperties: Object reference chain is too long/);
  assert.deepEqual(releasedGroups(calls), ['web-access-frames']);
});

// 审查 F1：同一标签页上重叠的请求各自释放自己的对象组，互不影响。
// 假浏览器按对象组登记远程对象，整组释放后再用其中的对象即报错（与 Chrome 一致），并在每个 CDP 调用上随机让出时间制造交错。
test('同一标签页上重叠的 listFrames / routePoint 全部成功，不释放彼此的临时对象', async () => {
  const groupOf = new Map();
  let counter = 0;
  const released = new Set();
  const send = async (method, params = {}) => {
    await new Promise(resolve => setTimeout(resolve, Math.random() * 4));
    const alive = objectId => !released.has(groupOf.get(objectId));
    const object = prefix => { const id = `${prefix}-${++counter}`; groupOf.set(id, params.objectGroup); return id; };
    const dead = { error: { message: 'Could not find object with given id' } };
    switch (method) {
      case 'Runtime.releaseObjectGroup': released.add(params.objectGroup); return { result: {} };
      case 'Runtime.evaluate':
        if (params.expression.includes('querySelectorAll')) return { result: { result: { objectId: object('list') } } };
        if (params.expression.includes('elementFromPoint')) return { result: { result: { objectId: object('hit') } } };
        if (params.expression.includes('innerWidth')) return { result: { result: { value: [300, 250] } } };
        return { result: { result: {} } };
      case 'Runtime.getProperties': {
        if (!alive(params.objectId)) return dead;
        const group = groupOf.get(params.objectId);
        const element = () => { const id = `el-${++counter}`; groupOf.set(id, group); return id; };
        return { result: { result: [{ name: '0', value: { objectId: element() } }, { name: '1', value: { objectId: element() } }] } };
      }
      case 'DOM.describeNode':
        return alive(params.objectId) ? { result: { node: { frameId: 'local-frame', attributes: [] } } } : dead;
      case 'DOM.getBoxModel':
        return alive(params.objectId) ? { result: { model: { content: [0, 0, 300, 0, 300, 250, 0, 250] } } } : dead;
      case 'Target.getTargets': return { result: { targetInfos: [] } };
      case 'Page.getFrameTree': return { result: { frameTree: { frame: { id: 'page-1' }, childFrames: [{ frame: { id: 'local-frame', url: 'http://localhost/a' } }] } } };
      case 'Page.createIsolatedWorld': return { result: { executionContextId: 1 } };
      case 'Page.captureScreenshot': return { result: { data: 'AA==' } };
    }
    return { result: {} };
  };
  const frames = createPageFrames({ send, ensureSession: async () => 'page-session' });
  const results = await Promise.allSettled(Array.from({ length: 24 }, (_, i) => (i % 2 ? frames.listFrames('page-1') : frames.routePoint('page-1', 10, 10))));
  const failures = results.filter(result => result.status === 'rejected').map(result => result.reason.message);
  assert.deepEqual(failures, []);
});

// 审查 F4：列举与命中测试在页面根 frame 的隔离环境里执行，页面脚本改写主环境的 DOM API 不影响结果
test('listFrames 与 routePoint 的 DOM 查询都在根 frame 的隔离环境中执行', async () => {
  const { frames, calls: listCalls } = fakeBrowser();
  assert.equal((await frames.listFrames('page-1')).length, 3);
  const route = routeFake({
    'page-1': { hit: true, child: 'oopif-frame', content: quad(55, 65, 300, 250) },
    'oopif-frame': { hit: true, viewport: [300, 250] },
  }, { oopifs: ['oopif-frame'] });
  await route.frames.routePoint('page-1', 115, 95);
  const calls = [...listCalls, ...route.calls];
  const queries = calls.filter(call => call.method === 'Runtime.evaluate' && /querySelectorAll|elementFromPoint/.test(call.params.expression));
  assert.ok(queries.length >= 2);
  for (const query of queries) {
    assert.equal(typeof query.params.contextId, 'number');
    const world = calls.find(call => call.method === 'Page.createIsolatedWorld' && call.sessionId === query.sessionId);
    assert.ok(world, '先为该 session 的根 frame 建隔离环境');
    assert.equal(world.params.frameId, query.sessionId === 'page-session' ? 'page-1' : 'oopif-frame');
  }
});
