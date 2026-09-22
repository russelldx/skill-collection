---
name: xls-poi
description: 处理 .xls（BIFF8）Excel 文件：结构分析、单元格读取修改、带数据验证(DV)下拉的导入模板生成与逐项核验。触发场景：.xls 文件、WPS 生成的 BIFF8 文件、EasyExcel/POI 表格处理、表头标注【见填写说明N】类模板优化。整列删除及 DeleteColumn/VerifyShift 验收链已暂停，不提供删列保结构保证；.xlsm 不是 BIFF8，不走 HSSFWorkbook 模板工具。
---

# XLS (BIFF8) 处理 — Java POI 方案

## 概述

.xls (BIFF8) 不能用 openpyxl 处理（仅支持 .xlsx）。本 skill 用 Java 8 + Apache POI 4.1.2（HSSFWorkbook）处理，已实测兼容 WPS 生成的文件：读改写后数据验证（DV）下拉、格式全部保留。

## 硬性原则

1. **必须用 Java POI（HSSFWorkbook 读→改→write）**。python xlwt/xlutils 方案会丢数据验证（DV 记录 0x00BE），已废弃。
2. 环境：Java 8 + POI 4.1.2。显式设置 `POI_CLASSPATH` 为本机已有依赖 jar 的完整 classpath，或含这些 jar 的绝对目录通配符（`/absolute/path/lib/*`）；不下载、不安装、不修改现有依赖。缺失时脚本报错并停止。
3. 输出中文加 `-Dfile.encoding=UTF-8`，否则 GBK 乱码。
4. classpath 分隔符：Windows Java 用 `;`，Linux/macOS 用 `:`。Git Bash 中 Windows 路径用正斜杠；整个 classpath 加引号，勿对含分号的整串运行 `cygpath -w`。
5. 依赖基线：poi/poi-ooxml/poi-ooxml-schemas 4.1.2、xmlbeans 3.1.0、commons-compress 1.19、curvesapi 1.04、commons-math3 3.6.1、commons-codec 1.13、commons-collections4 4.4、commons-logging 1.2。由用户提供已有依赖路径；编译/运行失败不能跳过或声称验证通过。

## 工作流

1. **分析**：在独立临时工作目录中 `source "<本 skill 绝对路径>/scripts/poi_env.sh"`，设置 `POI_CLASSPATH` 后运行 `poi_compile DumpStructure.java DumpAll.java RowInfo.java && poi_run DumpStructure <file.xls>`。源码按脚本所在目录定位，class 只输出到当前临时目录；不要复用旧 class。
   - DumpStructure：sheet 清单/表头前 4 行/DV 区域/Name（_FilterDatabase、Print_Area）
   - DumpAll：全量单元格内容+字体+对齐+边框+填充+列宽（dump 后重定向到文件再 Read，避免刷屏）
   - RowInfo：行高/列宽
2. **读枚举**：WPS 下拉列表不在 DVRecord.formula1（POI 读为 null，POI 5.2.5 也无 List12Record 实现）——列表以 StringPtg 独立记录存于 DV 记录之间，**二进制 UTF-16LE 扫描 CJK 片段可读**；POI 读改写不丢列表（实测验证）。
3. **修改/生成**：HSSFWorkbook 读→改→写。生成模板用 MergeTemplate（先 `poi_compile MergeTemplate.java`）；整列删除暂停，不运行旧删列或删列验收链。
4. **验证**：重新 dump 对比（表头文本/填写说明/DV 数量、区域及约束内容/筛选区域），再 `pandas` 或 xlrd 读一遍确认文件可打开、数据区为空。可打开和 DV 数量相同都不等于结构完整保留。

## 模板生成（MergeTemplate）

```
poi_run MergeTemplate <src.xls> <sheetIdx> <dst.xls> <enumsFile> <filterLastCol> [headerRow=2]
```

- 操作：清空表头行以下示例数据（保留格式）→ 收缩 _FilterDatabase 到实际表头列 → 删多余 sheet → 追加"填写说明"sheet（编号|字段名|枚举值）→ 表头优化。
- enumsFile 每行：`编号<TAB>字段名<TAB>枚举值(逗号分隔)`。枚举值恰为"是,否"的条目不进填写说明（自动重编号），改为在表头对应字段后追加【填写是或否】。
- 表头优化（v4，以处室确认版原样式为基准）：
  - 枚举字段（按字段名主干匹配，且该列有 DV）追加【见填写说明N】；是/否字段（表头以"是否"开头且该列有 DV）追加【填写是或否】
  - 标注文字用 RichTextString 染红（复制原字体属性仅改色）；**单元格样式/列宽/行高保持原文件不变**
  - 填写说明 sheet：B 列按字段名、C 列按枚举值自动列宽（上限 60），行高按折行数估算；样式参考旧版——编号行（第1行）宋体 11 加粗**红字黄底**、字段名行（第2行）宋体 12 加粗**黑字灰底**细边框、枚举值行（第3行）宋体 12 黑字灰底无边框左对齐
- 匹配注意：字段名主干取"（"前（如"重点监测机构（多个…）"→"重点监测机构"），用 `equals` 或 `startsWith(主干+"（")` 匹配，避免"所属产业"误匹配"所属产业链"。
- 常见布局：A1=附件名、A2=标题、A3=表头（headerRow=2 默认）；EasyExcel 读取配 `headRowNumber=3`。
- 拆分文件常见 253 列（保留原表 COLINFO），表头只填前 N 列属正常，勿"修复"。
- 原文件表头多为 RichTextString：如"计划总投资(万元)【必须为数字】"的标注本身已是红色内嵌字体，用 `getRichStringCellValue()` 验证。

