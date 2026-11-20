import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { userDataPaths, migrateLegacyData } from './user-data.mjs';

// 全部在临时目录中构造 Skill 安装位置与 HOME，不读写真实用户数据。
async function sandbox(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'web-access-user-data-'));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  const home = path.join(root, 'home');
  await fs.mkdir(home);
  return { root, home, target: userDataPaths(home) };
}

// 写一个 Skill 目录：可选 SKILL.md 名称、config.env、site-patterns 文件，并统一设定修改时间
async function skillDir(dir, { name = 'web-access', config, patterns = {}, mtime } = {}) {
  await fs.mkdir(path.join(dir, 'references', 'site-patterns'), { recursive: true });
  await fs.writeFile(path.join(dir, 'references', 'site-patterns', '.gitkeep'), '');
  if (name) await fs.writeFile(path.join(dir, 'SKILL.md'), `---\nname: ${name}\nlicense: MIT\n---\n\n# ${name}\n`);
  const files = [];
  if (config !== undefined) {
    await fs.writeFile(path.join(dir, 'config.env'), config);
    files.push(path.join(dir, 'config.env'));
  }
  for (const [rel, content] of Object.entries(patterns)) {
    const file = path.join(dir, 'references', 'site-patterns', ...rel.split('/'));
    await fs.mkdir(path.dirname(file), { recursive: true });
    await fs.writeFile(file, content);
    files.push(file);
  }
  if (mtime) for (const file of files) await fs.utimes(file, mtime, mtime);
  return dir;
}

const read = file => fs.readFile(file, 'utf8');
const exists = file => fs.access(file).then(() => true, () => false);

test('路径集中在 HOME/.web-access，按平台分隔规则拼接', () => {
  const posix = userDataPaths('/home/user');
  assert.equal(posix.dir, path.join('/home/user', '.web-access'));
  assert.equal(posix.config, path.join('/home/user', '.web-access', 'config.env'));
  assert.equal(posix.sitePatterns, path.join('/home/user', '.web-access', 'site-patterns'));
  assert.equal(userDataPaths().dir, path.join(os.homedir(), '.web-access'));

  // 模块不写死分隔符：换成 Windows 规则后得到原生反斜杠路径
  const originalJoin = path.join;
  path.join = path.win32.join;
  try {
    const win = userDataPaths('C:\\Users\\Name');
    assert.equal(win.dir, 'C:\\Users\\Name\\.web-access');
    assert.equal(win.config, 'C:\\Users\\Name\\.web-access\\config.env');
    assert.equal(win.sitePatterns, 'C:\\Users\\Name\\.web-access\\site-patterns');
    assert.equal(win.marker, 'C:\\Users\\Name\\.web-access\\.migrated');
  } finally {
    path.join = originalJoin;
  }
});

test('git 安装：Skill 根目录的旧数据递归复制到新位置，旧文件保留', async t => {
  const s = await sandbox(t);
  const skill = await skillDir(path.join(s.root, 'skills', 'web-access'), {
    config: 'WEB_ACCESS_BROWSER=edge\n',
    patterns: { 'example.com.md': 'example', 'archive/old.com.md': 'old' },
  });
  const result = migrateLegacyData({ root: skill, home: s.home });
  assert.deepEqual(result, { dir: s.target.dir, sources: [{ from: skill, config: true, patterns: 2 }] });
  assert.equal(await read(s.target.config), 'WEB_ACCESS_BROWSER=edge\n');
  assert.equal(await read(path.join(s.target.sitePatterns, 'example.com.md')), 'example');
  assert.equal(await read(path.join(s.target.sitePatterns, 'archive', 'old.com.md')), 'old');
  assert.equal(await exists(path.join(s.target.sitePatterns, '.gitkeep')), false);
  assert.ok(await exists(s.target.marker));
  // 只复制不删除
  assert.equal(await read(path.join(skill, 'config.env')), 'WEB_ACCESS_BROWSER=edge\n');
  assert.ok(await exists(path.join(skill, 'references', 'site-patterns', 'archive', 'old.com.md')));
});

test('插件按版本分目录：只取最新的 web-access 旧版本，不吸收其他目录的数据', async t => {
  const s = await sandbox(t);
  const cache = path.join(s.root, 'cache', 'web-access');
  const old = new Date('2026-01-01T00:00:00Z');
  const newer = new Date('2026-05-01T00:00:00Z');
  const newest = new Date('2026-09-01T00:00:00Z');
  await skillDir(path.join(cache, '2.5.2'), { config: 'WEB_ACCESS_BROWSER=chrome\n', patterns: { 'a.com.md': 'v252' }, mtime: old });
  await skillDir(path.join(cache, '2.5.4'), { config: 'WEB_ACCESS_BROWSER=edge\n', patterns: { 'b.com.md': 'v254' }, mtime: newer });
  // 以下目录都比 2.5.4 更新，但不是 web-access：其他 Skill、无 SKILL.md、名称只是相近或仅在正文提到
  await skillDir(path.join(cache, 'other-skill'), { name: 'other-skill', config: 'OTHER=1\n', patterns: { 'x.com.md': 'x' }, mtime: newest });
  await skillDir(path.join(cache, 'no-skill-md'), { name: null, config: 'NOPE=1\n', mtime: newest });
  await skillDir(path.join(cache, 'web-access-pro'), { name: 'web-access-pro', patterns: { 'y.com.md': 'y' }, mtime: newest });
  const mention = await skillDir(path.join(cache, 'mention'), { name: null, config: 'MENTION=1\n', mtime: newest });
  await fs.writeFile(path.join(mention, 'SKILL.md'), '---\nname: helper\ndescription: 搭配 web-access 使用\n---\nname: web-access\n');
  await fs.writeFile(path.join(cache, 'SKILL.md'), '---\nname: web-access\n---\n'); // 普通文件不是目录
  const current = await skillDir(path.join(cache, '2.5.5'));

  const result = migrateLegacyData({ root: current, home: s.home });
  assert.deepEqual(result.sources, [{ from: path.join(cache, '2.5.4'), config: true, patterns: 1 }]);
  assert.equal(await read(s.target.config), 'WEB_ACCESS_BROWSER=edge\n');
  assert.deepEqual(await fs.readdir(s.target.sitePatterns), ['b.com.md']);
});

