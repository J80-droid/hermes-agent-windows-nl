# Voegt UTF-8 BOM toe aan .ps1 (PSScriptAnalyzer PSUseBOMForUnicodeEncodedFile).
param(
    [Parameter(Mandatory)][string]$Root,
    [switch]$Quiet
)
$utf8Bom = New-Object System.Text.UTF8Encoding $true
$count = 0
Get-ChildItem -LiteralPath $Root -Filter '*.ps1' -File -Recurse | ForEach-Object {
    $raw = [System.IO.File]::ReadAllText($_.FullName)
    if ($raw.Length -eq 0) { return }
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return
    }
    [System.IO.File]::WriteAllText($_.FullName, $raw, $utf8Bom)
    $count++
    if (-not $Quiet) { Write-Host ('  BOM  ' + $_.FullName) }
}
if (-not $Quiet) { Write-Host ("[OK] UTF-8 BOM toegevoegd aan $count bestand(en).") }
