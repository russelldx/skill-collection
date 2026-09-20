import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.*;

import java.io.FileInputStream;

/**
 * 开发期工具：全量 dump .xls 每个 sheet 的单元格内容、列宽、样式（字体/对齐/边框/填充）。
 * 用法: java DumpAll <src.xls>
 */
public class DumpAll {

    public static void main(String[] args) throws Exception {
        String src = args[0];
        try (HSSFWorkbook wb = new HSSFWorkbook(new FileInputStream(src))) {
            System.out.println("== sheets: " + wb.getNumberOfSheets());
            for (int i = 0; i < wb.getNumberOfSheets(); i++) {
                Sheet sh = wb.getSheetAt(i);
                System.out.println("-- sheet[" + i + "] name=" + sh.getSheetName()
                        + " lastRow=" + sh.getLastRowNum() + " dvCount=" + sh.getDataValidations().size());
                for (int r = 0; r <= sh.getLastRowNum(); r++) {
                    Row row = sh.getRow(r);
                    if (row == null) {
                        continue;
                    }
                    for (int c = 0; c < row.getLastCellNum(); c++) {
                        Cell cell = row.getCell(c);
                        if (cell == null) {
                            continue;
                        }
                        String v = getCellValue(cell);
                        if (v.isEmpty() && cell.getCellType() == CellType.BLANK) {
                            continue;
                        }
                        CellStyle st = cell.getCellStyle();
                        Font f = wb.getFontAt(st.getFontIndex());
                        StringBuilder sb = new StringBuilder();
                        sb.append(String.format("  %s!%s%d", sh.getSheetName(), colName(c), r + 1));
                        sb.append(" [" + v.replace('\n', '|') + "]");
                        sb.append(" font=" + f.getFontName() + "/" + f.getFontHeightInPoints()
                                + (f.getBold() ? "/bold" : "") + "/color" + f.getColor());
                        sb.append(" align=" + st.getAlignment() + " v=" + st.getVerticalAlignment());
                        sb.append(" wrap=" + st.getWrapText());
                        sb.append(" fill=" + st.getFillForegroundColor());
                        sb.append(" border=" + st.getBorderTop() + "/" + st.getBorderBottom()
                                + "/" + st.getBorderLeft() + "/" + st.getBorderRight());
                        System.out.println(sb);
                    }
                }
                System.out.println("  == columns width:");
                for (int c = 0; c <= (sh.getLastRowNum() >= 0 ? lastCol(sh) : -1); c++) {
                    int w = sh.getColumnWidth(c);
                    if (w > 0) {
                        System.out.println("    col" + colName(c) + "=" + w + " (~" + (w / 256.0) + " chars)");
                    }
                }
            }
        }
    }

    private static int lastCol(Sheet sh) {
        int max = -1;
        for (int r = 0; r <= sh.getLastRowNum(); r++) {
            Row row = sh.getRow(r);
            if (row != null && row.getLastCellNum() > max) {
                max = row.getLastCellNum() - 1;
            }
        }
        return max;
    }

    private static String getCellValue(Cell cell) {
        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue();
            case NUMERIC:
                double d = cell.getNumericCellValue();
                return d == Math.floor(d) ? String.valueOf((long) d) : String.valueOf(d);
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            case FORMULA:
                return "=" + cell.getCellFormula();
            default:
                return "";
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
}
