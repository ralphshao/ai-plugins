# Runs ai-plugins.py with the first Python 3.9+ on PATH: run.ps1 <add|remove|update> [args]
foreach ($python in 'python3', 'python', 'py') {
  if (-not (Get-Command $python -CommandType Application -ErrorAction SilentlyContinue)) { continue }
  & $python -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>$null
  if ($LASTEXITCODE -eq 0) { & $python (Join-Path $PSScriptRoot 'ai-plugins.py') @args; exit $LASTEXITCODE }
}
Write-Error 'Python 3.9+ is required'
exit 1
