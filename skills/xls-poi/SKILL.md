---
name: xls-poi
description: 处理 .xls/.xlsm（BIFF8）Excel 文件：结构分析、单元格读取修改、生成保留数据验证(DV)下拉的导入模板；删列工具（DeleteColumn/VerifyShift）经 WorkbookFactory 同时支持 .xlsx。触发场景：遇到 .xls 后缀文件（openpyxl 不支持）、需要保留下拉列表/数字/日期限制的模板生成、删列/增删字段后保持原表格式（合并区/列宽/下拉 DV/公式同步）、WPS 生成的 Excel 文件、EasyExcel/POI 相关表格处理、表头标注【见填写说明N】类模板优化。anthropic-xlsx 只覆盖 .xlsx 的通用读写，本 skill 专补 .xls 与"删列保结构"。
---

# XLS (BIFF8) 处理 — Java POI 方案

## 概述

.xls (BIFF8) 不能用 openpyxl 处理（仅支持 .xlsx）。本 skill 用 Java 8 + Apache POI 4.1.2（HSSFWorkbook）处理，已实测兼容 WPS 生成的文件：读改写后数据验证（DV）下拉、格式全部保留。

## 硬性原则

1. **必须用 Java POI（HSSFWorkbook 读→改→write）**。python xlwt/xlutils 方案会丢数据验证（DV 记录 0x00BE），已废弃。
2. 环境：Java 8 + POI 4.1.2（jar 路径固化在 `scripts/poi_env.sh`）。
3. 输出中文加 `-Dfile.encoding=UTF-8`，否则 GBK 乱码。
4. Git Bash 传 classpath 用正斜杠路径（`D:/...`）；勿用 `cygpath -w` 处理含分号的整串（会破坏路径）。

## 工作流

1. **分析**：`source scripts/poi_env.sh` 后 `poi_compile DumpStructure.java DumpAll.java RowInfo.java && poi_run DumpStructure <file.xls>`。
   - DumpStructure：sheet 清单/表头前 4 行/DV 区域/Name（_FilterDatabase、Print_Area）
   - DumpAll：全量单元格内容+字体+对齐+边框+填充+列宽（dump 后重定向到文件再 Read，避免刷屏）
   - RowInfo：行高/列宽
2. **读枚举**：WPS 下拉列表不在 DVRecord.formula1（POI 读为 null，POI 5.2.5 也无 List12Record 实现）——列表以 StringPtg 独立记录存于 DV 记录之间，**二进制 UTF-16LE 扫描 CJK 片段可读**；POI 读改写不丢列表（实测验证）。
3. **修改/生成**：HSSFWorkbook 读→改→写。生成模板用 MergeTemplate（见下）；整列删除用 DeleteColumn + VerifyShift（见下）。
4. **验证**：重新 dump 对比（表头文本/填写说明/DV 数量/筛选区域），再 `pandas` 或 xlrd 读一遍确认文件可打开、数据区为空。

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

## 整列删除（DeleteColumn + VerifyShift）

`.xls` 与 `.xlsx` 都可用（WorkbookFactory 按文件实际格式选 HSSF/XSSF）：

**何时必须用本工具（而非在 Excel/WPS 里手工删列）**：先看上面六类结构里有几项非空——无 DV、无引用名称、无公式（典型如纯表头+数据的 `.xlsx` 导出模板）时手工删列即可；有下拉 DV 或 `_FilterDatabase`/`Print_Titles` 或公式（典型如 `.xls` 导入模板）时手工删容易公式引用错位/报 `#REF!`、DV 区域不随列收缩，走工具。

```
poi_run DeleteColumn <src> <delCol0基> <dst> [sheetIdx=0]
poi_run VerifyShift  <src> <dst> <delCol0基> [headerRow0基=3]   # 期望 MISMATCHES=0
```

删一列不只是搬值，**六类结构必须同步左移**（DeleteColumn 已实现，改代码时勿漏）：

1. 单元格值+样式：从 `del+1` 起逐格搬到 `c-1`（起点写成 `del` 会把被删列自己的值搬进前一列）；末列 `removeCell`
2. 合并区域：`first==last==del` 的整列区直接丢弃；其余 `first>del → first-1`、`last>=del → last-1`（先 `removeMergedRegions` 再 `addMergedRegionUnsafe` 重建）
3. 列宽：按实际使用列数（`max(row.getLastCellNum())`）整段左移，别写死数组长度
4. 引用名称：`_FilterDatabase`/`Print_Titles` 末列收缩一位
5. **公式列字母**：`(\$?)([A-Z]{1,2})(\$?)(\d+)` 匹配后对 `col>del` 的列号减一重拼（漏了这步，右侧列的公式会集体错位一列；引用到被删列要单独告警）
6. **公式缓存值**：`setCellFormula` 会清缓存 → 写出前 `evaluateAll()` 回填，否则 EasyExcel/POI 按缓存值读到 0

VerifyShift 是验收关：逐格比对 `new[i] == old[i>=del ? i+1 : i]` 的值/**公式文本**/样式关键属性/行高/列宽，并输出 DV 区域、合并区清单、被删列文本残留搜索。公式格要比**公式文本**（比对器自己算期望值），不要比缓存值——缓存值会掩盖引用错位。实测：24→23 列样表 `MISMATCHES=0`，与逐个手工核对结果一致。

## 坑速查

- commons-collections4 必须 4.4（4.1 缺 TreeBidiMap，POI 写路径报 NoClassDefFoundError）。
- 删 sheet 后必须清理残留 Name（_FilterDatabase/Print_Area 指向已删 sheet）。
- _FilterDatabase 收缩写法：`'<sheet名>'!$A$3:$<末列>$22`（数据从第 4 行起）。
- DV 列提取：`sheet.getDataValidations()` + `getRegions().getCellRangeAddresses()` 取 firstColumn（注意有的文件表头行也有 DV 残留，去重即可）。
- 验证 DV 保留：POI 读回 dvCount 与生成前一致。
- pandas 验证：`pd.ExcelFile(file)` 能打开即文件未损坏。
- **公式格调 `setCellValue` 只更新缓存、类型仍是 FORMULA** → 用左移值覆盖原公式格时该格还是公式；写值前先 `dst.setBlank()`（保留样式）。
- **`WorkbookFactory.create(File)` 打开 .xlsx 是 READ_WRITE 包 → `close()` 会回写并重新序列化源文件**（实测：删列后连"输入副本"都被就地改掉，第二次比对拿已删列的文件当"原件"，结果全是假差异）。只读或写新文件一律 `WorkbookFactory.create(new FileInputStream(src))`。.xls 走 POIFS 无此问题，但同样用流打开保持一致。
- `getDataValidations()` 返回 `List<? extends DataValidation>`，**4.1.2 的 `DataValidation` 接口就有 `getRegions()`**（早期结论"必须下转 `HSSFDataValidation`"作废），因此删列/比对工具可直接泛化到 .xlsx。
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
- `scripts/MergeTemplate.java` — 通用模板生成器（保 DV、填写说明 sheet、表头标注/格式/自动列宽）
- `scripts/DeleteColumn.java` — 整列删除（值/样式/合并区/列宽/Name/公式列字母/公式缓存值同步左移）
- `scripts/VerifyShift.java` — 删列后逐格比对器（值+公式文本+样式+行高+列宽+DV+合并区+残留搜索，期望 `MISMATCHES=0`）
