# Gedeelde UTF-8 (zonder BOM) log-hulp — voorkomt mojibake in Cursor/VS Code.
function Clear-RagAnsi {
    param([string]$Text)
    if (-not $Text) { return $Text }
    return [regex]::Replace($Text, '\x1b\[[0-9;?]*[ -/]*[@-~]', '')
}

function Write-RagConsoleLine {
    param([string]$Line)
    # Log = plat tekst; console = ANSI (VT moet aan staan via enable_console_ansi.ps1).
    [Console]::WriteLine($Line)
}

function New-RagIngestLogWriter {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$LogPath)
    if ($PSCmdlet.ShouldProcess($LogPath, 'Create', 'RAG ingest log')) {
        if (Test-Path -LiteralPath $LogPath) {
            Remove-Item -LiteralPath $LogPath -Force -ErrorAction SilentlyContinue
        }
        $utf8 = New-Object System.Text.UTF8Encoding $false
        return [System.IO.StreamWriter]::new($LogPath, $false, $utf8)
    }
    return $null
}

function Repair-RagIngestLogEncoding {
    param([Parameter(Mandatory)][string]$LogPath)
    if (-not (Test-Path -LiteralPath $LogPath)) { return }
    $bytes = [System.IO.File]::ReadAllBytes($LogPath)
    if ($bytes.Length -eq 0) { return }
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
        $text = [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
        $text = [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
    } else {
        while ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $bytes = $bytes[3..($bytes.Length - 1)]
        }
        $utf8 = New-Object System.Text.UTF8Encoding $false
        $text = $utf8.GetString($bytes)
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($LogPath, $text, $utf8NoBom)
}
