#!/usr/bin/env node
// Markdown -> 中文课程作业 docx 生成器（通用版）
// 用法: node gen_docx.cjs <源.md> <输出.docx> [--img-width 480]
// 支持: #~#### 标题(首个 H1 居中作大标题) | 管道表格 | - 无序列表 | 1. 有序列表(按组重编号)
//       > 引用行(居中灰色,适合放元信息) | --- 分隔线(跳过) | **加粗** | ![图注](图片) 内嵌
// 图片相对路径按源 md 所在目录解析；支持 png/jpg/jpeg/bmp
'use strict';
const fs = require('fs');
const path = require('path');

const argv = process.argv.slice(2);
const pos = argv.filter(a => !a.startsWith('--'));
if (pos.length < 2) {
  console.error('用法: node gen_docx.cjs <源.md> <输出.docx> [--img-width 480]');
  process.exit(1);
}
const SRC = path.resolve(pos[0]);
const OUT = path.resolve(pos[1]);
const BASE = path.dirname(SRC);
function optVal(flag, dflt) {
  const ix = argv.indexOf(flag);
  return ix >= 0 && argv[ix + 1] ? parseInt(argv[ix + 1], 10) : dflt;
}
const IMG_WIDTH_PX = optVal('--img-width', 480);

function loadDocx() {
  try { return require('docx'); } catch (e) { /* fallthrough */ }
  try {
    const globalRoot = require('child_process').execSync('npm root -g', { encoding: 'utf8' }).trim();
    return require(path.join(globalRoot, 'docx'));
  } catch (e2) {
    console.error('找不到 docx 模块：请先 npm install -g docx，或设置 NODE_PATH 指向全局 node_modules');
    process.exit(1);
  }
}
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType,
} = loadDocx();

const CONTENT_WIDTH = 9026; // A4 + 1 英寸页边距的正文宽（DXA）
const border = { style: BorderStyle.SINGLE, size: 1, color: '999999' };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function imgSize(buf, ext) {
  if (ext === 'png') return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  if (ext === 'jpg' || ext === 'jpeg') {
    let p = 2;
    while (p < buf.length - 9) {
      if (buf[p] !== 0xFF) { p++; continue; }
      const marker = buf[p + 1];
      if (marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC) {
        return { h: buf.readUInt16BE(p + 5), w: buf.readUInt16BE(p + 7) };
      }
      p += 2 + buf.readUInt16BE(p + 2);
    }
    throw new Error('无法解析 JPEG 尺寸: ' + ext);
  }
  if (ext === 'bmp') return { w: buf.readInt32LE(18), h: Math.abs(buf.readInt32LE(22)) };
  throw new Error('不支持的图片格式: ' + ext + '（仅 png/jpg/jpeg/bmp）');
}

function inlineRuns(text, extra) {
  const runs = [];
  for (const p of text.split(/(\*\*[^*]+\*\*)/g)) {
    if (!p) continue;
    if (p.startsWith('**') && p.endsWith('**')) {
      runs.push(new TextRun(Object.assign({ text: p.slice(2, -2), bold: true }, extra || {})));
    } else {
      runs.push(new TextRun(Object.assign({ text: p }, extra || {})));
    }
  }
  return runs;
}

function makeTable(rows) {
  const ncols = rows[0].length;
  const base = Math.floor(CONTENT_WIDTH / ncols);
  const widths = [];
  for (let c = 0; c < ncols; c++) widths.push(base);
  widths[0] += CONTENT_WIDTH - base * ncols;
  const trs = rows.map((cells, ri) => new TableRow({
    tableHeader: ri === 0,
    children: cells.map((cellText, ci) => new TableCell({
      borders,
      width: { size: widths[ci], type: WidthType.DXA },
      margins: cellMargins,
      shading: ri === 0 ? { fill: 'D9E2F3', type: ShadingType.CLEAR } : undefined,
      children: [new Paragraph({
        children: inlineRuns(cellText, ri === 0 ? { bold: true } : undefined),
      })],
    })),
  }));
  return new Table({ width: { size: CONTENT_WIDTH, type: WidthType.DXA }, columnWidths: widths, rows: trs });
}

const lines = fs.readFileSync(SRC, 'utf8').split(/\r?\n/);
const children = [];
let i = 0;
let firstHeading = true;
let numGroup = -1;
let inNumList = false;

