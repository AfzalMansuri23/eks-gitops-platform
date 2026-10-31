# Infrastructure (Terraform)

Three root modules, each with its own state in one S3 bucket (`use_lockfile` for locking):

| Module | What it creates |
|---|---|
| `bootstrap` | ECR repos (API image, Helm chart), GitHub OIDC provider and the two CI roles |
| `network` | VPC, 2 public and 2 private subnets, internet gateway, NAT gateway |
| `eks` | EKS cluster and node group in the private subnets (reads them from `network` state) |

## Account-specific values stay out of Git

The state bucket name contains the AWS account ID, so it is not in the code.

- **Locally:** copy `backend.hcl.example` to `backend.hcl` (gitignored) and fill in the bucket. For `eks`, also set `state_bucket` in `eks/terraform.tfvars` (gitignored) or `TF_VAR_state_bucket`.
- **In CI:** the workflows read repository secrets: `AWS_ROLE_ARN` (main-only push role), `AWS_PLAN_ROLE_ARN` (PR read-only role) and `TF_STATE_BUCKET`.

```sh
cd infra/terraform/network
terraform init -backend-config=../backend.hcl
terraform apply

cd ../eks
terraform init -backend-config=../backend.hcl
terraform apply            # state_bucket comes from terraform.tfvars
```

An existing checkout that was initialized before the bucket moved out of the code needs `terraform init -reconfigure -backend-config=../backend.hcl` once.

## EKS lab day

```powershell
.\scripts\eks-up.ps1      # network + EKS + ingress-nginx, locked to your current IP
# ... demo ...
.\scripts\eks-down.ps1    # same day: removes k8s-made load balancers and volumes first, then destroys
.\scripts\aws-check.ps1   # read-only: exits 1 if anything billable is left
```

| Safeguard | Where |
|---|---|
| EKS API endpoint only reachable from your IP (`admin_cidrs`, never `0.0.0.0/0`) | `eks/main.tf` |
| Load balancer only reachable from your IP (`loadBalancerSourceRanges`) | `scripts/eks-up.ps1`, `k8s/eks/ingress-nginx-values.yaml` |
| NetworkPolicies enforced: managed VPC CNI with `enableNetworkPolicy` (EKS ignores them otherwise) | `eks/main.tf` |
| Pods cannot use the node's IAM role: IMDSv2 required, hop limit 1 | `eks/main.tf` (launch template) |
| Node type limited to free-tier-eligible types (`t3.medium` is not; default `c7i-flex.large`, 4 GiB) | `eks/main.tf` |
| Teardown order: LoadBalancer Services and PVCs deleted and waited for before `terraform destroy` | `scripts/eks-down.ps1` |
| ExitZero image scanned by Trivy (HIGH/CRITICAL) before it is pushed to ECR | `.github/workflows/assistant.yml` |
| Agent mode key: a separate, spend-limited key in `EXITZERO_EKS_ANTHROPIC_KEY`, piped into a Secret, deleted after the demo | `scripts/eks-up.ps1` |

Cost while up: about $0.27 per hour (control plane, 2 nodes, NAT, NLB). Before the first EKS day, apply `bootstrap` once so the `eks-gitops-platform/assistant` ECR repository exists.
