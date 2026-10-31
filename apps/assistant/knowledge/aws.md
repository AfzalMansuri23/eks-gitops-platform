# AWS

## AccessDenied: not authorized to perform an action
Matches: `accessdenied`, `is not authorized to perform`, `explicit deny`

**Cause.** The caller has no Allow for that action on that resource, or something denies it: an explicit Deny, a service control policy, a permissions boundary, a resource policy (bucket, KMS key), or you are simply using a different role or profile than you think.

**Fix.** Confirm who you are first, then simulate the call. If the simulator allows it but AWS still denies, look at SCPs, boundaries and the resource's own policy.

```sh
aws sts get-caller-identity
aws iam simulate-principal-policy --policy-source-arn <role-or-user-arn> --action-names <service:Action> --resource-arns <resource-arn>
```

## Security token expired
Matches: `expiredtoken`, `the security token included in the request is expired`, `invalidclienttokenid`, `token has expired`

**Cause.** Temporary credentials (SSO, assumed role, session token) expired, or the access key was deleted or rotated.

**Fix.** Log in again or refresh the credentials, and check which profile is active.

```sh
aws sso login --profile <profile>
aws sts get-caller-identity --profile <profile>
```

## Unable to locate credentials
Matches: `unable to locate credentials`, `nocredentialproviders`, `no valid credential sources found`

**Cause.** No credentials were found in env vars, the config files, SSO cache or an instance or pod role.

**Fix.** Check what the CLI sees, set the profile, or attach a role to the instance or ServiceAccount.

```sh
aws configure list
echo $AWS_PROFILE
```

## Request signature expired
Matches: `signature expired`, `signaturedoesnotmatch`, `request has expired`

**Cause.** Signature expired means the machine's clock is off. SignatureDoesNotMatch usually means a wrong secret key (often a copy-paste with a stray character).

**Fix.** Sync the clock, or re-enter the secret access key.

```sh
timedatectl
aws configure
```

## Throttling: rate exceeded
Matches: `throttlingexception`, `rate exceeded`, `toomanyrequestsexception`, `requestlimitexceeded`, `slowdown`

**Cause.** Too many API calls in a short time, common with Terraform on large accounts, scripts in loops and many CI jobs sharing one account.

**Fix.** Turn on adaptive retries, add backoff, lower Terraform parallelism, and cache results instead of polling.

```sh
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10
terraform apply -parallelism=5
```

## EC2 instance unreachable
Matches: `compute.amazonaws.com`, `ec2 instance unreachable`, `instance status check failed`

**Cause.** The security group or network ACL does not allow your IP and port, the subnet's route table has no route to an internet gateway, the instance has no public IP, or a status check failed.

**Fix.** Check the instance state, public IP and security group, then the subnet's routes. Use SSM Session Manager when SSH is not an option.

```sh
aws ec2 describe-instances --instance-ids <id> --query "Reservations[].Instances[].{State:State.Name,PublicIp:PublicIpAddress,SGs:SecurityGroups}"
aws ec2 describe-security-groups --group-ids <sg-id>
aws ec2 describe-instance-status --instance-ids <id>
```

## Private subnet has no internet access
Matches: `private subnet`, `nat gateway`, `no route to the internet`

**Cause.** The private subnet's route table has no 0.0.0.0/0 route to a NAT gateway, or the NAT gateway sits in a subnet without an internet gateway route.

**Fix.** Add the default route to the NAT gateway, or use VPC endpoints for AWS services so traffic stays private.

```sh
aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=<subnet-id>
aws ec2 describe-nat-gateways
```

## S3 returns 403 AccessDenied
Matches: `getobject operation: access denied`, `putobject operation: access denied`

