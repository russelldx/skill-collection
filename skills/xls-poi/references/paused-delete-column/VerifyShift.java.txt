import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellStyle;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.DataValidation;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.ss.util.CellReference;

import java.io.FileInputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 删列结果逐格比对：new[i] 必须等于 old[i >= DEL ? i + 1 : i]
 * （值/公式 + 样式关键属性 + 行高 + 列宽 + 合并区 + DV + 被删列表头无残留）。支持 .xls 与 .xlsx。
 * 用法: VerifyShift <old> <new> <delCol0基> [表头行0基=3]
 */
public class VerifyShift {

    private static int DEL;
    private static int HDR = 3;

    private static final Pattern REF_PATTERN = Pattern.compile("(\\$?)([A-Z]{1,2})(\\$?)(\\d+)");

    public static void main(String[] args) throws Exception {
        DEL = Integer.parseInt(args[2]);
        if (args.length > 3) {
            HDR = Integer.parseInt(args[3]);
        }
        DataFormatter fmt = new DataFormatter();
        try (Workbook oldWb = open(args[0]); Workbook newWb = open(args[1])) {
            Sheet o = oldWb.getSheetAt(0);
            Sheet n = newWb.getSheetAt(0);
            System.out.println("sheetName old=" + o.getSheetName() + " new=" + n.getSheetName());
            System.out.println("lastRowNum old=" + o.getLastRowNum() + " new=" + n.getLastRowNum());
            System.out.println("dv old=" + describeDv(o) + " | new=" + describeDv(n));
            System.out.println("merged old=" + describeRegions(o) + " | new=" + describeRegions(n));

            int bad = 0;
            for (int ri = 0; ri <= o.getLastRowNum(); ri++) {
                Row orow = o.getRow(ri);
                Row nrow = n.getRow(ri);
                if (orow == null && nrow == null) {
                    continue;
                }
                if (orow == null || nrow == null) {
                    System.out.println("ROW MISSING " + ri);
                    bad++;
                    continue;
                }
                if (orow.getHeight() != nrow.getHeight()) {
                    System.out.println("rowHeight diff " + ri + " " + orow.getHeight() + " -> " + nrow.getHeight());
                    bad++;
                }
                int last = Math.max(orow.getLastCellNum(), nrow.getLastCellNum());
                for (int ni = 0; ni <= last; ni++) {
                    int oi = ni >= DEL ? ni + 1 : ni;
                    Cell oc = orow.getCell(oi);
                    Cell nc = nrow.getCell(ni);
                    if (oc != null && oc.getCellType() == CellType.FORMULA) {
                        String expect = shiftFormula(oc.getCellFormula());
                        String actual = (nc == null || nc.getCellType() != CellType.FORMULA)
                                ? "<" + (nc == null ? "missing" : nc.getCellType()) + ">" : nc.getCellFormula();
                        if (!expect.equals(actual)) {
                            System.out.println("FORMULA DIFF r" + ri + " new_c" + ni + " expect[" + expect + "] actual[" + actual + "]");
                            bad++;
                        }
                    } else {
                        String ov = oc == null ? "" : fmt.formatCellValue(oc);
                        String nv = nc == null ? "" : fmt.formatCellValue(nc);
                        if (!ov.equals(nv)) {
                            System.out.println("VALUE DIFF r" + ri + " new_c" + ni + "(old_c" + oi + ") ["
                                    + oneLine(ov) + "] -> [" + oneLine(nv) + "]");
                            bad++;
                        }
                    }
                    if (oc != null && nc != null && !styleEquals(oc.getCellStyle(), nc.getCellStyle())) {
                        System.out.println("STYLE DIFF r" + ri + " c" + ni + "(old_c" + oi + ")");
                        bad++;
                    }
                }
            }

            String gone = deletedHeader(o, fmt);
            int hits = 0;
            if (gone.isEmpty()) {
                System.out.println("-- 被删列表头为空，跳过残留扫描 --");
            } else {
                System.out.println("-- 被删列表头[" + gone + "] 残留（新文件全部 sheet 搜索）--");
                for (int si = 0; si < newWb.getNumberOfSheets(); si++) {
                    Sheet s = newWb.getSheetAt(si);
                    for (Row r : s) {
                        for (Cell c : r) {
                            String v = fmt.formatCellValue(c);
                            if (v != null && v.contains(gone)) {
                                System.out.println("sheet[" + s.getSheetName() + "] " + c.getAddress() + " = " + oneLine(v));
                                hits++;
                            }
                        }
                    }
                }
                System.out.println("残留hits=" + hits);
            }

            System.out.println("-- 新文件表头(索引" + HDR + ") --");
            Row nh = n.getRow(HDR);
            if (nh == null) {
                System.out.println("(表头行不存在)");
            }
            for (int ci = 0; nh != null && ci < nh.getLastCellNum(); ci++) {
                Cell c = nh.getCell(ci);
                System.out.println(ci + "|" + (c == null ? "" : oneLine(fmt.formatCellValue(c))));
            }

            System.out.println("-- 列宽比对 --");
            StringBuilder sb = new StringBuilder();
            for (int ci = 0; ci < usedCols(o, n); ci++) {
                int ow = o.getColumnWidth(ci >= DEL ? ci + 1 : ci);
                int nw = n.getColumnWidth(ci);
                sb.append(ci).append(":").append(nw).append(ow == nw ? "  " : "!!EXP" + ow + "  ");
            }
            System.out.println(sb);
            System.out.println("MISMATCHES=" + bad);
        }
    }

