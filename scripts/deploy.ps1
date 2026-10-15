param(
    [Parameter(Mandatory)]
    [ValidateSet("dev", "prod")]
    [string]$Env
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$chart    = Join-Path $repoRoot "charts/webapp"
$values   = Join-Path $repoRoot "envs/$Env/values.yaml"

Write-Host "Deploying webapp to webapp-$Env ..."
helm upgrade --install webapp $chart `
    --namespace "webapp-$Env" --create-namespace `
    -f $values --wait --timeout 2m

if ($LASTEXITCODE -ne 0) { throw "helm upgrade failed (exit code $LASTEXITCODE)" }