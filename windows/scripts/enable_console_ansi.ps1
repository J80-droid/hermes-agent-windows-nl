# Windows-console: ANSI/VT aan (kleuren voor RAG-ingest + tqdm).
# Aanroepen vóór ingest-output naar [Console]::WriteLine.
if ($PSVersionTable.PSVersion.Major -ge 7 -and $null -ne $PSStyle) {
    $PSStyle.OutputRendering = 'Ansi'
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class HermesConsoleVt {
    const int STD_OUTPUT_HANDLE = -11;
    const int STD_ERROR_HANDLE = -12;
    const uint ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004;
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
    [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr h, out uint mode);
    [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr h, uint mode);
    public static void Enable() {
        foreach (var h in new[] { GetStdHandle(STD_OUTPUT_HANDLE), GetStdHandle(STD_ERROR_HANDLE) }) {
            if (h == IntPtr.Zero || h == new IntPtr(-1)) continue;
            if (!GetConsoleMode(h, out uint mode)) continue;
            SetConsoleMode(h, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
        }
    }
}
"@ -ErrorAction SilentlyContinue | Out-Null

try { [HermesConsoleVt]::Enable() } catch { }
