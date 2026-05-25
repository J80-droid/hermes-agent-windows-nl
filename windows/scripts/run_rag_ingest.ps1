# LanceDB ingest vanuit hermes-env (conda) + UTF-8 log + correcte exitcode.
# Aangeroepen door update_knowledge.bat — niet handmatig in een lege PowerShell zonder env.
param(
    [string]$LogPath = "",
    [string]$CondaEnv = "hermes-env",
    [string]$RepoRoot = ""
)

# Niet "Stop": cmd/python schrijven waarschuwingen naar stderr (torch e.d.) — dat is geen fout.
$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "rag_log_encoding.ps1")
. (Join-Path $scriptDir "rag_ingest_log_filter.ps1")
. (Join-Path $scriptDir "enable_console_ansi.ps1")
. (Join-Path $scriptDir "..\HermesPythonPolicy.ps1")
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}
Set-Location $RepoRoot

if (-not $LogPath) {
    $LogPath = Join-Path $scriptDir "rag_ingest_run.log"
}

function Resolve-ActivateBat {
    if ($env:HERMES_ACTIVATE_BAT -and (Test-Path $env:HERMES_ACTIVATE_BAT)) {
        return $env:HERMES_ACTIVATE_BAT
    }
    if ($env:HERMES_CONDA_ROOT) {
        $c = Join-Path $env:HERMES_CONDA_ROOT "Scripts\activate.bat"
        if (Test-Path $c) { return $c }
    }
    foreach ($p in @(
            "$env:USERPROFILE\miniconda3\Scripts\activate.bat",
            "$env:USERPROFILE\anaconda3\Scripts\activate.bat",
            "$env:LOCALAPPDATA\miniconda3\Scripts\activate.bat"
        )) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$activate = Resolve-ActivateBat
if (-not $activate) {
    Write-Error "conda activate.bat niet gevonden. Zet HERMES_ACTIVATE_BAT of installeer Miniconda."
    exit 1
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONUTF8 = "1"
$tesseractBin = "C:\Program Files\Tesseract-OCR"
if (Test-Path $tesseractBin) {
    $env:PATH = "$tesseractBin;$env:PATH"
}
$userTess = Join-Path $env:USERPROFILE "Hermes"
$nld = Join-Path $userTess "tessdata\nld.traineddata"
if (Test-Path $nld) {
    # pytesseract: TESSDATA_PREFIX = map met eng.traineddata / nld.traineddata
    $env:TESSDATA_PREFIX = Join-Path $userTess "tessdata"
}
if (-not $env:HERMES_RAG_PERF_PROFILE) { $env:HERMES_RAG_PERF_PROFILE = "safe" }
if (-not $env:HERMES_RAG_QUIET_TORCH) { $env:HERMES_RAG_QUIET_TORCH = "1" }
if (-not $env:TRANSFORMERS_VERBOSITY) { $env:TRANSFORMERS_VERBOSITY = "error" }

# Perf defaults (zelfde als update_knowledge.bat)
$perfScript = Join-Path $scriptDir "rag_ingest_perf_defaults.ps1"
if (Test-Path $perfScript) {
    . $perfScript
}

$pyExe = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
if (-not $pyExe) {
    Write-Error "Geen conda hermes-env gevonden. Draai windows\REPAIR_PYTHON.bat."
    exit 1
}

$cmd = @"
call "$activate" $CondaEnv
if errorlevel 1 exit /b 1
cd /d "$RepoRoot"
set HERMES_FORCE_COLOR=1
set FORCE_COLOR=1
set PYTHONIOENCODING=utf-8
"$pyExe" -u scripts\rag_pipeline\ingest.py
exit /b %ERRORLEVEL%
"@

$tmpBat = Join-Path $env:TEMP ("hermes_rag_ingest_{0}.cmd" -f [guid]::NewGuid().ToString("N"))
Set-Content -Path $tmpBat -Value $cmd -Encoding ASCII

Write-Host ('[INFO] ' + 'Ingest via conda env: ' + $CondaEnv)
Write-Host ('[INFO] ' + 'Log (UTF-8): ' + $LogPath)
Write-Host ('[INFO] ' + 'Live: ' + $env:HERMES_LANCEDB_PATH + '\rag_ingest_live_status.json')

$writer = New-RagIngestLogWriter -LogPath $LogPath
$exit = 0
try {
    & cmd /c $tmpBat 2>&1 | ForEach-Object {
        # stderr (torch-waarschuwingen) is geen fout — platte string, geen RemoteException-regel.
        $line = if ($_ -is [System.Management.Automation.ErrorRecord]) {
            $_.ToString()
        } elseif ($_ -is [string]) {
            $_
        } else {
            $_.ToString()
        }
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        if (Test-RagIngestNoiseLine $line) { return }
        if ($line -match '^(System\.Management\.Automation\.RemoteException|CategoryInfo|FullyQualifiedErrorId)') {
            return
        }
        Write-RagConsoleLine $line
        $writer.WriteLine((Clear-RagAnsi $line))
        $writer.Flush()
    }
    if ($null -ne $LASTEXITCODE) { $exit = [int]$LASTEXITCODE }
} finally {
    $writer.Dispose()
    Remove-Item -LiteralPath $tmpBat -Force -ErrorAction SilentlyContinue
}

exit $exit
