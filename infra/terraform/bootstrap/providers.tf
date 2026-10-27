provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "eks-gitops-platform"
      ManagedBy = "terraform"
    }
  }
}