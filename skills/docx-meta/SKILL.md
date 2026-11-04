---
name: docx-meta
description: Word 文档(.docx)元数据与个人信息清理的独立后处理 skill。支持首次生成与反复人工修改后的常态收尾：默认首次建立包外时长基线，之后累计编辑时间，抵抗 Word/WPS 保存后 TotalTime 归零；支持用户追加分钟数、文档已有累计值及内容改动估算。清理作者、自定义属性、缩略图和审阅者信息，同步时间线与统计字段。触发场景：生成 Word 后交付、修改后重新清理、总编辑时间为零或减少、清除 docx 元数据/隐私信息、创建时间与编辑时长不一致、审阅者姓名残留。不适用于 PDF/PPTX/XLSX。
---

# docx-meta

## 用途与常规流程

对任意 `.docx` 做元数据收尾，与生成器解耦；保留正文、版式、图片和批注/修订内容，仅清理属性与审阅者标识。

**生成 → 首次收尾并保存基线 → 人工修改并保存 → 关闭 Word/WPS → 再次收尾 → 复核 → 交付。** 修改、收尾可以反复进行，不要求用户放弃编辑，也不要为了清元数据重新生成并覆盖人工改动。

默认 `--mode auto` 自动选择两种模式：无本地基线时初始化，有基线时累计。首次生成后就运行一次，才能在后续编辑器清零 `TotalTime` 时保留原总时长。

## 两种模式

### 模式一：首次初始化

- 无基线时，优先保留文档已有的正数 `TotalTime`；否则按正文规模估算。
- `--mode initial` 明确重新按全文估算并重建基线；用于同路径换了另一份文档、或确实要重置历史，不用于普通修订。
- `--edit-minutes N` 始终表示**绝对总分钟数**，覆盖并重建基线，允许 0；不要把本次新增分钟数传给它。
- 首次估算沿用下式，每次输出会标明来源；它不是实际人工编辑记录。

```text
base      = CJK字符数 / chars_per_min + 拉丁词数 / words_per_min
overhead  = max(0, 段落数-1)*0.4 + 表格数*4 + 图片数*2 + 标题数*1.5
jitter    = 0.92 + (SHA-256(正文)前2字节转整数 % 21) / 100
TotalTime = clamp(round((base + overhead) * jitter), 8, 6000)  # 分钟
```

### 模式二：再次修改后的累计

默认有基线就启用，也可用 `--mode update` 强制要求存在基线，防止丢失历史后悄悄初始化。按以下优先级**择一**，不是把几种来源相加：

1. **用户提供本次分钟数**：`--add-minutes N` → 上次总时长 + N。纯排版、阅读校对、思考耗时优先用这一项；需要已有基线，不与 `--edit-minutes` 同用。每次显式追加代表一段新的编辑时间，不要重复执行同一个追加命令；之后普通重跑不会再次加 N。
2. **文档已有总时长增长**：若当前 `TotalTime` 大于基线，采用当前值作为新的总量，不再额外叠加估算。这是编辑器提供的值，不保证是准确的活动计时。
3. **内容改动估算**：比对上次与当前的文本 token 指纹，对新增、替换、删除的片段及媒体字节变化估算成本；仅在文本/媒体发生变化时附加段落/表格/标题数量变化的开销，再追加到基线。不是两份全文估算值相减，同字数替换、删改也能产生增量。小改动至少估 1 分钟，不套用首次的 8 分钟下限；仅改标题样式或空段落不自动计时。
4. **无法估量的改动**：没有可估量内容增量时保留旧总量，并提示可用 `--add-minutes` 补充排版、阅读或思考时间；不能把“未计入”说成“实际耗时为零”。

同一版本普通重跑不累计；隔几天才保存也不会把空闲时间计入。旧值被 WPS 清零/删除时从包外基线恢复，不以 0 覆盖历史。估算总量和推算增量必须明确说是估算，不能宣称证明了人工写作时长。

## 基线保存与丢失处理

- 默认存用户本地数据目录：Windows 为 `%LOCALAPPDATA%/docx-meta/`；其他系统为 `$XDG_STATE_HOME/docx-meta/`（未设置时 `~/.local/state/docx-meta/`）。`DOCX_META_STATE_DIR` 可覆盖目录。
- 按文档规范化绝对路径的哈希区分文件；记录总分钟、来源、时间线、token/媒体指纹，不保存正文原文，也不写入 DOCX 自定义属性。指纹不等于匿名化，仍按本地工作数据保护，不上传、不随交付打包。
- 命令及 `--inspect` 输出基线位置。改名、移动或换机器时，显式用 `--state-file "原基线.json"` 续接同一文档；显式基线一次只能处理一个 DOCX。不要为无关文档复用基线。
- 旧版处理过的文档可能还没有基线：默认可接纳包内尚存的正数总时长；若它已丢失，只能首次估算或由用户用 `--edit-minutes` 指定已知总量，**无法从时间戳恢复真实历史**。`--mode update` 会报错而不是猜。
- 损坏基线停止写入，先检查/备份；确认要放弃历史后才用 `--mode initial` 重建。
- 写文件前取得基线锁，先准备新状态，DOCX 重写成功后才替换基线；失败不冒充成功。遇到 `.lock` 不抢删，先确认另一进程是否还在运行。
- `--inspect` / `--dry-run` 不写文档或基线；`--dry-run` 也不建立锁和状态目录。

## 清理内容与时间线