while (i < lines.length) {
  const line = lines[i].trim();
  if (!line) { i++; continue; }
  if (/^-{3,}$/.test(line)) { inNumList = false; i++; continue; }

  const img = line.match(/^!\[(.*)\]\((.+)\)$/);
  if (img) {
    inNumList = false;
    const caption = img[1].trim().replace(/\s+/g, ' ');
    const rel = img[2].trim();
    const abs = path.join(BASE, rel);
    const data = fs.readFileSync(abs);
    const ext = path.extname(abs).slice(1).toLowerCase();
    const dim = imgSize(data, ext);
    const height = Math.round(IMG_WIDTH_PX * dim.h / dim.w);
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      keepNext: true,
      spacing: { before: 120, after: 60 },
      children: [new ImageRun({
        type: ext === 'jpeg' ? 'jpg' : ext,
        data,
        transformation: { width: IMG_WIDTH_PX, height },
        altText: { title: caption, description: caption, name: path.basename(abs, '.' + ext) },
      })],
    }));
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: caption, size: 18, color: '555555' })],
    }));
    i++;
    continue;
  }

  if (line.startsWith('|')) {
    inNumList = false;
    const rows = [];
    while (i < lines.length && lines[i].trim().startsWith('|')) {
      const t = lines[i].trim();
      if (!/^\|[\s:|-]+\|$/.test(t)) {
        rows.push(t.slice(1, -1).split('|').map(s => s.trim()));
      }
      i++;
    }
    if (rows.length) {
      children.push(makeTable(rows));
      children.push(new Paragraph({ children: [] }));
    }
    continue;
  }

  const h = line.match(/^(#{1,6})\s+(.*)$/);
  if (h) {
    inNumList = false;
    const level = Math.min(h[1].length, 4);
    if (level === 1 && firstHeading) {
      children.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 },
        children: [new TextRun({ text: h[2], bold: true, size: 36, font: { ascii: 'Arial', eastAsia: 'SimHei' } })],
      }));
      firstHeading = false;
    } else {
      const hl = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3, HeadingLevel.HEADING_4][level - 1];
      children.push(new Paragraph({ heading: hl, children: inlineRuns(h[2]) }));
    }
    i++;
    continue;
  }

  if (line.startsWith('>')) {
    inNumList = false;
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: inlineRuns(line.replace(/^>\s*/, ''), { size: 21, color: '555555' }),
    }));
    i++;
    continue;
  }

  if (/^-\s+/.test(line)) {
    inNumList = false;
    children.push(new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: inlineRuns(line.slice(2).trim()) }));
    i++;
    continue;
  }

  const num = line.match(/^(\d+)[.、)]\s+(.*)$/);
  if (num) {
    if (!inNumList) { numGroup++; inNumList = true; }
    children.push(new Paragraph({ numbering: { reference: 'nums' + numGroup, level: 0 }, children: inlineRuns(num[2]) }));
    i++;
    continue;
  }

  inNumList = false;
  children.push(new Paragraph({ spacing: { after: 120 }, children: inlineRuns(line) }));
  i++;
}

const numberingConfig = [{
  reference: 'bullets',
  levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 480, hanging: 240 } } } }],
}];
for (let g = 0; g <= numGroup; g++) {
  numberingConfig.push({
    reference: 'nums' + g,
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 480, hanging: 240 } } } }],
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: { ascii: 'Times New Roman', eastAsia: 'SimSun' }, size: 21 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, font: { ascii: 'Arial', eastAsia: 'SimHei' } },
        paragraph: { spacing: { before: 240, after: 180 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: { ascii: 'Arial', eastAsia: 'SimHei' } },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 23, bold: true, font: { ascii: 'Arial', eastAsia: 'SimHei' } },
        paragraph: { spacing: { before: 160, after: 100 }, outlineLevel: 2 } },
      { id: 'Heading4', name: 'Heading 4', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 21, bold: true, font: { ascii: 'Arial', eastAsia: 'SimHei' } },
        paragraph: { spacing: { before: 120, after: 80 }, outlineLevel: 3 } },
    ],
  },
  numbering: { config: numberingConfig },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log('OK written', OUT, buf.length, 'bytes,', children.length, 'body elements');
}).catch(err => {
  console.error('FAIL', err.message);
  process.exit(1);
});
