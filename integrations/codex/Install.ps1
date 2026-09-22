param(
    [ValidateSet('auto','cpu','cuda','mps')][string]$Device = 'auto',
    [ValidateSet('plugin','direct','none')][string]$Mode = 'plugin',
    [ValidateSet('default','cpu','cu128')][string]$TorchIndex = 'default',
    [switch]$MigrateExisting
)
$ErrorActionPreference = 'Stop'
$setupArgs = @((Join-Path $PSScriptRoot 'bootstrap.py'), 'install', '--device', $Device, '--mode', $Mode, '--torch-index', $TorchIndex)
if ($MigrateExisting) { $setupArgs += '--migrate-existing' }
& py -3.12 @setupArgs
exit $LASTEXITCODE
