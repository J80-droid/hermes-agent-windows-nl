# Profiel-runtimechecks voor RUN_TRUST_FORENSIC_E2E (apart bestand: PSES-parser).
function Invoke-HermesTrustForensicProfileChecks {
    param(
        [Parameter(Mandatory)][string]$HermesRoot
    )
    $failureCount = 0
    $hermesProfilesPath = Join-Path $HermesRoot 'profiles'
    if (-not (Test-Path -LiteralPath $hermesProfilesPath)) {
        return 0
    }

    Get-ChildItem -LiteralPath $hermesProfilesPath -Directory | ForEach-Object {
        $profileName = $_.Name
        $userPath = Join-Path $_.FullName 'memories/USER.md'
        $memPath = Join-Path $_.FullName 'memories/MEMORY.md'
        $soulPath = Join-Path $_.FullName 'SOUL.md'
        if (-not (Test-Path -LiteralPath $userPath)) {
            Write-Host ("[FAIL] {0}: memories/USER.md ontbreekt" -f $profileName) -ForegroundColor Red
            $failureCount++
            return
        }
        $userText = Get-Content -LiteralPath $userPath -Raw -Encoding UTF8
        if (-not (Test-HermesUserTrustSeed -Text $userText)) {
            Write-Host ("[FAIL] {0}: USER.md mist trust seed" -f $profileName) -ForegroundColor Red
            $failureCount++
        }
        $userLeaks = Get-MemoryFileIdentityLeakLines -FilePath $userPath
        if ($userLeaks.Count -gt 0) {
            Write-Host ("[FAIL] {0}: USER.md identiteitslek (regel-gebaseerd)" -f $profileName) -ForegroundColor Red
            $failureCount++
        }
        if (Test-MemoryDoubleEncoding -Text $userText) {
            Write-Host ("[FAIL] {0}: USER.md double-encoding (section marker)" -f $profileName) -ForegroundColor Red
            $failureCount++
        }
        if (Test-Path -LiteralPath $memPath) {
            $memText = Get-Content -LiteralPath $memPath -Raw -Encoding UTF8
            $memLeaks = Get-MemoryFileIdentityLeakLines -FilePath $memPath
            if ($memLeaks.Count -gt 0) {
                Write-Host ("[FAIL] {0}: MEMORY.md identiteitslek (regel-gebaseerd)" -f $profileName) -ForegroundColor Red
                $failureCount++
            }
            if (Test-MemoryDoubleEncoding -Text $memText) {
                Write-Host ("[FAIL] {0}: MEMORY.md double-encoding (section marker)" -f $profileName) -ForegroundColor Red
                $failureCount++
            }
        }
        if (Test-Path -LiteralPath $soulPath) {
            $soulText = Get-Content -LiteralPath $soulPath -Raw -Encoding UTF8
            if (Test-HermesSoulIdentityLeak -Text $soulText) {
                Write-Host ("[FAIL] {0}: SOUL.md bevat nog identiteitsnaam" -f $profileName) -ForegroundColor Red
                $failureCount++
            }
            if (-not (Test-HermesSoulValuesOrAdvisory -Text $soulText)) {
                Write-Host ("[FAIL] {0}: SOUL.md mist Values en Principles (of legacy Advisory)" -f $profileName) -ForegroundColor Red
                $failureCount++
            }
            if (-not (Test-HermesSoulTrustVerification -Text $soulText)) {
                Write-Host ("[FAIL] {0}: SOUL.md mist Trust en verification" -f $profileName) -ForegroundColor Red
                $failureCount++
            }
        }
    }

    return $failureCount
}
