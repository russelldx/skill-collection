---
name: docx-meta
description: Word 文档(.docx)元数据与个人信息清理的独立后处理 skill，可在任何生成/编辑 docx 的工具之后使用。默认删除作者/最后修改者/标题/描述等核心属性，清理自定义属性、缩略图、人员列表、批注与修订作者，按正文规模动态估算总编辑时间并回填 Word 统计字段，把创建/修改/访问时间整理成"创建+总编辑时间=修改=访问"的闭环时间线。触发场景：生成 Word 后交付前、去掉文档作者、清除 docx 元数据/隐私信息、总编辑时间(TotalTime)、创建时间与编辑时长不一致、属性里显示 python-docx/Claude/WPS、审阅者姓名残留、文档看起来像 AI 生成。不适用于 PDF/PPTX/XLSX。
---

# docx-meta

## 用途

对任意 `.docx` 做交付前的元数据规范化：只改 ZIP 包里的属性部件，不碰正文、版式与图片。与生成器完全解耦——无论上游是 `anthropic-docx`、python-docx、docx-js、pandoc、Word 还是 WPS，产物都是 `.docx`，本 skill 都能处理，上游 skill 更新后无需同步修改。

## 何时执行

- 任何 `.docx` 生成完成、最终交付之前。
- 用 Word/WPS 做过最后一次人工保存或修订之后（保存会重新写入元数据）。
- 用户提到"作者怎么是我""总编辑时间是 0""一眼看出是 AI 生成"。

典型链路：生成 docx →（可选人工检查/Word 保存）→ 运行本 skill → `--inspect` 复核 → 交付。

## 默认清理内容

1. **核心属性**：删除 `dc:creator`、`cp:lastModifiedBy`、`dc:title`、`dc:subject`、`dc:description`、`cp:keywords`、`cp:category`、`cp:contentStatus`、`cp:identifier`、`cp:language`、`cp:version`、`cp:lastPrinted`；`revision` 置 1。
2. **时间线闭环**：以 `modified`（文件 mtime 或 `--modified`）为锚点；若 `created`（文件 birth 或 `--created`）到 `modified` 的间隔小于 `TotalTime`，把 `created` 前移到 `modified - TotalTime`，访问时间置为 `modified`，即 `创建 + 总编辑时间 = 修改 = 访问`。已有更长历史（间隔 ≥ TotalTime）的文档保留原创建时间。重写后同步 core 属性、文件 mtime/atime 与 Windows birthtime，统一 UTC/W3CDTF。
3. **扩展属性**：`docProps/app.xml` 缺失时按 Word 结构创建并补注册；`Application=Microsoft Office Word`、`AppVersion=16.0000`、`Template=Normal.dotm`；`Company`/`Manager`/`HyperlinkBase` 置空；移除 `HeadingPairs`/`TitlesOfParts`；`Pages`/`Words`/`Characters`/`CharactersWithSpaces`/`Lines`/`Paragraphs` 按正文重算。
4. **总编辑时间**：写入 `TotalTime`，公式见下节。
5. **删除部件**：`docProps/custom.xml`（WPS 版本号/ICV、邮箱等自定义属性）、`docProps/thumbnail.*`（内容预览图）、`word/people.xml`（审阅者列表），并同步移除对应关系与内容类型注册。
6. **审阅作者**：`word/*.xml` 中所有 `w:author` / `w:initials` 置空；批注与修订内容本身保留。
7. **ZIP 完整性**：保留条目顺序、压缩方式、外部属性；内部时间戳统一为 `modified`；写临时文件并通过 ZIP/关键 XML 校验后原子替换。

## 总编辑时间公式

```
base     = CJK字符数 / chars_per_min + 拉丁词数 / words_per_min
overhead = max(0, 段落数-1)*0.4 + 表格数*4 + 图片数*2 + 标题数*1.5
jitter   = 0.92 + (SHA-256(正文) % 21) / 100        # 0.92–1.12，确定性抖动
TotalTime = clamp(round((base + overhead) * jitter), 8, 6000)   # 分钟
```

同一份正文重复运行结果一致；调 `--chars-per-min` / `--words-per-min` 可整体调快慢。

**时间线闭环**：`modified` 为锚点；`created = min(原 created, modified - TotalTime)`；`atime = modified`。新建文档或副本会被前移出生时间，使 `modified - created = TotalTime`；创建较早、间隔已超过 TotalTime 的老文档保持原创建时间（间隔 > TotalTime 属正常的多次编辑）。

**副本形态**（`--copy-style`，或系统无法回写 birthtime 时自动落到该形态）：core 仍保持 `created + TotalTime = modified`，但文件系统出生时间留在重写时刻，呈现真实副本的样子——Explorer 看到 `创建 > 修改`，Word 属性里仍是源文档的闭环历史。适合不支持 `SetFileTime` 的文件系统，或不愿改写真实创建时刻的场景。

## 用法

在 skill 目录下执行：

