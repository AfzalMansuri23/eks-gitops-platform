<#
Tears down the EKS lab in the order that leaves nothing billing:

1. delete every LoadBalancer Service and PVC, so Kubernetes removes the AWS
   load balancers and EBS volumes it created (Terraform does not know about
   them, and a destroy with them still present fails with DependencyViolation
   while the load balancer keeps billing)
2. wait until AWS shows no load balancer tagged for the cluster
3. terraform destroy eks, then network (keeps the state bucket)
4. scripts/aws-check.ps1 confirms nothing billable is left

  .\scripts\eks-down.ps1
  .\scripts\eks-down.ps1 -KeepNetwork   # leaves the VPC and NAT up (the NAT bills hourly)
#>
param(
    [string]$Region = "ap-south-1",
    [string]$Context = "eks-gitops",
    [switch]$KeepNetwork,
    [int]$WaitMinutes = 10
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

function Get-ClusterLoadBalancers {
    $arns = aws resourcegroupstaggingapi get-resources --region $Region `
        --tag-filters "Key=kubernetes.io/cluster/$cluster" `
        --resource-type-filters elasticloadbalancing:loadbalancer `
        --query "ResourceTagMappingList[].ResourceARN" --output text
    if ($LASTEXITCODE -ne 0) { throw "could not list load balancers" }
    return @($arns -split "\s+" | Where-Object { $_ })
}

aws eks describe-cluster --region $Region --name $cluster --query "cluster.status" --output text 2>$null | Out-Null
$clusterExists = ($LASTEXITCODE -eq 0)

if ($clusterExists) {
    Invoke-Step "kubeconfig" { aws eks update-kubeconfig --region $Region --name $cluster --alias $Context }

    Invoke-Step "delete LoadBalancer services" {
        $svcs = kubectl --context $Context get svc -A -o json | ConvertFrom-Json
        foreach ($s in $svcs.items | Where-Object { $_.spec.type -eq "LoadBalancer" }) {
            kubectl --context $Context -n $s.metadata.namespace delete svc $s.metadata.name --wait=false
        }
        $global:LASTEXITCODE = 0
    }
    Invoke-Step "delete PVCs (their EBS volumes)" { kubectl --context $Context delete pvc --all --all-namespaces --wait=false }

    Write-Host "`n== waiting for AWS to remove the cluster's load balancers" -ForegroundColor Cyan
    $deadline = (Get-Date).AddMinutes($WaitMinutes)
    while ((Get-ClusterLoadBalancers).Count -gt 0) {
        if ((Get-Date) -gt $deadline) { throw "load balancers still present after $WaitMinutes min: $(Get-ClusterLoadBalancers -join ', ')" }
        Start-Sleep -Seconds 15
    }
    Write-Host "no load balancers left"
} else {
    Write-Host "Cluster $cluster not found; skipping the Kubernetes cleanup."
}

# destroy still needs values for the required variables; nothing is created with them
$eksVars = Join-Path $env:TEMP "eks-gitops-destroy.tfvars.json"
@{ admin_cidrs = @("192.0.2.1/32") } | ConvertTo-Json | Set-Content -Encoding ascii $eksVars

Invoke-Step "terraform init (eks)" { terraform "-chdir=$tf/eks" init -input=false -reconfigure "-backend-config=../backend.hcl" }
Invoke-Step "terraform destroy (eks)" { terraform "-chdir=$tf/eks" destroy "-var-file=$eksVars" }
Remove-Item $eksVars -ErrorAction SilentlyContinue

if (-not $KeepNetwork) {
    Invoke-Step "terraform init (network)" { terraform "-chdir=$tf/network" init -input=false -reconfigure "-backend-config=../backend.hcl" }
    Invoke-Step "terraform destroy (network)" { terraform "-chdir=$tf/network" destroy }
}

kubectl config delete-context $Context 2>$null | Out-Null
Write-Host "`n== checking for anything still billing" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "aws-check.ps1") -Region $Region
exit $LASTEXITCODE
