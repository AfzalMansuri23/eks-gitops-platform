# Terraform

## Resource already exists (needs import)
Matches: `already exists`, `entityalreadyexists`, `bucketalreadyownedbyyou`, `needs to be imported into the state`

**Cause.** The real resource exists but Terraform's state does not know about it, usually because it was created by hand or by another stack.

**Fix.** Import it into state (or add an import block), then plan until there are no changes.

```sh
terraform import <resource-address> <resource-id>
terraform plan
```

## Objects changed outside Terraform (drift)
Matches: `objects have changed outside of terraform`

**Cause.** Someone changed the resource in the console or with another tool, so the real world no longer matches state.

**Fix.** Review the drift with a refresh-only plan, then either accept it into state or let the next apply put the code's values back.

```sh
terraform plan -refresh-only
terraform apply -refresh-only
```

## Invalid count or for_each argument
Matches: `invalid count argument`, `invalid for_each argument`, `cannot be determined until apply`

**Cause.** count or for_each depends on a value only known after apply (for example an ID of a resource created in the same run).

**Fix.** Base count and for_each on values known at plan time (variables, static keys). As a one-off workaround, apply the dependency first with -target.

```sh
terraform apply -target=<resource-address>
terraform apply
```

## Cycle error
Matches: `error: cycle:`

**Cause.** Resources reference each other in a loop, often two security groups that reference each other inline.

**Fix.** Break the loop, for example by moving the rules into separate aws_security_group_rule resources.

```sh
terraform graph
```

## Provider version does not match constraint
Matches: `does not match configured version constraint`, `no available releases match`, `locked provider`

**Cause.** The version in .terraform.lock.hcl or a module's required_providers conflicts with your constraint.

**Fix.** Align the constraints across root and modules, then upgrade the lock file.

```sh
terraform providers
terraform init -upgrade
```

## Backend initialization required
Matches: `backend initialization required`, `reinitialization required`, `backend configuration changed`

**Cause.** The backend block changed (new bucket, key or type), or this directory was never initialized.

**Fix.** Re-run init. Use -migrate-state to copy existing state to the new backend, or -reconfigure to point at it without copying.

```sh
terraform init -migrate-state
terraform init -reconfigure
```

## Unsupported argument after a provider upgrade
Matches: `unsupported argument`, `an argument named`, `is not expected here`, `unsupported block type`

**Cause.** A major provider version renamed or removed the argument.

**Fix.** Check the provider's upgrade guide for the new name, or pin the previous major version until you migrate.

```sh
terraform version
terraform providers
```

## Timeout while waiting for state
Matches: `timeout while waiting for state`, `context deadline exceeded`, `still creating...`

**Cause.** The cloud resource is slow or stuck (an EKS cluster, an RDS instance, a NAT gateway), or it failed on the provider side.

**Fix.** Check the resource in the cloud console or CLI. Raise the resource's timeouts block if it is just slow, and turn on debug logs if it is stuck.

```sh
TF_LOG=DEBUG terraform apply
```

## Destroy fails: DependencyViolation
Matches: `dependencyviolation`, `has dependencies and cannot be deleted`, `resource has a dependent object`

**Cause.** Something created outside Terraform still uses the resource, for example ENIs or load balancers that Kubernetes created in the VPC.

**Fix.** Delete the Kubernetes Services and Ingresses (or other external objects) first, find leftover ENIs, then destroy again.

```sh
aws ec2 describe-network-interfaces --filters Name=vpc-id,Values=<vpc-id> --query "NetworkInterfaces[].{Id:NetworkInterfaceId,Desc:Description}"
terraform destroy
```

## Rename makes Terraform want to destroy and recreate
Matches: `must be replaced`, `forces replacement`, `will be destroyed`

**Cause.** Renaming a resource or moving it into a module changes its address, so Terraform sees a delete plus a create.

**Fix.** Add a moved block (or terraform state mv) so the address changes without touching the real resource.

```sh
terraform state mv <old-address> <new-address>
terraform plan
```

## Saved plan is stale
Matches: `saved plan is stale`

**Cause.** State changed after the plan file was created, so applying it would be unsafe.

**Fix.** Create a fresh plan and apply that.

```sh
terraform plan -out=tfplan
terraform apply tfplan
```

## Provider cannot find credentials
Matches: `error configuring terraform aws provider`, `no valid credential sources found`, `failed to get existing workspaces`

**Cause.** The provider found no credentials, or the backend and the provider use different profiles.

**Fix.** Confirm the identity Terraform will use, set AWS_PROFILE (or the cloud's equivalent), and re-run init.

```sh
aws sts get-caller-identity
export AWS_PROFILE=<profile>
terraform init
```

## State lock held in Terraform Cloud or another backend
Matches: `workspace is locked`, `locked by`, `lock info`

**Cause.** A run is in progress, or a crashed run left the lock behind.

**Fix.** Make sure no run is active, then force-unlock with the lock ID.

```sh
terraform force-unlock <lock-id>
```

## Value for undeclared variable
Matches: `value for undeclared variable`, `undeclared variable`

**Cause.** A -var, a tfvars file or a TF_VAR_ environment variable sets a variable the configuration does not declare, often a misspelled name.

**Fix.** Match the name to a variable block, or add the variable block.

```sh
grep -rn "variable \"" *.tf
```

## Reference to undeclared resource
Matches: `reference to undeclared resource`, `reference to undeclared input variable`, `reference to undeclared module`

**Cause.** The expression points at a resource, variable or module that does not exist under that exact type and name (a spelling difference, or a block that was removed).

**Fix.** Compare the reference with the block's type and name letter by letter. terraform validate catches these before plan.

```sh
terraform validate
```