```bash
python scripts/docx-meta.py --inspect 文档.docx          # 只读检查当前元数据
python scripts/docx-meta.py 文档.docx                    # 默认清理
python scripts/docx-meta.py --backup --author "代欣江" 文档.docx
python scripts/docx-meta.py --edit-minutes 90 --chars-per-min 40 文档.docx
python scripts/docx-meta.py a.docx b.docx c.docx        # 批量
```

Windows 下也可用封装命令：`docx-meta 文档.docx`。

| 参数 | 作用 | 默认 |
|---|---|---|
| `--inspect` | 只打印元数据，不写文件 | — |
| `--author` | 保留/设置作者与最后修改者 | 删除 |
| `--company` | 公司属性 | 空 |
| `--title` | 文档标题 | 删除 |
| `--created` / `--modified` | ISO 时间覆盖（同时写入文件系统时间；默认模式间隔不足 TotalTime 时 created 自动前移；`--copy-style` 下保留显式值） | 文件真实时间 + 闭环校正 |
| `--edit-minutes` | 直接指定总编辑分钟 | 公式估算 |
| `--copy-style` | 副本形态：core 仍闭环，文件系统创建时间留在重写时刻（`创建 > 修改`） | 关闭 |
| `--chars-per-min` | 中文写入速度（字/分钟） | 45 |
| `--words-per-min` | 英文写入速度（词/分钟） | 32 |
| `--revision` | 修订号 | 1 |
| `--keep-thumbnail` | 保留缩略图 | 删除 |
| `--keep-custom-properties` | 保留自定义属性 | 删除 |
| `--keep-people` | 保留 people.xml | 删除 |
| `--keep-review-authors` | 保留批注/修订作者 | 置空 |
| `--dry-run` | 只计算不写盘 | — |
| `--backup` | 生成 `.bak` 备份 | — |

## 复核

```bash
python scripts/docx-meta.py --inspect 文档.docx
```

期望：`core.author`/`core.lastModifiedBy` 为空；`modified - created ≥ app.TotalTime`（新建/副本通常正好相等）；`created` 与 `core.created` 一致；`file times` 中 `accessed` 不早于 `modified`（刚写完时相等，之后可能被系统读取刷新）；`removable parts: <none>`；`review authors` 为空。Word 的 文件 → 信息 → 属性 → 高级属性 中可看到"总编辑时间"。

`--copy-style` 的期望不同：文件系统 `created > modified`（副本形态），但 core 仍是 `core.created + TotalTime = core.modified`；此时 FS 创建时间与 `core.created` 本来就不应相等。

已实测：Word 2021 打开含批注/修订的样本，批注保留、作者为空、总编辑时间与写入值一致；新建文档的时间线满足 `created + TotalTime = modified = accessed`。

## 回归测试

```bash
PYTHONUTF8=1 python -B scripts/test_docx_meta.py -v
```

用标准库构造最小 docx 样本，覆盖部件删除、关系与内容类型清理、批注作者置空、时间线闭环、估算路径与 `--author` 保留；只在临时目录操作。

## 注意

- 只支持 `.docx`；`.doc` 需先另存为 `.docx`。不处理 PDF/PPTX/XLSX。
- 处理前关闭 Word/WPS，否则 Windows 文件锁会导致替换失败。
- 不扫描正文中的姓名/邮箱、图片 EXIF、嵌入对象与 `customXml` 数据；这些属于内容级审查，需另行处理。
- 重写会破坏数字签名与加密；已签名文档不要使用。
- 清理后再用 Word 保存，Word 会按真实编辑会话重写作者与 `TotalTime`。若要保持干净，把本 skill 放在最后一步，或交付前再跑一次。
- `--backup` 生成的 `.bak` 保留原始敏感元数据，确认无误后删除。
- 修订/批注作者被置空但痕迹仍在；不想暴露批注或修订时，先在 Word 中接受修订并删除批注。
- Linux 上创建时间用 ctime 近似，可用 `--created` 覆盖。
- Windows 上副本天然 birth > mtime；默认会被拉成闭环（出生时间前移到 `modified - TotalTime`），这是刻意行为。若必须保留原始创建时间，先手工记录并接受时间线不闭环。
- `--copy-style` 下 Explorer 看到创建晚于修改，Word 属性里仍是从源文件继承的闭环创建/修改与总编辑时间，与真实复制一致；`SetFileTime` 失败时会自动落到这一形态。
- 访问时间在写入时置为 `modified`，但系统、杀毒软件或索引服务之后读取文件会刷新它；`创建 + 总编辑时长 = 修改` 这条不变量不受影响。
- 只改属性，不改正文、页数与排版。

## 与其他 skill 的关系

- `anthropic-docx`（及未来版本）只负责生成；生成后用本 skill 收尾，二者无代码依赖。
- `course-assignment` 已在第 6 步强制调用本 skill；其他交付链路也应在生成 docx 后追加本 skill，缺它时不要跳过元数据收尾。
- 本 skill 不生成内容，不替代任何文档生成 skill。
