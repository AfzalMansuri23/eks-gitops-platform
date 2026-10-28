variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "ecr_repository_name" {
  type    = string
  default = "eks-gitops-platform/api"
}

variable "github_repo" {
  type    = string
  default = "AfzalMansuri23/eks-gitops-platform"
}
variable "ecr_chart_repository_name" {
  type    = string
  default = "eks-gitops-platform/charts/webapp"
}
