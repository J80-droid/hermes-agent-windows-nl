# Gedeelde UTF-8 (zonder BOM) log-hulp — voorkomt mojibake in Cursor/VS Code.
function New-RagIngestLogWriter {
    param([Parameter(Mandatory)][string]$LogPath)
    if (Test-Path -LiteralPath $LogPath) {
        Remove-Item -LiteralPath $LogPath -Force -ErrorAction SilentlyContinue
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    return [System.IO.StreamWriter]::new($LogPath, $false, $utf8)
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
