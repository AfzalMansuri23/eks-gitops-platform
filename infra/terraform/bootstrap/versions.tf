terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    # bucket comes from -backend-config=../backend.hcl (see backend.hcl.example)
    key          = "eks-gitops-platform/bootstrap/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true
  }
}