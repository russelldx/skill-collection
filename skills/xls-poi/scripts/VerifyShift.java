/** Fail-closed legacy entrypoint. Original source is in references/paused-delete-column/. */
public final class VerifyShift {
    public static void main(String[] args) {
        System.err.println("PAUSED: the legacy verifier excludes DV, merged regions and widths "
                + "from MISMATCHES. It cannot certify column deletion. No workbook was opened or written.");
        System.exit(2);
    }
}
