# Unit tests: Repair-SoulDuplicateConfigGovernanceBlocks
$ErrorActionPreference = 'Stop'
$moduleRoot = Join-Path $PSScriptRoot '..\scripts'
Import-Module (Join-Path $moduleRoot 'SyncSoulSnippet.psm1') -Force

Describe 'Repair-SoulDuplicateConfigGovernanceBlocks' {
    It 'Verwijdert dubbele Config governance-blokken (houdt eerste)' {
        $dup = @'
# SOUL.md - legal

## Config governance (Windows)

- eerste

## Identity

x

## Values & Principles

y

## Config governance (Windows)

- tweede

## Communication Style

z
'@
        $fixed = Repair-SoulDuplicateConfigGovernanceBlocks -Content $dup
        $count = ([regex]::Matches($fixed, '(?m)^## Config governance \(Windows\)')).Count
        $count | Should Be 1
        ($fixed -match 'eerste') | Should Be $true
        ($fixed -match 'tweede') | Should Be $false
    }

    It 'Laat lege string ongemoeid' {
        Repair-SoulDuplicateConfigGovernanceBlocks -Content '' | Should Be ''
    }

    It 'Laat enkelvoudig blok ongemoeid' {
        $single = @'
## Config governance (Windows)

- ok

## Identity
'@
        $fixed = Repair-SoulDuplicateConfigGovernanceBlocks -Content $single
        ([regex]::Matches($fixed, '(?m)^## Config governance')).Count | Should Be 1
        ($fixed -match 'ok') | Should Be $true
    }

    It 'Verwijdert drie dubbele koppen' {
        $triple = @'
## Config governance (Windows)

a

## Identity

## Config governance (Windows)

b

## Communication Style

## Config governance (Windows)

c
'@
        $fixed = Repair-SoulDuplicateConfigGovernanceBlocks -Content $triple
        ([regex]::Matches($fixed, '(?m)^## Config governance \(Windows\)')).Count | Should Be 1
        ($fixed -match '\ba\b') | Should Be $true
        ($fixed -match '\bb\b') | Should Be $false
        ($fixed -match '\bc\b') | Should Be $false
    }
}

Describe 'Test-IsLegalProfileMemoryUserPath' {
    . (Join-Path $moduleRoot 'HermesMemoryMergeCommon.ps1')

    It 'Herkennt legal USER-pad (Windows en forward slashes)' {
        (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\hermes\profiles\legal\memories\USER.md') | Should Be $true
        (Test-IsLegalProfileMemoryUserPath -FilePath '/home/hermes/profiles/legal/memories/USER.md') | Should Be $true
        (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\hermes\profiles\core\memories\USER.md') | Should Be $false
    }
}
