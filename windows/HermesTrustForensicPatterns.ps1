# Trust/forensic checks voor RUN_TRUST_FORENSIC_E2E (functies i.p.v. $script:-patronen: PSES-parser).
function Test-HermesSoulLegalForensicTrust {
    param([string]$Text)
    return ($Text -like '*Forensic*trust*')
}

function Test-HermesUserTrustSeed {
    param([string]$Text)
    if ($Text -like '*no pleaser*') { return $true }
    if ($Text -like '*pleaser-behavior*') { return $true }
    if ($Text -like '*zero babysitting*') { return $true }
    return $false
}

function Test-HermesSoulIdentityLeak {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $false }
    $lower = $Text.ToLowerInvariant()
    if ($lower.Contains('jamel')) { return $true }
    if ($lower.Contains('el mourif')) { return $true }
    return $false
}

function Test-HermesSoulValuesOrAdvisory {
    param([string]$Text)
    if ($Text -like '*Values*Principles*') { return $true }
    if ($Text -like '*Advisory*trust*') { return $true }
    return $false
}

function Test-HermesSoulTrustVerification {
    param([string]$Text)
    if ($Text -like '*Trust*verification*') { return $true }
    if ($Text -like '*Advisory*trust*') { return $true }
    return $false
}
