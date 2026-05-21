@{
    # Hermes windows-scripts: CLI Write-Host; batch in @' here-strings; hyphenated functienamen.
    ExcludeRules = @(
        'PSAvoidUsingWriteHost',
        'PSUseSingularNouns',
        'PSUseAliasToAvoidAbbreviations',
        'PSAvoidUsingAliases'
    )
}
