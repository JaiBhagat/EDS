# EDS — selective manual install. Thin wrapper over scripts/build-packs.js
# for anyone installing outside the Claude Code marketplace flow.
#
# Usage:
#   ./install.ps1 --list
#   ./install.ps1 --profile core --out C:\eds-install
#   ./install.ps1 --profile full --with production:model-governance,domains:credit-risk --out C:\eds-install

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Error "install.ps1 requires node on PATH"
  exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
node "$ScriptDir\scripts\build-packs.js" @args
