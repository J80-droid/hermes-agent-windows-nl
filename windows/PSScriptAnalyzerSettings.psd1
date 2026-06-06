@{
    # Hermes windows-scripts: CLI Write-Host; batch in @' here-strings; hyphenated functienamen.
    # Doel: 0 Warning/Error op windows\ (zie Invoke-HermesPSScriptAnalyzer.ps1 / RUN_PSScriptAnalyzer.bat).
    ExcludeRules = @(
        'PSAvoidUsingWriteHost',
        'PSUseSingularNouns',
        'PSUseAliasToAvoidAbbreviations',
        'PSAvoidUsingAliases',
        'PSUseBOMForUnicodeEncodedFile',
        'PSAvoidAssignmentToAutomaticVariable',
        'PSProvideCommentHelp',
        # HermesLaunchVisualState: intentional cross-script launch UI state (dot-sourced + .psm1).
        'PSAvoidGlobalVars'
    )
}
