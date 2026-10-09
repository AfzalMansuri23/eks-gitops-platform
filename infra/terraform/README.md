# Infrastructure (Terraform): Stage 2

> 🚧 Planned. Not implemented yet.

This folder will contain the Terraform code for the AWS infrastructure:

- **VPC**: public and private subnets across 2 availability zones
- **EKS**: managed Kubernetes cluster with a managed node group
- **Remote state**: S3 backend with state locking

The same Helm chart from `charts/webapp` will then be deployed to EKS.