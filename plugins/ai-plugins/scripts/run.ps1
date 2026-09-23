# Runs ai-plugins.py with the Python on PATH: run.ps1 <add|remove|update> [args]
$python = Get-Command python3, python, py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $python) { Write-Error 'Python 3 is required'; exit 1 }
& $python.Source (Join-Path $PSScriptRoot 'ai-plugins.py') @args
exit $LASTEXITCODE
