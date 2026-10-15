param(
    [ValidateSet("dev", "prod", "all")]
    [string]$Env = "all"
)

$ErrorActionPreference = "Stop"

$targets = if ($Env -eq "all") { @("dev", "prod") } else { @($Env) }

foreach ($t in $targets) {
    $ns = "webapp-$t"
    Write-Host "Removing webapp from $ns ..."

    helm uninstall webapp --namespace $ns --ignore-not-found
    kubectl delete namespace $ns --ignore-not-found --wait=true

    if ($LASTEXITCODE -ne 0) { throw "teardown of $ns failed" }
}

Write-Host "Done."