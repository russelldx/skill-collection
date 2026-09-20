# 读模型 + 分层压缩 + 本地检索（补救三件套）

> 触发：需要机器可解析的当前态、活跃区超阈要折叠、或要跨会话找回旧结论时 Read 本文件。
> 背景：原 session-handoff 只有 append-only 的 `HANDOFF.md`（事件日志），缺①机器可读的当前态、②分层降采样（只有 20 KB 一刀切）、③跨会话语义召回。本文件把后端的老原则搬进来：**CQRS（读写模型分离）+ 冷热分层（存储分级）+ log compaction**。
> **不依赖 claude-mem / 任何网络**：检索用随包的 `scripts/handoff.py`（纯标准库 BM25，CJK 友好）。

## 一、读模型：STATE.json（物化视图 / read model）

`HANDOFF.md` 同目录放一份 `STATE.json` —— **给机器读的当前态快照**，有界、不增长、每次会话刷新。人读 markdown，机器读 STATE.json，各走各的。

字段（保持极小，别塞进散文）：

| 字段 | 类型 | 含义 |
|---|---|---|
| `schemaVersion` | int | 结构版本，向后兼容用，当前 1 |
| `session` / `title` | str | 会话标识 / 任务主题 |
| `phase` | str | 当前聚焦（一句话） |
| `status` | str | `in-progress` \| `blocked` \| `done` |
| `updatedAt` | str | ISO 时间；**校验器用它判快照是否落后日志** |
| `openBlockers[]` | list | 未决阻塞（只列还开着的，done 的移出） |
| `nextActions[]` | list[obj] | `{id,desc,owner,done}` 机器可执行待办 |
| `fileOwnership{}` | dict | `角色或会话 → [路径/glob]`，专家团防撞车 |
| `artifacts[]` | list[obj] | `{path,purpose}` 关键产物 |
| `keyDecisions[]` | list[obj] | `{id,date,decision}` 决策留痕 |
| `tags[]` | list | 全局标签，喂检索与索引 |

**单一真相源原则**：STATE.json 是**派生视图**，不是第二份手写账。规则是"markdown 有、STATE 也要同步刷新"；不确定就以 markdown 为准重生成 STATE。`validate` 会抓两类漂移：`updatedAt` 早于最新小节（快照过期）、`fileOwnership` 路径查无（引用失效）。

## 二、分层压缩：从"一刀切倾倒"到"梯度折叠"

旧模型二值：活跃区 → 涨到 20 KB → 整节 dump 进 archive。新模型分四档，**每档各管各的容量**，没有单一悬崖：

```
Tier 0  §0 滚动摘要        —— 新会话首读；唯一允许每次重写的 rollup（软上限 ~4 KB）
Tier 1  活跃区最近几节原文  —— append-only，全保真，软上限 20 KB（hook 阈值不变）
Tier 2  milestones.md      —— §0 自身涨顶后，把更早的里程碑二级 rollup 到这里（递归摘要）
Tier 3  archive/ 原始全量   —— 全保真冷存，只按节号点查，永不整篇 load
Tier 4  （语义召回）        —— 原计划交 claude-mem；因网络不可用，改由 handoff.py 本地 BM25 承担
```

**折叠（fold）操作**——活跃区超 Tier1 阈值时，对每个"已标完成/定稿/不改"的最旧节 §n：

1. `extract_actionable_facts(§n)`：只抽"可执行事实"（结论/路径/仍生效的坑/未决），**叙事丢弃、事实零损失**；把结果合并进 §0（去重、同类合并，沿用 archiving.md 既有纪律）。
2. 原文整节**逐字**移入 `archive/HANDOFF.md`（保留原节号，跨节引用仍可 `grep`）。
3. §0 若自身超 ~4 KB：把更早的里程碑折进 `milestones.md`（Tier 2 递归）。
4. 刷新 STATE.json（`updatedAt`、`phase`、`openBlockers`、`nextActions`）。

**折叠是判断题，由 agent 做**（沿用"hook 只提示不代做"）；`handoff.py index` 只做机械的体积测量 + 报"待折叠"清单，不替你决定哪些是"可执行事实"。

## 三、本地检索：handoff.py search（替代 claude-mem）

`claude-mem` 需要常驻 MCP + 网络，本环境不可用。跨会话"这事以前解决过吗"改用随包脚本，**纯标准库、离线、CJK 友好**：

