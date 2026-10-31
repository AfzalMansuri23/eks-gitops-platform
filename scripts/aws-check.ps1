<#
Read-only: lists anything still billing in the region after a lab session.
Exits 1 if something is left, 0 if the account is clean. The state bucket and
ECR repositories are expected to stay and are not reported.

  .\scripts\aws-check.ps1
#>
param(
    [string]$Region = "ap-south-1"
)

$ErrorActionPreference = "Stop"

function Get-Aws {
    param([string[]]$Arguments)
    $out = & aws @Arguments --region $Region --output json
    if ($LASTEXITCODE -ne 0) { throw "aws $($Arguments -join ' ') failed" }
    if ($out) { return ($out | Out-String | ConvertFrom-Json) }
    return $null
}

$checks = [ordered]@{
    "EKS clusters"         = { Get-Aws @("eks", "list-clusters", "--query", "clusters") }
    "EC2 instances"        = { Get-Aws @("ec2", "describe-instances", "--filters", "Name=instance-state-name,Values=pending,running,stopping,stopped", "--query", "Reservations[].Instances[].InstanceId") }
    "NAT gateways"         = { Get-Aws @("ec2", "describe-nat-gateways", "--filter", "Name=state,Values=pending,available", "--query", "NatGateways[].NatGatewayId") }
    "Load balancers"       = { Get-Aws @("elbv2", "describe-load-balancers", "--query", "LoadBalancers[].LoadBalancerName") }
    "Classic LBs"          = { Get-Aws @("elb", "describe-load-balancers", "--query", "LoadBalancerDescriptions[].LoadBalancerName") }
    "Unattached volumes"   = { Get-Aws @("ec2", "describe-volumes", "--filters", "Name=status,Values=available", "--query", "Volumes[].VolumeId") }
    "Elastic IPs"          = { Get-Aws @("ec2", "describe-addresses", "--query", "Addresses[].PublicIp") }
}

$left = 0
foreach ($name in $checks.Keys) {
    $found = @(& $checks[$name]) | Where-Object { $_ }
    if ($found.Count -gt 0) {
        $left += $found.Count
        Write-Host ("{0,-20} {1} left: {2}" -f $name, $found.Count, ($found -join ", ")) -ForegroundColor Yellow
    } else {
        Write-Host ("{0,-20} none" -f $name) -ForegroundColor Green
    }
}

if ($left -gt 0) {
    Write-Host "`n$left billable resource(s) still exist in $Region." -ForegroundColor Yellow
    exit 1
}
Write-Host "`nNothing billable left in $Region." -ForegroundColor Green
exit 0