## 整列删除：PAUSED（不执行）

DeleteColumn 不迁移数据验证（DV），VerifyShift 只打印 DV、合并区域和列宽，未把这些差异计入 `MISMATCHES`。历史 `MISMATCHES=0` **不能证明保留完整，也不是删列验收通过**。

- 暂停整个删列执行/验收链；不要编译参考源码、复制改名运行、复用旧 class 或换工具绕过暂停。
- `scripts/DeleteColumn.java` 和 `scripts/VerifyShift.java` 仅保留 fail-closed 入口：任何参数均在打开/写入工作簿前以退出码 2 停止。`poi_compile`/`poi_run` 同样拒绝这两个入口。
- 原实现及其删列专用私有 helpers 完整保存在 `references/paused-delete-column/*.java.txt`，只供阅读；其中旧注释/用法/保留能力宣称不是当前操作指令。
- 需要删列时先报告暂停原因、保留原件，等待另行审查并验证 DV 区域/约束、合并区、列宽、名称与公式等结构迁移后再考虑恢复。本次没有实现或验证完整修复。
- DumpStructure、DumpAll、RowInfo、CheckRich 和 MergeTemplate 保留；它们不构成删列修复或删列验收。

## 坑速查

- commons-collections4 必须 4.4（4.1 缺 TreeBidiMap，POI 写路径报 NoClassDefFoundError）。
- 删 sheet 后必须清理残留 Name（_FilterDatabase/Print_Area 指向已删 sheet）。
- _FilterDatabase 收缩写法：`'<sheet名>'!$A$3:$<末列>$22`（数据从第 4 行起）。
- DV 列提取：`sheet.getDataValidations()` + `getRegions().getCellRangeAddresses()` 取 firstColumn（注意有的文件表头行也有 DV 残留，去重即可）。
- 验证 DV 保留：除 POI 读回 dvCount 外，还需核对区域、约束及下拉内容；数量一致不足以证明保留。
- pandas 验证：`pd.ExcelFile(file)` 能打开即文件未损坏。
- **公式格调 `setCellValue` 只更新缓存、类型仍是 FORMULA** → 用左移值覆盖原公式格时该格还是公式；写值前先 `dst.setBlank()`（保留样式）。
- **`WorkbookFactory.create(File)` 打开 .xlsx 是 READ_WRITE 包 → `close()` 会回写并重新序列化源文件**（实测：删列后连"输入副本"都被就地改掉，第二次比对拿已删列的文件当"原件"，结果全是假差异）。只读或写新文件一律 `WorkbookFactory.create(new FileInputStream(src))`。.xls 走 POIFS 无此问题，但同样用流打开保持一致。
- `getDataValidations()` 返回 `List<? extends DataValidation>`，**4.1.2 的 `DataValidation` 接口就有 `getRegions()`**；这只支持读取区域，不代表暂停的删列/比对工具能够安全处理 .xlsx。
- `FormulaEvaluator.evaluateAll()` 在 4.1.2 **返回 void**，别链 `.size()`；Sheet 接口没有 `getSheetVersion()`，取版本用 `Workbook.getSpreadsheetVersion()`（HSSF=EXCEL97 / XSSF=EXCEL2007）。
- 拼绝对引用别用 POI：`CellReference.quoteSheetName` 在 4.1.2 不存在，`AreaReference.formatAsString()` 输出**相对**引用（丢 `$`），把 `new CellReference(r,c,true,true)` 直接拼进字符串会报 `FormulaParseException: Specified name 'org.apache.poi.ss.util.CellReference' for sheet`。手拼 `"$" + convertNumToColString(col) + "$" + (row+1)`，sheet 名用 `'…'`（内部 `'` 双写）。
- `javac` 漏 `-encoding UTF-8` → 中文源码报"错误: 编码GBK的不可映射字符"**编译失败**，而旧 `.class` 还在，下一次 `poi_run` 跑的是旧逻辑（会把旧结果当成新验证通过）。**编译必须看 exit code**；输出重定向到文件后用 `iconv -f GBK -t UTF-8` 再看（否则 GBK 字节会让 grep 判定为 Binary file）。
- 改列/改表类操作先备份原件到 `.backup/`，且**比对基准固定用原件**——原地覆盖后第二次运行就会拿"结果"当"输入"。

## Resources

- `scripts/poi_env.sh` — 环境脚本（source 后可用 poi_compile / poi_run）
- `scripts/DumpStructure.java` — sheet/表头/DV/Name dump
- `scripts/DumpAll.java` — 全量单元格内容+样式+列宽
- `scripts/RowInfo.java` — 行高/列宽
- `scripts/CheckRich.java` — 检查表头 RichTextString 内嵌字体（验证标注染红/原文件红色标注）
- `scripts/MergeTemplate.java` — 通用模板生成器（填写说明 sheet、表头标注/格式/自动列宽；输出需逐项核验 DV）
- `scripts/DeleteColumn.java` / `scripts/VerifyShift.java` — 暂停提示入口，不处理工作簿
- `references/paused-delete-column/` — 历史删列与比对源码（`.java.txt`，非执行参考）
