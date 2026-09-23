# Thin wrapper: ai-plugins.py add
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot '..\..\..\scripts\ai-plugins.py'
$python = Get-Command python3, python, py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $python) { Write-Error 'Python 3 is required'; exit 1 }
& $python.Source $script add @args
exit $LASTEXITCODE
