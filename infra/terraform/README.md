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
