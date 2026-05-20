# Windows-console: ANSI/VT aan (kleuren voor RAG-ingest + tqdm). PS 5.1+ compatibel.
if ($PSVersionTable.PSVersion.Major -ge 7 -and $null -ne $PSStyle) {
    $PSStyle.OutputRendering = 'Ansi'
}

if (-not ('HermesConsoleVt' -as [type])) {
    $csharp = @"
using System;
using System.Runtime.InteropServices;
public class HermesConsoleVt {
    private const int STD_OUTPUT_HANDLE = -11;
    private const int STD_ERROR_HANDLE = -12;
    private const uint ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4;
    [DllImport("kernel32.dll")]
    private static extern IntPtr GetStdHandle(int nStdHandle);
    [DllImport("kernel32.dll")]
    private static extern bool GetConsoleMode(IntPtr hConsoleHandle, out uint lpMode);
    [DllImport("kernel32.dll")]
    private static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);
    public static void Enable() {
        EnableHandle(GetStdHandle(STD_OUTPUT_HANDLE));
        EnableHandle(GetStdHandle(STD_ERROR_HANDLE));
    }
    private static void EnableHandle(IntPtr h) {
        if (h == IntPtr.Zero || h == new IntPtr(-1)) return;
        uint mode;
        if (!GetConsoleMode(h, out mode)) return;
        SetConsoleMode(h, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
    }
}
"@
    try {
        Add-Type -TypeDefinition $csharp -Language CSharp -ErrorAction Stop
    } catch {
        Write-Warning "ANSI-console VT niet geactiveerd: $($_.Exception.Message)"
        exit 0
    }
}

try {
    [HermesConsoleVt]::Enable()
} catch {
    Write-Warning "ANSI-console VT enable mislukt: $($_.Exception.Message)"
}

exit 0
