/** Fail-closed legacy entrypoint. Original source is in references/paused-delete-column/. */
public final class DeleteColumn {
    public static void main(String[] args) {
        System.err.println("PAUSED: column deletion does not migrate data validation safely. "
                + "No workbook was opened or written. Reference source is not an executable tool.");
        System.exit(2);
    }
}
