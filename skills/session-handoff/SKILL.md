---
name: session-handoff
description: 会话交接/对接文档范式（通用，不限编程）。任何连续多会话任务——编程开发、作业/解题、论文/写作、翻译、调研、数据处理等——需保留进度/需求/踩坑给后续会话（新对话、其他 agent）时，创建或增量更新交接文档与 AGENTS.md，保证新会话读文档即可接续。含专家团模式：多个会话各扮演一个专家角色协作同一任务。触发：用户说"注意会话交接""更新交接文档""这是交接""新会话看文件""专家团""多会话协作""我是XX角色会话"；任务跨多会话/需分批推进/发现需沉淀的坑。
---

# Session Handoff — 会话交接范式（核心）

> 本文件只含每次会话都需要的最小核心。场景细则按需 Read 对应文件，禁止一次全读。

## 参考索引（按需加载，命中场景才 Read）

| 场景 | Read |
|---|---|
| 专家团 / 多会话协作 | `references/expert-team.md` |
| 新建交接文档，或活跃区 > 20 KB 需归档 | `references/archiving.md` |
| 任务是编程 / 开发 | `references/programming-plugin.md` |
| 机器要读当前态 / 活跃区超阈要折叠 / 跨会话找回旧结论 | `references/state-schema.md`（STATE.json 读模型 + §0 分层折叠 + 本地 BM25 检索） |

- 适用范围：任何跨会话任务（编程、作业/解题、论文/写作、翻译、调研、数据处理等）；核心机制领域无关
- 非编程任务：无 git/编译条款；验证证据写实际核对方式（复算、对答案、交叉审阅）

## 流程

0. **会话开始（强制）**：先找 `AGENTS.md` 并 Read 载入当前会话（搜索顺序：`.handoff/AGENTS.md` → 根目录 `AGENTS.md`），全程严格遵守其中约定（路径/环境/规范/红线）；找不到才跳过。交接文档旁若有 `STATE.json`，先读它取"机器视角的当前态"（阶段/未闭环阻塞/下一步/文件归属），配合文档顶部 §0 滚动摘要作为人类入口——二者不一致时以正文小节为准并回头修 STATE.json
1. **找**：是否已有交接文档？（`.handoff/` 目录 → `*实施计划*.md` / `*交接*.md` → AGENTS.md 中引用的路径）
2. **无** → 复制 `assets/handoff-template.md` 新建。**默认创建 `.handoff/` 子目录**存放所有交接文件（AGENTS.md / STATE.json / 交接文档.md），并在项目根 `.gitignore` 中添加 `.handoff/` 规则，确保交接文档不提交到项目仓库。如用户指定其他目录则遵从用户意见。按 `references/archiving.md` 建立双文件结构；建议用 `python scripts/handoff.py init` 一键脚手架（建 §0 滚动摘要 + STATE.json + archive/ + .backup/）；**有** → 只追加本次会话小节，禁止覆盖
3. **会话结束** → 追加 `## N、YYYY-MM-DD 会话：<主题>`：完成内容（关键结论）、验证证据（编程=编译/测试结果，作业/写作=核对或审阅方式；未验证写"待验证"）、新坑（现象→根因→处理→已修复/遗留）、环境变更（工具/账号/命令）、遗留/待办（完成划掉）；**同轮更新旁侧 `STATE.json`**（status/openBlockers/nextActions/fileOwnership/updatedAt 反映追加后的真相，别留过期态）。**活跃区超折叠阈值时**：把最老的已闭环小节摘要进 §0 滚动摘要（下移到 Tier1，正文原样保留供 grep），再跑 `python scripts/handoff.py index` 重建检索索引
4. 临时文件：统一目录 + 声明生命周期（仅当前会话 → 交接时删除）

## 行为纪律（强制）

