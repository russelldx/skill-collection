import org.apache.poi.ss.usermodel.*;
import org.apache.poi.hssf.usermodel.*;
import java.io.FileInputStream;
public class CheckRich {
    public static void main(String[] args) throws Exception {
        try (HSSFWorkbook wb = new HSSFWorkbook(new FileInputStream(args[0]))) {
            Sheet sh = wb.getSheetAt(0);
            Row row = sh.getRow(2);
            for (int c = 0; c < row.getLastCellNum(); c++) {
                Cell cell = row.getCell(c);
                if (cell == null || cell.getCellType() != CellType.STRING) continue;
                HSSFRichTextString rt = (HSSFRichTextString) cell.getRichStringCellValue();
                String t = rt.getString();
                if (!t.contains("【")) continue;
                short f1 = rt.getFontAtIndex(0);
                short f2 = rt.getFontAtIndex(t.length() - 1);
                HSSFFont fnt = wb.getFontAt(f2);
                System.out.println(colName(c) + ": [" + t + "] font0=" + f1 + " fontEnd=" + f2 + " endColor=" + fnt.getColor() + " endBold=" + fnt.getBold());
            }
        }
    }
    static String colName(int col){StringBuilder sb=new StringBuilder();int c=col;while(c>=0){sb.insert(0,(char)('A'+(c%26)));c=c/26-1;}return sb.toString();}
}
