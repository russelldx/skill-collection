import org.apache.poi.ss.SpreadsheetVersion;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.Name;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.apache.poi.ss.util.AreaReference;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.ss.util.CellReference;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 整列删除（列号 0 基），右侧列左移一格：
 * 单元格值/样式、合并区域、列宽、引用名称（_FilterDatabase 等）、公式列号同步收缩。
 * 支持 .xls（BIFF8/HSSF）与 .xlsx（XSSF），由 WorkbookFactory 按文件实际格式选择。
 */
public class DeleteColumn {

    private static final Pattern REF_PATTERN = Pattern.compile("(\\$?)([A-Z]{1,2})(\\$?)(\\d+)");

    public static void main(String[] args) throws Exception {
        String src = args[0];
        int del = Integer.parseInt(args[1]);
        String dst = args[2];
        int sheetIdx = args.length > 3 ? Integer.parseInt(args[3]) : 0;
        // 必须用流打开：WorkbookFactory.create(File) 对 .xlsx 是 READ_WRITE 包，close() 会回写源文件
        Workbook wb;
        try (InputStream is = new FileInputStream(src)) {
            wb = WorkbookFactory.create(is);
        }
        Sheet sheet = wb.getSheetAt(sheetIdx);
        String sheetName = sheet.getSheetName();

        int widthCount = shiftColumnWidths(sheet, del);
        int regionCount = rebuildMergedRegions(sheet, del);
        int cellCount = shiftCells(sheet, del);
        int nameCount = fixNames(wb, sheetName, del, wb.getSpreadsheetVersion());
        // setCellFormula 会清空缓存结果，导入按缓存值读取，写回前重算一次
        wb.getCreationHelper().createFormulaEvaluator().evaluateAll();

        try (OutputStream os = new FileOutputStream(dst)) {
            wb.write(os);
        }
        wb.close();
        System.out.println("deleted col " + del + " -> " + dst);
        System.out.println("colWidthsShifted=" + widthCount + " mergedRegionsRebuilt=" + regionCount
                + " cellsMoved=" + cellCount + " namesFixed=" + nameCount);
    }

    private static int shiftColumnWidths(Sheet sheet, int del) {
        int used = del + 1;
        for (Row r : sheet) {
            used = Math.max(used, r.getLastCellNum());
        }
        int[] width = new int[Math.min(used + 1, 256)];
        for (int c = 0; c < width.length; c++) {
            width[c] = sheet.getColumnWidth(c);
        }
        for (int c = del; c < width.length - 1; c++) {
            sheet.setColumnWidth(c, width[c + 1]);
        }
        return width.length - 1 - del;
    }

    private static int rebuildMergedRegions(Sheet sheet, int del) {
        List<CellRangeAddress> kept = new ArrayList<>();
        for (CellRangeAddress ra : sheet.getMergedRegions()) {
            if (ra.getFirstColumn() == del && ra.getLastColumn() == del) {
                continue;
            }
            int first = ra.getFirstColumn() > del ? ra.getFirstColumn() - 1 : ra.getFirstColumn();
            int last = ra.getLastColumn() >= del ? ra.getLastColumn() - 1 : ra.getLastColumn();
            if (last < first) {
                continue;
            }
            kept.add(new CellRangeAddress(ra.getFirstRow(), ra.getLastRow(), first, last));
        }
        List<Integer> all = new ArrayList<>();
        for (int i = 0; i < sheet.getNumMergedRegions(); i++) {
            all.add(i);
        }
        sheet.removeMergedRegions(all);
        for (CellRangeAddress ra : kept) {
            sheet.addMergedRegionUnsafe(ra);
        }
        return kept.size();
    }

    private static int shiftCells(Sheet sheet, int del) {
        int moved = 0;
        for (Row row : sheet) {
            int last = row.getLastCellNum();
            if (last - 1 < del) {
                continue;
            }
            for (int c = del + 1; c < last; c++) {
                Cell src = row.getCell(c);
                Cell dst = row.getCell(c - 1);
                if (src == null) {
                    if (dst != null) {
                        row.removeCell(dst);
                    }
                    continue;
                }
                if (dst == null) {
                    dst = row.createCell(c - 1);
                }
                dst.setCellStyle(src.getCellStyle());
                copyValue(src, dst, del);
                moved++;
            }
            Cell tail = row.getCell(last - 1);
            if (tail != null) {
                row.removeCell(tail);
            }
        }
        return moved;
    }

    private static void copyValue(Cell src, Cell dst, int del) {
        CellType type = src.getCellType();
        if (dst.getCellType() == CellType.FORMULA) {
            dst.setBlank();
        }
        if (type == CellType.STRING) {
            dst.setCellValue(src.getRichStringCellValue());
        } else if (type == CellType.NUMERIC) {
            dst.setCellValue(src.getNumericCellValue());
        } else if (type == CellType.BOOLEAN) {
            dst.setCellValue(src.getBooleanCellValue());
        } else if (type == CellType.FORMULA) {
            dst.setCellFormula(shiftFormula(src.getCellFormula(), del));
        } else {
            dst.setBlank();
        }
    }

    private static String shiftFormula(String formula, int del) {
        Matcher m = REF_PATTERN.matcher(formula);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            int col = CellReference.convertColStringToIndex(m.group(2));
            String replaced = m.group(0);
            if (col == del) {
                System.out.println("WARN 公式引用了被删列: " + formula);
            } else if (col > del) {
                replaced = m.group(1) + CellReference.convertNumToColString(col - 1) + m.group(3) + m.group(4);
            }
            m.appendReplacement(sb, Matcher.quoteReplacement(replaced));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    private static int fixNames(Workbook wb, String sheetName, int del, SpreadsheetVersion ver) {
        int fixed = 0;
        List<Integer> toDelete = new ArrayList<>();
        for (int i = 0; i < wb.getNumberOfNames(); i++) {
            Name name = wb.getNameAt(i);
            if (name.isDeleted() || !sheetName.equals(name.getSheetName())) {
                continue;
            }
            String formula = name.getRefersToFormula();
            AreaReference area = parse(formula, ver);
            if (area == null) {
                continue;
            }
            CellReference first = area.getFirstCell();
            CellReference last = area.getLastCell();
            int fc = first.getCol() > del ? first.getCol() - 1 : first.getCol();
            int lc = last.getCol() >= del ? Math.max(last.getCol() - 1, 0) : last.getCol();
            if (fc > lc) {
                toDelete.add(i);
                continue;
            }
            if (fc == first.getCol() && lc == last.getCol()) {
                continue;
            }
            String absolute = quoteSheet(sheetName) + "!" + absRef(first.getRow(), fc) + ":" + absRef(last.getRow(), lc);
            name.setRefersToFormula(absolute);
            fixed++;
            System.out.println("name " + name.getNameName() + ": " + formula + " -> " + name.getRefersToFormula());
        }
        for (int i = toDelete.size() - 1; i >= 0; i--) {
            wb.removeName(wb.getNameAt(toDelete.get(i)));
            fixed++;
        }
        return fixed;
    }

    private static String absRef(int row, int col) {
        return "$" + CellReference.convertNumToColString(col) + "$" + (row + 1);
    }

    private static String quoteSheet(String sheetName) {
        return "'" + sheetName.replace("'", "''") + "'";
    }

    private static AreaReference parse(String formula, SpreadsheetVersion ver) {
        try {
            int bang = formula.lastIndexOf('!');
            String ref = bang >= 0 ? formula.substring(bang + 1) : formula;
            return new AreaReference(ref, ver);
        } catch (Exception e) {
            System.out.println("skip name (not an area): " + formula);
            return null;
        }
    }
}