- **同项目 = 同打开目录**：大部分时候在同一目录打开的会话才算同一个项目；用户需确保每次打开一个项目时固定用同一目录，否则会被当作其他项目（各自独立交接文档，进度不互通）。同一目录内发现混有多个项目/任务时，与用户确认后为各项目分别建交接文档，并在 AGENTS.md 写清"哪个项目 → 哪份文档"
- **未经允许不做不可逆/外部可见操作**：git commit / git push、提交作业、发送消息、发布内容、删除大段成果等，一律禁止，除非用户明确允许（"可以提交""提交吧"等）；本地可逆操作（编辑/编译/试算/查资料）可自主进行
- **用户在并行编辑同一份文件时，立刻停止交接文档的生成/更新（最高优先，覆盖本节其他条款）**
  - 判据：交接文档所描述的对象（代码、成果文件、工作区态）在你的两次核对之间又变了（`git diff`/`git status`/mtime 任一变化），或用户明说"我在改""先别动"
  - 禁止动作：**继续写文档、改用户的文件、把已失效的措辞就地补一句**——文档里"我刚改过/未提交/待生效"这类陈述一旦与磁盘态不符，下个会话会照它行动，**坏文档比没文档更有害**；也不要为了追平而反复重写同一条（每追一次都在制造新的过期句）
  - 正确收尾：①停手，把"当前工作区态 ≠ 文档说法"这一事实直接告知用户，附最新 `git status`/`git diff` 证据；②未完成的归档/瘦身**留到用户编辑结束后再做**（体积超阈值是可用多次会话解决的事，失真陈述不是）；③若必须留痕，只写不随用户编辑漂移的中性事实（如"用户正在改 X 文件，其结论待其编辑完成后复核"），不写具体行号/改动清单
  - 同理适用于自己：落盘改动可能被用户的编辑器静默覆盖 → 改完同轮用命令复核，发现被覆盖**不要写回去抢用户的编辑**，报事实由用户定
- **编译失败兜底（编程任务）**：命令行编译连续失败 2 次即停止尝试，报告原因并请用户在 IDE 中编译；禁止为让编译通过而改动本地仓库 jar / 依赖 / 配置

## 关系

- AGENTS.md = 静态约定（背景/架构/规范/文档路径）；交接文档 = 动态进度（分批/踩坑/环境/遗留）
- 默认存放在 `.handoff/` 子目录（已 gitignore），不提交到项目仓库
- 每次会话结束必更新交接文档；AGENTS.md 仅约定变化时改

## 成本规则（token）

- 只记新会话需要但不显然的信息（绝对路径/完整命令/账号/坑）；不写废话
- 小节只追加不重写；条目式，不用长段落；不复制代码/日志/长文本全文（只写结论 + 路径）
- 会话开始**先读 `STATE.json` + 顶部 §0 滚动摘要**，O(1) 拿到"当前态/下一步/未闭环"，不必整篇读入活跃区；只有要具体细节时才按节号进对应小节
- 需要历史结论时用 `python scripts/handoff.py search "<关键词>"`（离线 BM25，覆盖活跃区 + archive/）单点定位，替代手动 grep 与整篇读入；§0 本身是折叠产物，不进检索
- 有多个交接会话不知先接哪个时，用 `python scripts/handoff.py status`（遍历所有 STATE.json 出当前态大表，blocked/超期的排前面），一次看清全局，不必逐个目录读 STATE.json；再用 `search`/直接读该会话 §0 深入
- 需要提醒用户开新会话时，判据用可观测量：活跃区 > 20 KB 且本会话已追加 ≥ 2 个小节，或任务已切换到新批次

## 模板与参考

- `assets/handoff-template.md` — 交接文档模板（新建时复制）
- `assets/expert-team-template.md` — 专家团 TEAM.md 模板
- `assets/code-standard-template.md` — 代码规范章节模板（仅编程）
- `references/` — 场景细则（见上方索引）
- `scripts/handoff.py` — 零依赖纯标准库工具：`init`（脚手架 §0+STATE.json+archive/.backup）、`validate`（STATE.json schema/新鲜度/一致性）、`index`（重建 INDEX.md 检索索引 + 顶部「⚠ 待折叠」清单）、`search "<关键词>"`（离线 BM25 跨活跃区+archive 定位）、`status [<root>]`（遍历 root 下所有 STATE.json 出跨会话当前态大表，`--status`/`--stale-days` 过滤、`--format json` 供机器消费）、`install-hooks`（把 `hooks/*.sh` 部署到 `~/.qoder/hooks`：内容一致跳过、有变动先备份旧版到 `.backup/` 再写 + sha256 校验）。详见 `references/state-schema.md`
- `hooks/` — Stop/PostToolUse hook 的**源真相**（`handoff-stamp.sh` 打标记、`handoff-stop-check.sh` 结束拦截 ①小节 ②折叠/归档 ③STATE.json 新鲜度），运行时用 `install-hooks` 装到 `~/.qoder/hooks/`；改 hook 只改这里再重装，勿直接编辑运行时副本。`hooks/README.md` 讲源↔安装关系与 ①②③ 语义
- 归档由 `hooks/handoff-stop-check.sh`（经 `install-hooks` 装到 `~/.qoder/hooks/`）在会话结束 Stop 时按字节强制（阈值 20 KB，`HANDOFF_SIZE_LIMIT` 可覆盖）：超阈/STATE 过期会**逐目录打印可直接复制的 `handoff.py index/validate/search/status` 命令**，并指示先读 `INDEX.md` 顶部「⚠ 待折叠」清单挑候选节，再决定折叠 §0 还是搬 archive
