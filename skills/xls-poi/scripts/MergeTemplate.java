import org.apache.poi.hssf.usermodel.HSSFFont;
import org.apache.poi.hssf.usermodel.HSSFRichTextString;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 通用 .xls 模板生成器（POI 保留数据验证/格式）。
 * 用法: java MergeTemplate <src.xls> <sheetIdx> <dst.xls> <enumsFile> <filterLastCol> [headerRow=2]
 * 操作:
 *  1. 清空表头行以下示例数据（保留格式）
 *  2. 收缩筛选区域(_FilterDatabase)到实际表头列
 *  3. 追加"填写说明"sheet：编号|字段名|枚举值（"是,否"条目不进填写说明，直接标注在表头字段后）
 *  4. 表头优化：枚举字段追加【见填写说明N】；是/否字段追加【填写是或否】（标注文字红色，单元格原样式/宽高不变）
 *  5. 填写说明 sheet 列宽/行高按内容自动
 * enumsFile 每行: 编号\t字段名\t枚举值(逗号分隔)
 */
public class MergeTemplate {

    public static void main(String[] args) throws Exception {
        String src = args[0];
        int sheetIdx = Integer.parseInt(args[1]);
        String dst = args[2];
        String enumsFile = args[3];
        int filterLastCol = Integer.parseInt(args[4]);
        int headerRow = args.length > 5 ? Integer.parseInt(args[5]) : 2;
        List<String[]> enums = readEnums(enumsFile);
        try (HSSFWorkbook wb = new HSSFWorkbook(new FileInputStream(src))) {
            Sheet sheet = wb.getSheetAt(sheetIdx);
            for (int r = 3; r <= sheet.getLastRowNum(); r++) {
                Row row = sheet.getRow(r);
                if (row == null) {
                    continue;
                }
                for (int c = 0; c < row.getLastCellNum(); c++) {
                    Cell cell = row.getCell(c);
                    if (cell != null) {
                        cell.setBlank();
                    }
                }
            }
            shrinkFilter(wb, sheet.getSheetName(), filterLastCol);
            removeOtherSheets(wb, sheetIdx);
            List<String[]> kept = buildFillSheet(wb, enums);
            Set<Integer> dvCols = dvColumns(sheet);
            optimizeHeader(wb, sheet, kept, dvCols, headerRow);
            try (FileOutputStream out = new FileOutputStream(dst)) {
                wb.write(out);
            }
            System.out.println("saved: " + dst);
        }
    }

    /**
     * 生成"填写说明"sheet；"是,否"枚举条目不进填写说明（重编号），返回保留条目（含新编号 1..N）。
     * 列宽/行高按内容自动：B 列按字段名、C 列按枚举值，行高按折行数估算
     */
    private static List<String[]> buildFillSheet(HSSFWorkbook wb, List<String[]> enums) {
        List<String[]> kept = new ArrayList<>();
        for (String[] e : enums) {
            if (!"是,否".equals(e[2])) {
                kept.add(e);
            }
        }
        Sheet fs = wb.createSheet("填写说明");
        CellStyle numStyle = createNumStyle(wb);
        CellStyle fieldStyle = createFieldStyle(wb);
        CellStyle bodyStyle = createBodyStyle(wb);
        int bWidth = 19;
        int cWidth = 46;
        for (String[] e : kept) {
            bWidth = Math.max(bWidth, Math.min(60, textWidth(e[1]) + 2));
            cWidth = Math.max(cWidth, Math.min(60, textWidth(e[2]) + 2));
        }
        int lines2 = 1;
        int lines3 = 1;
        for (String[] e : kept) {
            lines2 = Math.max(lines2, (textWidth(e[1]) + bWidth - 1) / bWidth);
            lines3 = Math.max(lines3, (textWidth(e[2]) + cWidth - 1) / cWidth);
        }
        fs.setColumnWidth(0, 5000);
        for (int c = 1; c < kept.size(); c++) {
            fs.setColumnWidth(c, (c == 1 ? bWidth : cWidth) * 256);
        }
        fs.createRow(0).setHeight((short) 400);
        fs.createRow(1).setHeight((short) Math.min(2000, lines2 * 20 * 20 + 300));
        fs.createRow(2).setHeight((short) Math.min(3200, lines3 * 20 * 20 + 300));
        for (int c = 0; c < kept.size(); c++) {
            setCell(fs, 0, c, "填写说明" + (c + 1), numStyle);
            setCell(fs, 1, c, kept.get(c)[1], fieldStyle);
            setCell(fs, 2, c, kept.get(c)[2], bodyStyle);
        }
        return kept;
    }