1. 删除核心作者、最后修改者、标题、主题、描述、关键词、类别等个人属性，`revision` 置 1；显式 `--author` / `--title` 可保留指定值。
2. 以文件 mtime 或 `--modified` 为锚点；初始化采用文件创建时间，累计沿用上次的 core 创建时间；显式 `--created` 优先。若跨度不足总分钟数，把创建时间前移，使 `modified - created ≥ TotalTime`。已有更长历史不压缩成一次连续编辑。
3. 默认同步 core、文件 mtime/atime 与 Windows birthtime。`--copy-style` 保留文件系统重写时刻作为出生时间，core 仍维护时间线；其 FS 创建晚于修改不代表损坏。非 Windows 无可移植的出生时间写入接口。
4. 创建/更新 `docProps/app.xml` 及注册，统一 `Application=Microsoft Office Word`、`AppVersion=16.0000`、`Template=Normal.dotm`；这些是规范化兼容值，**不代表文档真的由该软件生成**。清空 Company/Manager/HyperlinkBase，移除 HeadingPairs/TitlesOfParts。
5. 更新 Words/Characters/CharactersWithSpaces/Lines/Paragraphs 等统计；Pages 默认估算，可传 `--pages N` 覆盖为实际渲染页数。只改页数属性，不改变真实分页。
6. 删除 `docProps/custom.xml`、`docProps/thumbnail.*`、`word/people.xml` 及对应关系/内容类型注册。`word/*.xml` 的 `w:author` / `w:initials` 默认置空，审阅内容保留。
7. 保留 ZIP 条目顺序、压缩方式、外部属性，内部时间戳统一为 modified；临时文件通过 ZIP/关键 XML 校验后原子替换。

## 用法

在 skill 目录下执行（路径也可换成脚本绝对路径）：

```bash
python scripts/docx-meta.py "文档.docx"
python scripts/docx-meta.py --inspect "文档.docx"
# 修改保存并关闭编辑器后，再运行同一命令即可自动累计
python scripts/docx-meta.py "文档.docx"
# 已知本次额外编辑 15 分钟；只追加一次
python scripts/docx-meta.py --mode update --add-minutes 15 "文档.docx"
# 指定绝对总量、实际页数
python scripts/docx-meta.py --edit-minutes 90 --pages 12 "文档.docx"
# 改名后明确续接原基线
python scripts/docx-meta.py --mode update --state-file "原基线.json" "文档定稿.docx"
python scripts/docx-meta.py --backup --author "代欣江" "文档.docx"
python scripts/docx-meta.py a.docx b.docx c.docx
```

| 参数 | 作用 | 默认 |
|---|---|---|
| `--mode auto/initial/update` | 自动选择 / 重置初始化 / 必须有基线的累计 | auto |
| `--edit-minutes N` | 绝对总分钟数，重建基线 | 按模式解析 |
| `--add-minutes N` | 在基线上追加本次分钟数，每次调用均追加 | 不指定 |
| `--state-file PATH` | 显式 JSON 基线，可续接改名文档，仅单文档 | 用户数据目录 |
| `--pages N` | 实际渲染页数属性，正整数 | 估算 |
| `--inspect` / `--dry-run` | 只读检查 / 预演，不写文档与基线 | — |
| `--author` / `--company` / `--title` | 指定保留内容 | 删除或清空 |
| `--created` / `--modified` | ISO 时间覆盖 | 文件时间、已有基线及跨度校正 |
| `--copy-style` | FS 出生时间保留在重写时刻 | 关闭 |
| `--chars-per-min` / `--words-per-min` | 中文字/分钟、拉丁词/分钟 | 45 / 32 |
| `--revision` | 修订号 | 1 |
| `--keep-thumbnail` / `--keep-custom-properties` / `--keep-people` / `--keep-review-authors` | 保留对应数据 | 清理 |
| `--backup` | 生成含原元数据的 `.bak`，不含基线历史备份 | 关闭 |

## 复核

执行 `--inspect`，检查作者/最后修改者、removable parts、review authors 均为空；检查 `app.TotalTime` 与基线总量、来源，以及 `core.modified - core.created ≥ TotalTime`。普通模式 Windows 的 FS created 与 core.created 一致；`--copy-style` 除外。访问时间写入时等于 modified，之后可被系统读取刷新。

在 Windows 文件属性 → 详细信息或 Word 高级属性中核对“总编辑时间”。普通重复收尾应保留数值；修改后清零样本应恢复基线并追加适用增量。不要只凭终端计算日志断言属性已写入；打开 Office 检查后若再次保存，关闭并重新收尾。

```bash
PYTHONUTF8=1 python -B scripts/test_docx_meta.py -v
```

回归使用临时样本与独立状态目录，覆盖清理、时间线、累计、归零恢复、改删文本、明确追加、重复运行、基线丢失/损坏、只读预演与失败保护；不碰用户文档。模拟保存回归不等于所有 Word/WPS 版本的真实保存验收。

## 边界与集成

- 只支持 `.docx`；`.doc` 先另存。不处理签名/加密文档，重写会破坏签名。
- 不清理正文中的姓名/邮箱、图片 EXIF、嵌入对象和 customXml；需另行内容审查。
- 不因编辑器再次保存就断言所有属性必然清零；具体行为取决于软件、版本与文档，检查实际值。
- 不用“属性空白/总时间 0”判断是否人工写作；不把目录时间戳跨度当作实测编辑时间。
- 调用脚本（wrapper）不要在收尾后再次删除 TotalTime/Application 等属性，也不要固定传 `--edit-minutes 0`；普通累计直接调用本脚本。真实页数用 `--pages`，不必二次改 ZIP。用户明确选择留空/不估算的独立项目策略需另行确认，不擅自覆盖。
- `course-assignment` 等生成链路首次及每轮修改后均调用；要重新生成时先保全并回流人工修改。换成无关文档才重置基线，同一文档的修订不重置。
- 交付只包含用户需要的文件；`.bak` 保留原隐私信息，不随交付，删除前遵守用户授权。
