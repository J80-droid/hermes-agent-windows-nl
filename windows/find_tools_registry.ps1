# Zoekt Conda/Anaconda/NVM in uninstall-registry (leesbaar voor support)
$uninstallPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
)
Get-ChildItem -Path $uninstallPaths -ErrorAction SilentlyContinue |
    Get-ItemProperty |
    Where-Object { $_.DisplayName -match 'Conda|Anaconda|NVM' } |
    Select-Object DisplayName, InstallLocation, UninstallString |
    Format-Table -AutoSize
