import org.apache.poi.hssf.record.DVRecord;
import org.apache.poi.hssf.record.Record;
import org.apache.poi.hssf.usermodel.HSSFDataValidation;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.formula.ptg.Ptg;
import org.apache.poi.ss.usermodel.Name;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;

import java.io.FileInputStream;
import java.lang.reflect.Field;
import java.util.List;

/**
 * 开发期工具：dump 处室确认版原文件结构（sheet/表头/DV/隐藏列表），只读不写。
 * 用法: java DumpStructure <src.xls>
 */
public class DumpStructure {

    public static void main(String[] args) throws Exception {
        String src = args[0];
        try (HSSFWorkbook wb = new HSSFWorkbook(new FileInputStream(src))) {
            System.out.println("== sheets: " + wb.getNumberOfSheets());
            System.out.println("== names: " + wb.getNumberOfNames());
            for (int n = 0; n < wb.getNumberOfNames(); n++) {
                Name name = wb.getNameAt(n);
                try {
                    System.out.println("-- name=" + name.getNameName() + " refers=" + name.getRefersToFormula());
                } catch (Exception e) {
                    System.out.println("-- name=" + name.getNameName() + " <builtin? " + e.getMessage() + ">");
                }
            }
            for (int i = 0; i < wb.getNumberOfSheets(); i++) {
                Sheet sh = wb.getSheetAt(i);
                System.out.println("-- sheet[" + i + "] name=" + sh.getSheetName()
                        + " lastRow=" + sh.getLastRowNum() + " lastCol=" + getLastCol(sh)
                        + " dvCount=" + sh.getDataValidations().size()
                        + " hidden=" + wb.isSheetHidden(i) + " veryHidden=" + wb.isSheetVeryHidden(i));
                if (sh.getLastRowNum() < 0) {
                    continue;
                }
                int maxRow = Math.min(sh.getLastRowNum(), 4);
                for (int r = 0; r <= maxRow; r++) {
                    Row row = sh.getRow(r);
                    if (row == null) {
                        continue;
                    }
                    int maxCol = Math.min(row.getLastCellNum() - 1, 60);
                    StringBuilder sb = new StringBuilder("  R" + r + ": ");
                    for (int c = 0; c <= maxCol; c++) {
                        Cell cell = row.getCell(c);
                        if (cell != null && cell.getCellType() != CellType.BLANK) {
                            String v = getCellValue(cell);
                            if (!v.isEmpty()) {
                                sb.append("[").append(c).append("]").append(v).append("; ");
                            }
                        }
                    }
                    System.out.println(sb);
                }
                for (DataValidation dv : sh.getDataValidations()) {
                    DVRecord record = getDvRecord(dv);
                    Ptg[] ptgs = record != null ? record.getFormula1() : null;
                    String formula1 = ptgs != null ? ptgsToString(ptgs) : "<null>";
                    int type = record != null ? record.getDataType() : -1;
                    for (CellRangeAddress ra : dv.getRegions().getCellRangeAddresses()) {
                        System.out.println("  DV region=" + ra.formatAsString()
                                + " type=" + type
                                + " formula1=[" + formula1 + "]");
                    }
                }
            }
        }
    }

    private static String ptgsToString(Ptg[] ptgs) {
        StringBuilder sb = new StringBuilder();
        for (Ptg ptg : ptgs) {
            sb.append(ptg.toFormulaString());
        }
        return sb.toString();
    }

    private static DVRecord getDvRecord(DataValidation dv) {
        if (!(dv instanceof HSSFDataValidation)) {
            return null;
        }
        try {
            Field f = HSSFDataValidation.class.getDeclaredField("_dvRecord");
            f.setAccessible(true);
            return (DVRecord) f.get(dv);
        } catch (Exception e) {
            return null;
        }
    }

    private static int getLastCol(Sheet sh) {
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
                return cell.getStringCellValue().replace('\n', '|');
            case NUMERIC:
                double d = cell.getNumericCellValue();
                return d == Math.floor(d) ? String.valueOf((long) d) : String.valueOf(d);
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            default:
                return "";
        }
    }
}