test('当前目录与兄弟旧版本都有数据时合并，当前目录优先且不覆盖', async t => {
  const s = await sandbox(t);
  const parent = path.join(s.root, 'cache', 'web-access');
  await skillDir(path.join(parent, '2.5.4'), { config: 'WEB_ACCESS_BROWSER=chrome\n', patterns: { 'a.com.md': 'sibling', 'b.com.md': 'sibling' } });
  const current = await skillDir(path.join(parent, '2.6.0'), { config: 'WEB_ACCESS_BROWSER=edge\n', patterns: { 'a.com.md': 'current' } });
  const result = migrateLegacyData({ root: current, home: s.home });
  assert.deepEqual(result.sources, [
    { from: current, config: true, patterns: 1 },
    { from: path.join(parent, '2.5.4'), config: false, patterns: 1 },
  ]);
  assert.equal(await read(s.target.config), 'WEB_ACCESS_BROWSER=edge\n');
  assert.equal(await read(path.join(s.target.sitePatterns, 'a.com.md')), 'current');
  assert.equal(await read(path.join(s.target.sitePatterns, 'b.com.md')), 'sibling');
});

for (const parentName of ['skills', 'home']) {
  test(`父目录不是 web-access（${parentName}）时不扫描兄弟目录，只迁移当前目录`, async t => {
    const s = await sandbox(t);
    const parent = parentName === 'home' ? s.home : path.join(s.root, 'skills');
    // 兄弟目录看起来就是 web-access 旧版本，也不应被读取
    await skillDir(path.join(parent, 'web-access-old'), { config: 'WEB_ACCESS_BROWSER=chrome\n', patterns: { 'old.com.md': 'sibling' } });
    await skillDir(path.join(parent, 'Desktop'), { config: 'WEB_ACCESS_BROWSER=edge\n' });
    const current = await skillDir(path.join(parent, 'web-access'), { patterns: { 'a.com.md': 'current' } });
    const result = migrateLegacyData({ root: current, home: s.home });
    assert.deepEqual(result.sources, [{ from: current, config: false, patterns: 1 }]);
    assert.equal(await exists(s.target.config), false);
    assert.deepEqual(await fs.readdir(s.target.sitePatterns), ['a.com.md']);
  });
}

test('新位置已存在的文件不被旧副本覆盖', async t => {
  const s = await sandbox(t);
  const skill = await skillDir(path.join(s.root, 'skills', 'web-access'), {
    config: 'WEB_ACCESS_BROWSER=edge\n',
    patterns: { 'example.com.md': 'old', 'new.com.md': 'new' },
  });
  await fs.mkdir(s.target.sitePatterns, { recursive: true });
  await fs.writeFile(s.target.config, 'WEB_ACCESS_BROWSER=chrome\n');
  await fs.writeFile(path.join(s.target.sitePatterns, 'example.com.md'), 'kept');
  const result = migrateLegacyData({ root: skill, home: s.home });
  assert.deepEqual(result.sources, [{ from: skill, config: false, patterns: 1 }]);
  assert.equal(await read(s.target.config), 'WEB_ACCESS_BROWSER=chrome\n');
  assert.equal(await read(path.join(s.target.sitePatterns, 'example.com.md')), 'kept');
  assert.equal(await read(path.join(s.target.sitePatterns, 'new.com.md')), 'new');
});

test('迁移标记存在后不再扫描，用户删除的文件不会被旧副本复活', async t => {
  const s = await sandbox(t);
  const skill = await skillDir(path.join(s.root, 'skills', 'web-access'), { patterns: { 'example.com.md': 'old' } });
  assert.equal(migrateLegacyData({ root: skill, home: s.home }).sources.length, 1);
  await fs.rm(path.join(s.target.sitePatterns, 'example.com.md'));
  assert.equal(migrateLegacyData({ root: skill, home: s.home }), null);
  assert.equal(await exists(path.join(s.target.sitePatterns, 'example.com.md')), false);
});

test('没有旧数据时不复制任何文件，只写标记', async t => {
  const s = await sandbox(t);
  const parent = path.join(s.root, 'skills');
  await skillDir(path.join(parent, 'other'), { name: 'other', config: 'X=1\n' });
  const skill = await skillDir(path.join(parent, 'web-access'));
  const result = migrateLegacyData({ root: skill, home: s.home });
  assert.deepEqual(result, { dir: s.target.dir, sources: [] });
  assert.deepEqual(await fs.readdir(s.target.dir), ['.migrated']);
});

test('迁移失败直接抛出且不写标记，下次可重试', async t => {
  const s = await sandbox(t);
  const skill = await skillDir(path.join(s.root, 'skills', 'web-access'), { config: 'WEB_ACCESS_BROWSER=edge\n' });
  await fs.writeFile(s.target.dir, '占位文件，使数据目录无法创建');
  assert.throws(() => migrateLegacyData({ root: skill, home: s.home }));
  await fs.rm(s.target.dir);
  assert.equal(migrateLegacyData({ root: skill, home: s.home }).sources.length, 1);
  assert.equal(await read(s.target.config), 'WEB_ACCESS_BROWSER=edge\n');
});
