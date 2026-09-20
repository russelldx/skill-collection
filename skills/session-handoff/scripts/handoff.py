#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handoff.py — session-handoff 的读模型 + 分层压缩 + 本地检索工具（零依赖、纯离线）

后端类比：
  - HANDOFF.md / archive 是 append-only 事件日志（write model，给人看）
  - STATE.json 是物化视图 / read model（给机器读，有界、可校验）
  - §0 滚动摘要 + milestones 是时序库降采样（rollup），archive 是冷存点查
  - search 子命令 = 本地 BM25 检索（替代 claude-mem：不联网、不装包、CJK 友好）

子命令：
  init     <dir>                      生成一套会话目录（HANDOFF.md/STATE.json/archive/.backup/INDEX.md）
  validate <dir> [--fix-hint]         校验 STATE.json 结构 + 快照 vs 日志的新鲜度 + 一致性，报"待折叠"
  index    <dir> [--max-bytes N]      重建 INDEX.md（节号/标题/tags/体积），并提示应折叠的节
  search   <dir> "<query>" [-k K]     对 active + archive 全部小节做 BM25 排序，回节号 + 定位行
  status   [<root>] [--status ...]    跨会话总览：遍历 root 下所有 STATE.json 出当前态大表（--format json 供机器消费）
  install-hooks [--source DIR] [--target DIR]  把 skill/hooks/*.sh 部署到 ~/.qoder/hooks（备份 + sha256 校验）

纯标准库实现；所有文件读写强制 encoding='utf-8', newline=''（规避 Windows \\r\\n 虚增字节）。
"""
import sys, os, re, json, math, argparse, time, glob, datetime, hashlib
from collections import Counter

# Windows GBK 控制台会把中文打成乱码（文件内容不受影响）；尽量把 stdout 切到 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------- 通用：分节 ----------
H2 = re.compile(r'^##\s+(.*)$')
SECNO = re.compile(r'^(\d+)[、.．]\s*(.*)$')  # "3、2026-.. 会话：.." 或 "0、滚动摘要"

def read_text(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def write_text(p, s):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)

def split_sections(path):
    """把 markdown 切成 {preamble, sections[]}。section: secno,title,start_line,tags[],text。
    secno=None 表示非编号节（如 Context / 任务计划）。"""
    lines = read_text(path).split('\n')
    secs = []
    cur = None
    for idx, ln in enumerate(lines, start=1):
        m = H2.match(ln)
        if m:
            if cur: cur['end'] = idx - 1; secs.append(cur)
            head = m.group(1).strip()
            mn = SECNO.match(head)
            secno = int(mn.group(1)) if mn else None
            title = mn.group(2) if mn else head
            cur = {'file': path, 'secno': secno, 'title': title,
                   'start': idx, 'raw_head': head, 'text_lines': []}
        elif cur is not None:
            cur['text_lines'].append(ln)
    if cur: cur['end'] = len(lines); secs.append(cur)
    for s in secs:
        body = '\n'.join(s['text_lines'])
        s['text'] = body
        s['size'] = len(body.encode('utf-8'))
        s['tags'] = extract_tags(body)
    return secs

TAG = re.compile(r'\*\*tags\*\*\s*[:：]\s*(.+)')
def extract_tags(body):
    for ln in body.split('\n'):
        m = TAG.search(ln)
        if m:
            return [t.strip() for t in re.split(r'[、,，;；]', m.group(1)) if t.strip()]
    return []

def all_docs(root):
    files = [os.path.join(root, 'HANDOFF.md')]
    files += sorted(glob.glob(os.path.join(root, 'archive', '**', '*.md'), recursive=True))
    files += sorted(glob.glob(os.path.join(root, 'milestones.md')))
    files = [f for f in files if os.path.isfile(f)]
    docs = []
    for f in files:
        for s in split_sections(f):
            if s['secno'] == 0:   # 摘要本身不参与检索（它是 rollup 结果）
                continue
            s['bucket'] = 'archive' if os.sep + 'archive' + os.sep in f else 'active'
            docs.append(s)
    return docs

# ---------- BM25（CJK 友好，无分词库） ----------
CJK = r'\u4e00-\u9fff\u3400-\u4dbf'
def tokenize(s):
    s = s.lower()
    toks = re.findall(r'[a-z0-9_]+', s)
    for run in re.findall(r'[%s]+' % CJK, s):
        ch = list(run)
        toks.extend(ch)
        toks.extend(ch[i] + ch[i+1] for i in range(len(ch) - 1))
    return toks

def bm25(query, docs, k1=1.5, b=0.75):
    q = tokenize(query)
    if not q: return []
    tokenized = [tokenize((d['title'] + ' ' + ' '.join(d['tags']) + ' ' + d['title'] + ' ' + d['text'])) for d in docs]
    N = len(docs); avgdl = sum(len(t) for t in tokenized) / max(N, 1) or 1
    df = Counter()
    for t in tokenized:
        for term in set(t): df[term] += 1
    scores = []
    qset = set(q)
    for i, t in enumerate(tokenized):
        tf = Counter(t); dl = len(t); sc = 0.0
        for term in qset:
            if term not in tf: continue
            idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
            sc += idf * (tf[term] * (k1 + 1)) / (tf[term] + k1 * (1 - b + b * dl / avgdl))
        scores.append((sc, i))
    scores.sort(reverse=True)
    return [(s, docs[i]) for s, i in scores if s > 0]

# ---------- STATE.json ----------
STATE_SCHEMA = {
    'schemaVersion': int, 'session': str, 'title': str, 'phase': str,
    'status': str, 'updatedAt': str,
    'openBlockers': list, 'nextActions': list, 'fileOwnership': dict,
    'artifacts': list, 'keyDecisions': list, 'tags': list,
}
VALID_STATUS = {'in-progress', 'blocked', 'done'}

def state_template():
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    return {
        'schemaVersion': 1, 'session': '<chatId-or-name>', 'title': '<任务主题>',
        'phase': '<当前聚焦>', 'status': 'in-progress', 'updatedAt': now,
        'openBlockers': [], 'nextActions': [], 'fileOwnership': {},
        'artifacts': [], 'keyDecisions': [], 'tags': [],
    }

# ---------- init ----------
HANDOFF_SHELL = """# {title} · 交接文档

> 会话交接唯一权威进度源。新会话先读 `## 0 滚动摘要` + STATE.json，再按需点查 archive。
> 事件流（§N）只追加不重写；`## 0` 是唯一允许每次重写的 rollup 区。

## 0、滚动摘要（截至 §0）

> 机器与新会话首读区，只保留"可执行事实"，每次折叠后重写。保持精简（软上限 ~4KB）。

- 当前阶段：{phase}
- 已完成批次：（折叠后自动汇入，如 §1–§3）
- 关键坑（仍生效）：—
- 未决：—
- **tags**: 摘要

## Context

- 背景/目标/需求来源（绝对路径）：
- 已确认决策（按日期）：

## 环境与工具（新会话必读）

- 工具/命令/入口、账号路径、依赖可达性：

## 1、{date} 会话：起始

- 完成内容：
- 验证证据：
- 新坑：现象 → 根因 → 处理 → 状态
- 环境变更：
- 遗留/待办：
- **tags**: 起始

---
## 遗留/待办（滚动清单，完成划掉）

- [ ] —
"""

def cmd_init(a):
    root = os.path.abspath(a.dir)
    if os.path.isdir(root) and os.listdir(root) and not a.force:
        print('ERR 目录非空（加 --force 覆盖模板文件）：' + root); return 2
    os.makedirs(os.path.join(root, 'archive'), exist_ok=True)
    os.makedirs(os.path.join(root, '.backup'), exist_ok=True)
    hp = os.path.join(root, 'HANDOFF.md')
    if not os.path.isfile(hp) or a.force:
        write_text(hp, HANDOFF_SHELL.format(title=a.title or os.path.basename(root),
                 phase=a.phase or '未定', date=time.strftime('%Y-%m-%d')))
    sp = os.path.join(root, 'STATE.json')
    if not os.path.isfile(sp) or a.force:
        st = state_template(); st['session'] = os.path.basename(root)
        st['title'] = a.title or os.path.basename(root); st['phase'] = a.phase or '未定'
        write_text(sp, json.dumps(st, ensure_ascii=False, indent=2) + '\n')
    print('init ok →', root)
    print('  HANDOFF.md  STATE.json  archive/  .backup/  （INDEX.md 由 `index` 生成）')
    return 0

# ---------- validate ----------
def newest_section_date(root):
    ds = []
    for s in all_docs(root):
        m = re.search(r'(20\d\d-\d\d-\d\d)', s['title'])
        if m: ds.append(m.group(1))
        m2 = re.search(r'(20\d\d-\d\d-\d\d)', s['text'][:80])
        if m2: ds.append(m2.group(1))
    return max(ds) if ds else None

def cmd_validate(a):
    root = os.path.abspath(a.dir); sp = os.path.join(root, 'STATE.json'); warns = []; errs = []
    if not os.path.isfile(sp):
        print('ERR 缺 STATE.json（读模型快照）'); return 2
    try: st = json.loads(read_text(sp))
    except Exception as e:
        print('ERR STATE.json 解析失败：', e); return 2
    for k, ty in STATE_SCHEMA.items():
        if k not in st: errs.append('缺字段 ' + k)
        elif not isinstance(st[k], ty): errs.append('%s 类型应为 %s' % (k, ty.__name__))
    if st.get('status') not in VALID_STATUS and 'status' in st:
        errs.append('status 非法：%s（取 %s）' % (st.get('status'), sorted(VALID_STATUS)))
    # 一致性：nextActions 里 done 的不应还在 openBlockers 文本里出现
    donetext = ' '.join(x.get('desc', '') for x in st.get('nextActions', []) if isinstance(x, dict) and x.get('done'))
    for b in st.get('openBlockers', []):
        if donetext and b and b in donetext:
            warns.append('blocker 疑似已完成却仍列 openBlockers：%s' % b)
    # 新鲜度：STATE.updatedAt 日期 不应早于 最新小节日期（快照落后日志 → 坏快照比没快照更有害）
    nd = newest_section_date(root)
    upd = (st.get('updatedAt') or '')[:10]
    if nd and upd and upd < nd:
        warns.append('STATE.updatedAt(%s) 早于最新小节(%s) → 快照可能过期，刷新 STATE.json 与 §0' % (upd, nd))
    # fileOwnership 存在性
    for role, paths in (st.get('fileOwnership') or {}).items():
        for g in paths:
            if not glob.glob(g.replace('\\\\', os.sep)) and not os.path.exists(g):
                warns.append('fileOwnership[%s] 路径查无（可能失效）：%s' % (role, g))
    for e in errs: print('ERROR:', e)
    for w in warns: print('WARN :', w)
    if not errs and not warns: print('OK STATE.json 结构/新鲜度/一致性通过')
    return 2 if errs else (1 if warns else 0)

# ---------- index ----------
def cmd_index(a):
    root = os.path.abspath(a.root)
    docs = all_docs(root)
    active = [d for d in docs if d['bucket'] == 'active']
    total_active = sum(d['size'] for d in active if d['secno'] != 0)
    lines = ['# 交接索引（自动生成的只读视图）', '',
             '> 由 `handoff.py index` 重建。节号稳定，archive 按 `grep -n "^## N、"` 点查，禁止整篇读入。', '']
    lines.append('| § | 标题 | tags | 体积 | 位置 |')
    lines.append('|---|------|------|------|------|')
    for d in sorted(docs, key=lambda x: (x['bucket'] != 'active', x['secno'] if x['secno'] is not None else 999)):
        secn = '' if d['secno'] is None else d['secno']
        lines.append('| %s | %s | %s | %dB | %s:%d |' % (
            secn, d['title'][:40].replace('|', '/'), '、'.join(d['tags']),
            d['size'], os.path.basename(d['file']), d['start']))
    # 倒排 tag
    tmap = {}
    for d in docs:
        for t in d['tags']: tmap.setdefault(t, []).append((d['secno'], d['file'], d['start']))
    lines += ['', '## tag → 定位', '']
    for t in sorted(tmap):
        refs = ['§%s' % (s if s is not None else '-') for s, f, ln in tmap[t]]
        lines.append('- **%s** → %s' % (t, '、'.join(refs)))
    # 折叠提示
    hint = ''
    if a.max_bytes and total_active > a.max_bytes:
        closed = [d for d in active if d['secno'] not in (None, 0)
                  and re.search(r'(完成|定稿|不改|已关闭|✅|DONE)', d['title'] + d['text'][:60])]
        closed.sort(key=lambda x: x['secno'])
        hint = ('\n\n## ⚠ 待折叠\n活跃区 %dB > 阈值 %dB。建议把已闭环节折进 §0 并将原文整节移入 archive/：\n'
                % (total_active, a.max_bytes)) + '\n'.join(
                '- §%s %s（%dB）' % (c['secno'], c['title'][:30], c['size']) for c in closed[:8])
    lines.append(hint)
    ip = os.path.join(root, 'INDEX.md')
    write_text(ip, '\n'.join(lines) + '\n')
    print('wrote', ip, '(活跃区 %dB)' % total_active)
    if hint: print(hint.strip())
    return 1 if (a.max_bytes and total_active > a.max_bytes) else 0

# ---------- search ----------
def snippet(text, n=120):
    t = re.sub(r'\s+', ' ', text).strip()
    return (t[:n] + '…') if len(t) > n else t

def cmd_search(a):
    root = os.path.abspath(a.dir)
    docs = all_docs(root)
    hits = bm25(a.query, docs)[:a.k]
    if not hits: print('（无匹配，试更短的关键词，或确认 archive 内容）'); return 1
    print('query=%r  命中 %d（top %d）' % (a.query, len(hits), a.k))
    for rank, (sc, d) in enumerate(hits, 1):
        secn = d['secno'] if d['secno'] is not None else '-'
        print('\n#%d  score=%.2f  [§%s]  %s' % (rank, sc, secn, d['title']))
        print('    %s' % snippet(d['text']))
        print('    定位: %s:%d   （只读命中的这一节，勿整篇 load）' % (d['file'], d['start']))
    return 0

# ---------- status：跨会话总览 ----------
STATUS_SKIP_DIRS = {'.backup', 'archive', 'node_modules', '.git', '__pycache__', '.venv'}
STATUS_PRIORITY = {'blocked': 0, 'in-progress': 1, 'done': 2}

def _age_days(iso):
    if not iso: return None
    try:
        s = iso[:19]
        dt = datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
        return max(0, (datetime.datetime.now() - dt).days)
    except Exception:
        return None

def _iter_state_files(root, max_depth):
    root_abs = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root_abs):
        rel = os.path.relpath(dirpath, root_abs)
        depth = 0 if rel == '.' else rel.count(os.sep) + 1
        dirnames[:] = [d for d in dirnames if d not in STATUS_SKIP_DIRS]
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []
        if 'STATE.json' in filenames:
            yield os.path.join(dirpath, 'STATE.json')

def cmd_status(a):
    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print('ERR 目录不存在：' + root); return 2
    allow = None
    if a.status:
        allow = set(x.strip() for x in a.status.split(',') if x.strip())
    rows, errs = [], []
    for p in _iter_state_files(root, a.max_depth):
        try:
            st = json.loads(read_text(p))
            if not isinstance(st, dict): raise ValueError('not a dict')
        except Exception as e:
            errs.append((p, str(e))); continue
        na = st.get('nextActions') or []
        total = len(na) if isinstance(na, list) else 0
        done = sum(1 for x in na if isinstance(x, dict) and x.get('done')) if total else 0
        blk = st.get('openBlockers') or []
        upd = st.get('updatedAt') or ''
        rows.append({
            'path': p,
            'status': st.get('status') or '?',
            'session': st.get('session') or os.path.basename(os.path.dirname(p)),
            'title': (st.get('title') or '')[:80],
            'phase': (st.get('phase') or '')[:60],
            'updatedAt': upd,
            'age_days': _age_days(upd),
            'blockers': len(blk) if isinstance(blk, list) else 0,
            'act_done': done, 'act_total': total,
        })
    if allow is not None:
        rows = [r for r in rows if r['status'] in allow]
    if a.stale_days is not None:
        rows = [r for r in rows if r['age_days'] is not None and r['age_days'] >= a.stale_days]
    rows.sort(key=lambda r: (STATUS_PRIORITY.get(r['status'], 9),
                             -(r['age_days'] if r['age_days'] is not None else 10**6),
                             r['session']))
    if a.format == 'json':
        print(json.dumps({'root': root, 'count': len(rows),
                          'errors': [{'path': p, 'error': e} for p, e in errs],
                          'sessions': rows}, ensure_ascii=False, indent=2))
        return 0
    by = Counter(r['status'] for r in rows)
    other = sum(v for k, v in by.items() if k not in ('in-progress', 'blocked', 'done'))
    print('共 %d 个任务  in-progress:%d  blocked:%d  done:%d  其他:%d  root=%s' % (
        len(rows), by.get('in-progress', 0), by.get('blocked', 0), by.get('done', 0), other, root))
    print()
    if not rows:
        print('（无匹配任务）')
    else:
        print('%-11s %-11s %-5s %-8s %-24s %s' % ('STATUS', 'UPDATED', 'AGE', 'ACT/BLK', 'SESSION', 'TITLE'))
        print('-' * 106)
        for r in rows:
            age = '-' if r['age_days'] is None else ('%dd' % r['age_days'])
            print('%-11s %-11s %-5s %-8s %-24s %s' % (
                r['status'], (r['updatedAt'] or '')[:10] or '-', age,
                '%d/%d b=%d' % (r['act_done'], r['act_total'], r['blockers']),
                r['session'][:24], r['title'][:44]))
    if a.stale_days is not None and rows:
        print()
        print('（仅列 updatedAt ≥ %d 天前的）' % a.stale_days)
    if errs:
        print()
        for p, e in errs:
            print('ERR %s: %s' % (p, e))
    return 1 if errs else 0

# ---------- install-hooks：把 skill/hooks/*.sh 部署到 ~/.qoder/hooks ----------
def cmd_install_hooks(a):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.abspath(a.source or os.path.join(script_dir, '..', 'hooks'))
    if not os.path.isdir(src):
        print('ERR skill hooks 源目录不存在：' + src); return 2
    files = sorted(f for f in os.listdir(src) if f.endswith('.sh'))
    if not files:
        print('ERR 源目录无 .sh：' + src); return 2
    tgt = os.path.abspath(os.path.expanduser(a.target))
    os.makedirs(tgt, exist_ok=True)
    bkp = os.path.join(tgt, '.backup'); os.makedirs(bkp, exist_ok=True)
    ts = time.strftime('%Y%m%d-%H%M%S')
    print('source: ' + src)
    print('target: ' + tgt)
    err = 0
    for fn in files:
        sp = os.path.join(src, fn); tp = os.path.join(tgt, fn)
        with open(sp, 'rb') as f: src_bytes = f.read()
        src_h = hashlib.sha256(src_bytes).hexdigest()
        if os.path.isfile(tp):
            with open(tp, 'rb') as f: cur = f.read()
            if hashlib.sha256(cur).hexdigest() == src_h:
                print('  =   %-28s 内容一致，跳过' % fn); continue
            b = os.path.join(bkp, '%s.pre-install-%s' % (fn, ts))
            with open(b, 'wb') as f: f.write(cur)
            print('  B   %-28s 已备份旧版 → %s' % (fn, os.path.relpath(b, tgt)))
        with open(tp, 'wb') as f: f.write(src_bytes)
        try: os.chmod(tp, 0o755)
        except Exception: pass
        with open(tp, 'rb') as f: ok = hashlib.sha256(f.read()).hexdigest() == src_h
        if ok:
            print('  ✓   %-28s sha256 %s…' % (fn, src_h[:12]))
        else:
            print('  ✗   %-28s 校验失败！' % fn); err += 1
    print('done.  errors=%d' % err)
    return 1 if err else 0

def main():
    ap = argparse.ArgumentParser(prog='handoff.py', description='session-handoff 读模型/分层/本地检索（离线）')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init'); p.add_argument('dir'); p.add_argument('--title'); p.add_argument('--phase'); p.add_argument('--force', action='store_true'); p.set_defaults(func=cmd_init)
    p = sub.add_parser('validate'); p.add_argument('dir'); p.add_argument('--fix-hint', action='store_true'); p.set_defaults(func=cmd_validate)
    p = sub.add_parser('index'); p.add_argument('root'); p.add_argument('--max-bytes', type=int, default=20480); p.set_defaults(func=cmd_index)
    p = sub.add_parser('search'); p.add_argument('dir'); p.add_argument('query'); p.add_argument('-k', type=int, default=5); p.set_defaults(func=cmd_search)
    p = sub.add_parser('status', help='跨会话总览：遍历 root 下 STATE.json 出当前态大表')
    p.add_argument('root', nargs='?', default='.'); p.add_argument('--status', help='逗号分隔过滤，如 in-progress,blocked')
    p.add_argument('--stale-days', type=int, help='只显示 updatedAt ≥ N 天前的'); p.add_argument('--max-depth', type=int, default=4)
    p.add_argument('--format', choices=['table', 'json'], default='table'); p.set_defaults(func=cmd_status)
    p = sub.add_parser('install-hooks', help='把 skill/hooks/*.sh 部署到 ~/.qoder/hooks（备份 + sha256 校验）')
    p.add_argument('--source', help='默认取脚本同级的 ../hooks'); p.add_argument('--target', default='~/.qoder/hooks')
    p.set_defaults(func=cmd_install_hooks)
    a = ap.parse_args()
    sys.exit(a.func(a) or 0)

if __name__ == '__main__':
    main()