    /**
     * 表头优化：枚举列追加红色【见填写说明N】；是/否列（有 DV）追加红色【填写是或否】。
     * 单元格样式/列宽/行高保持原文件不变（以处室确认版为准）
     */
    private static void optimizeHeader(HSSFWorkbook wb, Sheet sheet, List<String[]> kept,
                                       Set<Integer> dvCols, int headerRow) {
        Row header = sheet.getRow(headerRow);
        if (header == null) {
            return;
        }
        HSSFFont redFont = null;
        for (int c = 0; c < header.getLastCellNum(); c++) {
            Cell cell = header.getCell(c);
            if (cell == null || cell.getCellType() != CellType.STRING) {
                continue;
            }
            String text = cell.getStringCellValue();
            if (text.isEmpty()) {
                continue;
            }
            String suffix = null;
            for (int i = 0; i < kept.size(); i++) {
                String main = mainName(kept.get(i)[1]);
                if (text.equals(main) || text.startsWith(main + "（")) {
                    suffix = "【见填写说明" + (i + 1) + "】";
                    break;
                }
            }
            if (suffix == null && text.startsWith("是否") && dvCols.contains(c)) {
                suffix = "【填写是或否】";
            }
            if (suffix != null && !text.contains("【")) {
                if (redFont == null) {
                    redFont = redFontOf(wb, wb.getFontAt(cell.getCellStyle().getFontIndex()));
                }
                HSSFRichTextString rt = new HSSFRichTextString(text + suffix);
                rt.applyFont(0, text.length(), wb.getFontAt(cell.getCellStyle().getFontIndex()));
                rt.applyFont(text.length(), text.length() + suffix.length(), redFont);
                cell.setCellValue(rt);
            }
        }
    }

    /**
     * 复制原字体属性、仅将颜色改为红色（用于表头标注文字）
     */
    private static HSSFFont redFontOf(HSSFWorkbook wb, Font orig) {
        HSSFFont f = wb.createFont();
        f.setFontName(orig.getFontName());
        f.setFontHeightInPoints(orig.getFontHeightInPoints());
        f.setBold(orig.getBold());
        f.setItalic(orig.getItalic());
        f.setColor(IndexedColors.RED.getIndex());
        return f;
    }

    /**
     * 估算文本显示宽度：中文/全角 2 单位，ASCII 1 单位
     */
    private static int textWidth(String s) {
        int w = 0;
        for (int i = 0; i < s.length(); i++) {
            w += s.charAt(i) >= '\u2E80' ? 2 : 1;
        }
        return w;
    }

    /**
     * 字段名主干：取"（"前部分，用于与表头匹配（如"重点监测机构（多个以英文逗号","分割）"→"重点监测机构"）
     */
    private static String mainName(String field) {
        int idx = field.indexOf('（');
        return idx > 0 ? field.substring(0, idx) : field;
    }

    /**
     * 提取有数据验证(DV)的列号
     */
    private static Set<Integer> dvColumns(Sheet sheet) {
        Set<Integer> cols = new HashSet<>();
        for (DataValidation dv : sheet.getDataValidations()) {
            for (CellRangeAddress ra : dv.getRegions().getCellRangeAddresses()) {
                cols.add(ra.getFirstColumn());
            }
        }
        return cols;
    }