```bash
# 对 active + archive 全部小节做 BM25 排序，回节号 + 摘要 + 定位行
python scripts/handoff.py search "<交接目录>" "关键词 或 中文短语" -k 5
```

原理：中文无空格，脚本把 CJK 按**单字 + 相邻双字**切词，拉丁按词切，再跑标准 BM25（k1=1.5, b=0.75）。够覆盖 80% 的"以前踩过这个坑吗"，且不需要 embedding、不需要联网、不需要装包。命中的节**只 `grep` 定位读那一节**，不整篇 load。

> 想要真·语义（同义改写也能召回）才需要向量检索；纯离线前提下 BM25 是最佳性价比。若哪天 claude-mem 可用，把 Tier 4 换回 mem-search 即可，其余不动。

## 四、六个子命令

```bash
handoff.py init          <dir> [--title T --phase P]   # 生成 HANDOFF.md(含§0) + STATE.json + archive/ + .backup/
handoff.py validate      <dir>                          # 校验 STATE.json 结构/新鲜度/一致性；退出码 0/1/2
handoff.py index         <dir> [--max-bytes N]          # 重建 INDEX.md（节号/tags/体积倒排）+ 顶部"⚠ 待折叠"清单
handoff.py search        <dir> "<query>" [-k K]         # 本地 BM25 找回旧结论（活跃区+archive）
handoff.py status        [<root>] [--status ..] [--stale-days N] [--format table|json]  # 跨会话当前态大表
handoff.py install-hooks [--source DIR --target DIR]    # 把 skill hooks/*.sh 部署到 ~/.qoder/hooks（备份+sha256 校验）
```

`INDEX.md` 是人机共享的只读视图：节号稳定、tag→定位倒排，新会话可先扫 INDEX 再决定读哪节，避免整篇 load。`index` 只测体积、报哪些已闭环节可折，不替你决定"可执行事实"。

`status` 是**跨文档全局索引的"当前态"那一半**：递归 root 下所有 `STATE.json`（自动跳过 `.backup/archive/node_modules/.git` 等），每个任务一行，按 `blocked < in-progress < done` 优先级、再按"距今多少天"降序排——所以下面几个总是最该接的。`--status blocked,in-progress` 只看没闭环的，`--stale-days 7` 只揪一周没动静的僵尸任务，`--format json` 给脚本/仪表盘消费。它只读 STATE.json（读模型），不 parse 大段 markdown，所以很快；前提是每个会话都守住了"改文档同轮刷 STATE"的规矩（漏刷的会被 validate 抓）。

`install-hooks` 解决"skill 里的 hook 是源、`~/.qoder/hooks` 是运行时副本"的同步问题：内容一致跳过，有变动先把运行时旧版备份到 `~/.qoder/hooks/.backup/<fn>.pre-install-<ts>` 再覆盖并 sha256 复核。改 hook 永远改 skill `hooks/` 里那份，再跑一次它部署，别直接编辑运行时副本。

## 五、与既有件的关系

- `SKILL.md` 流程已加入：会话开始读 `§0 + STATE.json`；会话结束"追加小节 →（可选）折叠 → 刷新 STATE → 重建 INDEX"。
- `archiving.md` 的"整节移到 archive"是本文件 Tier 1→3 的具体化，二者一致。
- hook `handoff-stop-check.sh` 的 20 KB 检测不变（仍兜底防膨胀），但 ②/③ 现在会解析出 `handoff.py` 的绝对路径，指示先读 `INDEX.md` 顶部"⚠ 待折叠"清单挑候选节，并**逐目录打印可直接复制的 `index / validate / search / status` 命令**——把 hook 的"该瘦身了"直接接到工具动作上，不再停在口号式提示。
- hook 源改放在 skill 的 `hooks/` 目录（`handoff-stamp.sh` + `handoff-stop-check.sh` + `README.md`），是**唯一该编辑的那份**；`~/.qoder/hooks/` 只是运行时副本，靠 `install-hooks` 部署（内容一致跳过、有变动先备份再写并 sha256 复核）。skill 以 `.qoder/skills/session-handoff/` 为唯一权威副本（QoderWork 时代的 `.qoderwork` 双副本已于 2026-09-15 随迁移删除）。
- Windows 体质坑（`\r\n` 虚增字节、控制台 GBK 乱码、`grep -c` 非计数）见 `archiving.md`，脚本已强制 `encoding=utf-8, newline=''`。
