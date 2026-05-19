@{
    # Hermes windows-scripts zijn CLI-/gebruikersgericht; Write-Host is bewust.
    ExcludeRules = @(
        'PSAvoidUsingWriteHost'
    )
}
