# Consulta apenas. Nao altera configuracoes e nao coleta chaves ou conversas.
$ErrorActionPreference = 'Continue'
Write-Output 'Portas 8000/8001 em escuta:'
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in @(8000,8001) } |
    Select-Object LocalAddress, LocalPort, OwningProcess
Write-Output 'Regras de firewall do dashboard antigo:'
Get-NetFirewallRule -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like 'JARVIS Dashboard*' } |
    Select-Object DisplayName, Enabled, Direction, Action, Profile
Write-Output 'Estado do Microsoft Defender:'
Get-MpComputerStatus -ErrorAction SilentlyContinue |
    Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated
Write-Output 'Consulta concluida. Nenhuma alteracao foi feita.'