    /**
     * 删除非目标 sheet 及其残留 Name（模板只保留一个数据表 + 填写说明）
     */
    private static void removeOtherSheets(HSSFWorkbook wb, int keepIdx) {
        for (int i = wb.getNumberOfSheets() - 1; i >= 0; i--) {
            if (i != keepIdx) {
                wb.removeSheetAt(i);
            }
        }
        for (int i = wb.getNumberOfNames() - 1; i >= 0; i--) {
            Name name = wb.getNameAt(i);
            if (!"_FilterDatabase".equals(name.getNameName())) {
                try {
                    wb.removeName(name);
                } catch (Exception ignored) {
                }
            }
        }
    }

    /**
     * 多余列不配置筛选框：_FilterDatabase 收缩到实际表头列（行 3-22 保留），非目标 sheet 的删除
     */
    private static void shrinkFilter(HSSFWorkbook wb, String sheetName, int lastCol) {
        for (int i = wb.getNumberOfNames() - 1; i >= 0; i--) {
            Name name = wb.getNameAt(i);
            if (!"_FilterDatabase".equals(name.getNameName())) {
                continue;
            }
            String ref = name.getRefersToFormula();
            if (ref != null && ref.contains(sheetName)) {
                name.setRefersToFormula("'" + sheetName + "'!$A$3:$" + colName(lastCol) + "$22");
            } else {
                wb.removeName(name);
            }
        }
    }

    private static String colName(int col) {
        StringBuilder sb = new StringBuilder();
        int c = col;
        while (c >= 0) {
            sb.insert(0, (char) ('A' + (c % 26)));
            c = c / 26 - 1;
        }
        return sb.toString();
    }

    private static void setCell(Sheet sheet, int r, int c, String value, CellStyle style) {
        Row row = sheet.getRow(r);
        Cell cell = row.createCell(c);
        cell.setCellValue(value);
        cell.setCellStyle(style);
    }

    /**
     * 填写说明编号行样式（参考旧版）：宋体 11 加粗 红字 黄底 细边框 居中
     */
    private static CellStyle createNumStyle(HSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        HSSFFont font = wb.createFont();
        font.setFontName("宋体");
        font.setFontHeightInPoints((short) 11);
        font.setBold(true);
        font.setColor(IndexedColors.RED.getIndex());
        style.setFont(font);
        style.setWrapText(true);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setAlignment(HorizontalAlignment.CENTER);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderBottom(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        style.setFillForegroundColor((short) 26); // 浅黄，与旧版一致
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        return style;
    }

    /**
     * 填写说明字段名行样式（参考旧版）：宋体 12 加粗 黑字 灰底 细边框 居中
     */
    private static CellStyle createFieldStyle(HSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        HSSFFont font = wb.createFont();
        font.setFontName("宋体");
        font.setFontHeightInPoints((short) 12);
        font.setBold(true);
        style.setFont(font);
        style.setWrapText(true);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setAlignment(HorizontalAlignment.CENTER);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderBottom(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        style.setFillForegroundColor((short) 64); // 灰，与旧版一致
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        return style;
    }

    /**
     * 填写说明枚举值行样式（参考旧版）：宋体 12 黑字 灰底 无边框 左对齐
     */
    private static CellStyle createBodyStyle(HSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        HSSFFont font = wb.createFont();
        font.setFontName("宋体");
        font.setFontHeightInPoints((short) 12);
        style.setFont(font);
        style.setWrapText(true);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setAlignment(HorizontalAlignment.LEFT);
        style.setFillForegroundColor((short) 64);
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        return style;
    }

    private static List<String[]> readEnums(String path) throws Exception {
        List<String[]> list = new ArrayList<>();
        try (java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(new FileInputStream(path), "UTF-8"))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] parts = line.split("\t", -1);
                if (parts.length >= 3) {
                    list.add(new String[]{parts[0], parts[1], parts[2]});
                }
            }
        }
        return list;
    }
}
