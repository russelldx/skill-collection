# 交付件三重校验手册

目的：在没有 Word 渲染工具链的机器上，仍然对交付 docx 给出**可复核、不夸大**的质量证据。

## 第 1 层 格式合法性

```bash
PYTHONUTF8=1 python ~/.qoder/skills/anthropic-docx/scripts/office/validate.py <输出.docx>
```

- Windows 中文环境必须带 `PYTHONUTF8=1`（否则 GBK 解码 UTF-8 XML 报错）
- 关注输出里的段落数：与内容源规模对一下数量级，防止解析器吃掉了大段内容

## 第 2 层 结构检查（无需渲染）

代码模板（按需改路径与期望值）：

```bash
PYTHONUTF8=1 python -c "
import zipfile,re,hashlib,os
docx=r'<输出.docx>'; base=r'<工作目录>'; imgs=['<内嵌图相对路径1>','<相对路径2>']
z=zipfile.ZipFile(docx); d=z.read('word/document.xml').decode('utf8')
print('drawings:',d.count('<w:drawing>'),'期望',len(imgs))
print('extents:',set(re.findall(r'cx=\"(\d+)\" cy=\"(\d+)\"',d)))  # cx 应 <= 5731686 EMU（正文宽 6.27in）
def sha(p): return hashlib.sha1(open(p,'rb').read()).hexdigest()
media={os.path.basename(n):n for n in z.namelist() if n.startswith('word/media/')}
for p in imgs:
    h=sha(os.path.join(base,p)); print(p,'->',('OK' if h in media else 'MISSING'))
"
```

必查清单：

- [ ] `<w:drawing>` 数 = 内容源里 `![` 图行数；`wp:extent` 的 cx ≤ 5731686 EMU（9026 DXA 正文宽），否则图片会出血
- [ ] `word/media/` 中每个文件的 SHA1 与源图一致（证明嵌入的就是那张证据图，没被换/截断）
- [ ] 图注文本齐全（grep `图 [0-9]`），且正文引用（"见图 2"）与实际图号一一对应
- [ ] **数字一致性 grep**：题量/通过数/失败数/缺陷数/执行率/日期范围在全篇出现处全部对得上（这是最高频翻车点）
- [ ] **可追溯性**：每张截图里出现的账号、文件名、时间戳，在正文"环境/材料"章节找得到
- [ ] 占位符：`{学号}` `{姓名}` 出现次数 = 预期（正文各处 + 无遗漏）；提交替换后应为 0
- [ ] 无外部文件残留：正文不应再出现 `evidence_*.png` 这类裸文件名（内嵌后应写"见图 N"）

## 第 3 层 独立双校（Workflow / 子 agent）

- **合规审计 agent**：给它作业题面原文 + 内容源，要求逐条核对硬性要求（章节结构、数量下限、命名规则）并输出差异清单
- **视觉校验 agent**：仅当存在渲染链路（LibreOffice/pandoc 可用）时执行；没有就跳过并在报告口径里明说
- 子 agent prompt 必须包含两条红线：
  1. 禁止打开/修改/上传/提交学习通等任何作业平台的任何页面
  2. 禁止编辑交接文档与作业执行文档（只有主会话可写）
- 主会话对子 agent 结论**抽查复核**（它声称改了什么，就 grep 什么），不直接转述为"已验证"

## 诚实口径（写进最终汇报）

- 明确三件事：做了哪层校验、跳过了哪层、为什么跳过
- 未渲染就不能说"排版没问题"；只能说"结构检查与内容核对通过，渲染效果由用户在 Word/WPS 中目检"

## 提交前最后核对

1. 用户给出学号/姓名 → 替换内容源全部占位符 + 重命名文件 → 重生成 → 重跑第 1、2 层
2. 交付物数量与题面要求一致（一个文档就别附 zip）
3. 截止时间还剩多少：不足 1 小时优先提交，校验瑕疵留备注，不要为完美卡点