**Cause.** The bucket policy, Block Public Access, object ownership, or a KMS key policy denies the request, or the IAM role lacks s3 permissions on the right ARN (bucket vs bucket/*).

**Fix.** Check the bucket policy and Block Public Access, and that the role's policy covers both arn:aws:s3:::bucket and arn:aws:s3:::bucket/*. For SSE-KMS objects, the role also needs kms:Decrypt.

```sh
aws s3api get-bucket-policy --bucket <bucket>
aws s3api get-public-access-block --bucket <bucket>
aws s3api head-object --bucket <bucket> --key <key>
```

## S3 bucket name already exists
Matches: `bucketalreadyexists`, `the requested bucket name is not available`

**Cause.** Bucket names are global across all AWS accounts, and someone already has this one.

**Fix.** Use a unique name, for example with your account ID and region in it.

```sh
aws sts get-caller-identity --query Account --output text
```

## KMS access denied
Matches: `kms:decrypt`, `kms.amazonaws.com`, `accessdeniedexception`, `kms key`

**Cause.** The key policy does not allow the caller, even if their IAM policy does. KMS checks the key policy first.

**Fix.** Add the role to the key policy (or let the key policy delegate to IAM), and grant kms:Decrypt and kms:GenerateDataKey as needed.

```sh
aws kms get-key-policy --key-id <key-id> --policy-name default
```

## vCPU or service quota exceeded
Matches: `vcpulimitexceeded`, `you have requested more vcpu capacity`, `limitexceeded`, `servicequotaexceeded`, `addresslimitexceeded`

**Cause.** The account hit a service quota, for example the On-Demand vCPU limit, which is low on new accounts.

**Fix.** Check the quota and request an increase, or use smaller instances.

```sh
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A
aws service-quotas request-service-quota-increase --service-code ec2 --quota-code L-1216C47A --desired-value <value>
```

## Insufficient instance capacity
Matches: `insufficientinstancecapacity`, `we currently do not have sufficient`

**Cause.** AWS has no spare capacity of that instance type in that Availability Zone right now.

**Fix.** Try another AZ or instance type, or allow several types in the Auto Scaling group or node group.

```sh
aws ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=instance-type,Values=<type>
```

## EKS: kubectl says Unauthorized
Matches: `you must be logged in to the server (unauthorized)`, `error: you must be logged in to the server`

**Cause.** Your IAM identity is not mapped into the cluster (no access entry or aws-auth mapping), or the kubeconfig uses a different profile or role.

**Fix.** Refresh the kubeconfig with the right profile and add an access entry for your role.

```sh
aws sts get-caller-identity
aws eks update-kubeconfig --name <cluster> --region <region>
aws eks list-access-entries --cluster-name <cluster>
aws eks create-access-entry --cluster-name <cluster> --principal-arn <role-arn>
```
Tool: Amazon EKS

## EKS nodes do not join the cluster
Matches: `nodecreationfailure`, `instances failed to join the kubernetes cluster`, `node group`

**Cause.** The node role is missing AmazonEKSWorkerNodePolicy, AmazonEKS_CNI_Policy or AmazonEC2ContainerRegistryReadOnly, the nodes are in private subnets with no NAT or VPC endpoints, or the security groups block node to control plane traffic.

**Fix.** Read the node group's health issues, then fix the role policies or the subnet routing.

```sh
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup> --query "nodegroup.health"
aws iam list-attached-role-policies --role-name <node-role>
```
Tool: Amazon EKS

## EKS LoadBalancer Service stuck pending
Matches: `ensuringloadbalancer`, `could not find any suitable subnets`, `external-ip <pending>`

**Cause.** The subnets are not tagged for load balancers (kubernetes.io/role/elb for public, kubernetes.io/role/internal-elb for private), or the AWS Load Balancer Controller is missing or lacks IAM permissions.

**Fix.** Tag the subnets and check the controller's logs.

```sh
kubectl describe svc <service> -n <namespace>
aws ec2 describe-subnets --filters Name=tag:kubernetes.io/role/elb,Values=1
kubectl -n kube-system logs deploy/aws-load-balancer-controller --tail=50
```
Tool: Amazon EKS

## ALB or NLB targets unhealthy
Matches: `unhealthy targets`, `target group`, `health checks failed`, `elb 502`

**Cause.** The health check path or port is wrong, the target security group does not allow the load balancer, or the app is slow to start.

**Fix.** Read the target health reason, then fix the health check settings or the security group.

```sh
aws elbv2 describe-target-health --target-group-arn <arn>
```

## EKS pod cannot assume its IAM role (IRSA)
Matches: `webidentityerr`, `assumerolewithwebidentity`, `eks.amazonaws.com/role-arn`

**Cause.** The role's trust policy does not match the cluster's OIDC provider, namespace or ServiceAccount name, the ServiceAccount annotation is missing, or the pod started before the annotation was added.

**Fix.** Check the annotation and the trust policy's sub condition (system:serviceaccount:namespace:name), then restart the pods.

```sh
kubectl get sa <serviceaccount> -n <namespace> -o yaml
aws iam get-role --role-name <role> --query Role.AssumeRolePolicyDocument
kubectl rollout restart deploy/<deployment> -n <namespace>
```
Tool: Amazon EKS

## EKS pods cannot get an IP address
Matches: `failed to assign an ip address to container`, `insufficientfreeaddressesinsubnet`, `aws-node`

**Cause.** The VPC CNI gives each pod a real VPC IP, and the subnets ran out, or the instance type hit its ENI and IP limit.

**Fix.** Check free IPs in the subnets. Enable prefix delegation, add larger subnets, or use instance types with more ENIs.

```sh
aws ec2 describe-subnets --subnet-ids <subnet-id> --query "Subnets[].AvailableIpAddressCount"
kubectl -n kube-system logs -l k8s-app=aws-node --tail=50
kubectl -n kube-system set env daemonset aws-node ENABLE_PREFIX_DELEGATION=true
```
Tool: Amazon EKS

## Cannot connect to RDS
Matches: `rds.amazonaws.com`, `could not connect to server: connection timed out`

**Cause.** The DB security group does not allow the client's security group or IP, the instance is not publicly accessible, or the client is in a different VPC with no peering.

**Fix.** Check where the instance lives and what its security group allows. Connect from inside the VPC or through a bastion or SSM.

```sh
aws rds describe-db-instances --db-instance-identifier <id> --query "DBInstances[].[Endpoint.Address,PubliclyAccessible,VpcSecurityGroups]"
```

## Lambda task timed out
Matches: `task timed out after`, `lambda timeout`

**Cause.** The function ran past its timeout, often waiting on a network call from inside a VPC with no NAT or endpoint, or a cold start with heavy dependencies.

**Fix.** Read the logs to see where it waits. Add a NAT or VPC endpoint, raise the timeout, or move slow work out of the request path.

```sh
aws logs tail /aws/lambda/<function> --since 15m
```

## CloudFormation stack stuck in ROLLBACK
Matches: `rollback_complete`, `update_rollback_failed`, `rollback_in_progress`

**Cause.** A resource failed to create or update. A stack in ROLLBACK_COMPLETE after its first create cannot be updated and must be deleted.

**Fix.** Read the first failed event (the root cause), then delete the stack or continue the rollback.

```sh
aws cloudformation describe-stack-events --stack-name <stack> --max-items 25
aws cloudformation continue-update-rollback --stack-name <stack>
```

## ECR login fails: no basic auth credentials or expired token
Matches: `no basic auth credentials`, `authorization token has expired`, `denied: your authorization token`

**Cause.** Docker has no valid login for the registry. ECR login tokens last 12 hours, so a long-lived shell or runner loses it.

**Fix.** Log in again right before the push. In GitHub Actions, run the ECR login step in the same job as the push.

```sh
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
```
Tool: ECR

## S3 bucket name is not valid
Matches: `invalidbucketname`, `the specified bucket is not valid`

**Cause.** The name breaks S3 rules: 3 to 63 characters, lowercase letters, numbers, dots and hyphens only. terraform plan does not check this, so it fails only at apply.

**Fix.** Use a compliant name, for example project-env-accountid-region.

```sh
aws s3api head-bucket --bucket <bucket>
```
