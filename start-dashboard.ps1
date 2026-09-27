param([ValidateSet('setup','start')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'scripts\dashboard.py') $Action
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
