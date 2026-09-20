import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.*;
import java.io.FileInputStream;
public class RowInfo {
    public static void main(String[] args) throws Exception {
        try (HSSFWorkbook wb = new HSSFWorkbook(new FileInputStream(args[0]))) {
            for (int i = 0; i < wb.getNumberOfSheets(); i++) {
                Sheet sh = wb.getSheetAt(i);
                System.out.println("== " + sh.getSheetName());
                for (int r = 0; r <= Math.min(sh.getLastRowNum(), 5); r++) {
                    Row row = sh.getRow(r);
                    if (row == null) continue;
                    System.out.println("  row" + r + " height=" + row.getHeight() + " (~" + (row.getHeight() / 20.0) + "pt) custom=" + row.getHeight());
                }
                System.out.println("  col widths: " + sh.getLastRowNum());
                for (int c = 0; c < 40; c++) {
                    int w = sh.getColumnWidth(c);
                    if (w > 0) System.out.print(" " + colName(c) + "=" + (int)(w/256.0));
                }
                System.out.println();
            }
        }
    }
    static String colName(int col){StringBuilder sb=new StringBuilder();int c=col;while(c>=0){sb.insert(0,(char)('A'+(c%26)));c=c/26-1;}return sb.toString();}
}
