<#
Brings up the EKS lab: network, cluster, ingress-nginx.

Locked to the IP you run it from: the EKS API endpoint and the load balancer
accept only <your-ip>/32. Terraform asks before each apply.

Optional: set $env:EXITZERO_EKS_ANTHROPIC_KEY to a separate, spend-limited key
for this session and the script stores it as a Kubernetes Secret. The key is
piped to kubectl, so it is never written to disk or shown in a command line.

  .\scripts\eks-up.ps1
  .\scripts\eks-down.ps1     # same day, always
#>
param(
    [string]$Region = "ap-south-1",
    [ValidateSet("t3.small", "c7i-flex.large", "m7i-flex.large")]
    [string]$NodeType = "c7i-flex.large",
    [string]$Context = "eks-gitops",
    [string]$IngressChartVersion = "4.15.1"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$tf = Join-Path $root "infra/terraform"
$cluster = "eks-gitops-platform"

function Invoke-Step {
    param([string]$Name, [scriptblock]$Command)
    Write-Host "`n== $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Name failed (exit code $LASTEXITCODE)" }
}

if (-not (Test-Path (Join-Path $tf "backend.hcl"))) {
    throw "infra/terraform/backend.hcl is missing: copy backend.hcl.example and fill in the state bucket"
}

$myIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
if ($myIp -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { throw "could not read your public IPv4 address (got '$myIp')" }
Write-Host "Your public IP is $myIp. Only $myIp/32 will reach the EKS API and the load balancer."

# variables go through files, not quoted command-line JSON
$eksVars = Join-Path $env:TEMP "eks-gitops-admin.tfvars.json"
@{ admin_cidrs = @("$myIp/32"); node_instance_type = $NodeType } | ConvertTo-Json | Set-Content -Encoding ascii $eksVars
$ingressVars = Join-Path $env:TEMP "eks-gitops-ingress-sources.yaml"
"controller:`n  service:`n    loadBalancerSourceRanges:`n      - $myIp/32" | Set-Content -Encoding ascii $ingressVars

Invoke-Step "terraform init (network)" { terraform "-chdir=$tf/network" init -input=false -reconfigure "-backend-config=../backend.hcl" }
Invoke-Step "terraform apply (network)" { terraform "-chdir=$tf/network" apply }
Invoke-Step "terraform init (eks)" { terraform "-chdir=$tf/eks" init -input=false -reconfigure "-backend-config=../backend.hcl" }
Invoke-Step "terraform apply (eks)" { terraform "-chdir=$tf/eks" apply "-var-file=$eksVars" }

Invoke-Step "kubeconfig" { aws eks update-kubeconfig --region $Region --name $cluster --alias $Context }
Invoke-Step "nodes" { kubectl --context $Context get nodes -o wide }

Invoke-Step "ingress-nginx" {
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx --force-update
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --kube-context $Context `
        --namespace ingress-nginx --create-namespace --version $IngressChartVersion `
        -f (Join-Path $root "k8s/eks/ingress-nginx-values.yaml") -f $ingressVars --wait
}

if ($env:EXITZERO_EKS_ANTHROPIC_KEY) {
    Invoke-Step "ExitZero API key secret" {
        $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:EXITZERO_EKS_ANTHROPIC_KEY))
        $manifest = "apiVersion: v1`nkind: Namespace`nmetadata:`n  name: assistant`n---`napiVersion: v1`nkind: Secret`nmetadata:`n  name: exitzero-anthropic`n  namespace: assistant`ntype: Opaque`ndata:`n  ANTHROPIC_API_KEY: $b64`n"
        $manifest | kubectl --context $Context apply -f -
        Remove-Variable b64, manifest
    }
} else {
    Write-Host "`nNo EXITZERO_EKS_ANTHROPIC_KEY set: ExitZero will run without agent mode." -ForegroundColor Yellow
}

Remove-Item $eksVars, $ingressVars -ErrorAction SilentlyContinue
$lb = kubectl --context $Context -n ingress-nginx get svc ingress-nginx-controller -o "jsonpath={.status.loadBalancer.ingress[0].hostname}"
Write-Host "`nUp. Load balancer: http://$lb (reachable from $myIp only; DNS can take a few minutes)." -ForegroundColor Green
Write-Host "Billing has started (about `$0.27/hour). Run .\scripts\eks-down.ps1 the same day." -ForegroundColor Yellow