    /** 必须用流打开：create(File) 的 .xlsx 包是 READ_WRITE，close() 会回写并重序列化源文件 */
    private static Workbook open(String path) throws Exception {
        try (InputStream is = new FileInputStream(path)) {
            return WorkbookFactory.create(is);
        }
    }

    private static String shiftFormula(String formula) {
        Matcher m = REF_PATTERN.matcher(formula);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            int col = CellReference.convertColStringToIndex(m.group(2));
            String replaced = m.group(0);
            if (col > DEL) {
                replaced = m.group(1) + CellReference.convertNumToColString(col - 1) + m.group(3) + m.group(4);
            }
            m.appendReplacement(sb, Matcher.quoteReplacement(replaced));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    /** 被删列在原表头行的文本，新文件中不应再出现 */
    private static String deletedHeader(Sheet o, DataFormatter fmt) {
        Row hr = o.getRow(HDR);
        Cell c = hr == null ? null : hr.getCell(DEL);
        return c == null ? "" : oneLine(fmt.formatCellValue(c));
    }

    private static int usedCols(Sheet o, Sheet n) {
        int max = DEL + 2;
        for (Sheet s : new Sheet[]{o, n}) {
            for (Row r : s) {
                max = Math.max(max, r.getLastCellNum());
            }
        }
        return max + 1;
    }

    private static String describeDv(Sheet sheet) {
        List<String> cols = new ArrayList<>();
        for (DataValidation av : sheet.getDataValidations()) {
            for (CellRangeAddress ra : av.getRegions().getCellRangeAddresses()) {
                cols.add("c" + ra.getFirstColumn() + "-" + ra.getLastColumn() + "/r" + ra.getFirstRow() + "-" + ra.getLastRow());
            }
        }
        cols.sort(String::compareTo);
        return sheet.getDataValidations().size() + " " + cols;
    }

    private static String describeRegions(Sheet sheet) {
        Set<String> seen = new HashSet<>();
        for (CellRangeAddress ra : sheet.getMergedRegions()) {
            seen.add(ra.formatAsString());
        }
        List<String> list = new ArrayList<>(seen);
        list.sort(String::compareTo);
        return sheet.getNumMergedRegions() + (list.size() == sheet.getNumMergedRegions() ? "" : "(unique " + list.size() + ")")
                + " " + list;
    }

    private static boolean styleEquals(CellStyle a, CellStyle b) {
        return a.getDataFormat() == b.getDataFormat()
                && a.getFillForegroundColor() == b.getFillForegroundColor()
                && a.getFontIndex() == b.getFontIndex()
                && a.getAlignment() == b.getAlignment()
                && a.getWrapText() == b.getWrapText()
                && a.getBorderTop() == b.getBorderTop()
                && a.getBorderBottom() == b.getBorderBottom()
                && a.getBorderLeft() == b.getBorderLeft()
                && a.getBorderRight() == b.getBorderRight()
                && a.getVerticalAlignment() == b.getVerticalAlignment();
    }

    private static String oneLine(String v) {
        return v == null ? "" : v.replace("\n", "\\n");
    }
}
