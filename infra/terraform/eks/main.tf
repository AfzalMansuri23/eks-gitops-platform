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
    key          = "eks-gitops-platform/eks/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project   = "eks-gitops-platform"
      ManagedBy = "terraform"
    }
  }
}

variable "state_bucket" {
  description = "S3 bucket holding the network state (same bucket as backend.hcl)"
  type        = string
}

variable "admin_cidrs" {
  description = "CIDRs allowed to reach the public EKS API endpoint, e.g. [\"<your-ip>/32\"]. scripts/eks-up.ps1 fills in your current IP."
  type        = list(string)

  validation {
    condition     = length(var.admin_cidrs) > 0 && !contains(var.admin_cidrs, "0.0.0.0/0")
    error_message = "List at least one CIDR, and never 0.0.0.0/0: the API endpoint must not be open to the internet."
  }
}

variable "node_instance_type" {
  description = "Node instance type. The account is on the AWS free plan, which only launches free-tier-eligible types."
  type        = string
  default     = "c7i-flex.large" # 2 vCPU, 4 GiB

  validation {
    condition     = contains(["t3.small", "c7i-flex.large", "m7i-flex.large"], var.node_instance_type)
    error_message = "Use a free-tier-eligible type: t3.small, c7i-flex.large or m7i-flex.large (t3.medium is not eligible)."
  }
}

data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = {
    bucket = var.state_bucket
    key    = "eks-gitops-platform/network/terraform.tfstate"
    region = "ap-south-1"
  }
}

data "aws_iam_policy_document" "eks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "eks-gitops-platform-eks-cluster"
  assume_role_policy = data.aws_iam_policy_document.eks_assume.json
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "main" {
  name     = "eks-gitops-platform"
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = data.terraform_remote_state.vpc.outputs.private_subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = var.admin_cidrs
  }

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# Managed VPC CNI with its network policy agent on. Without it EKS accepts
# NetworkPolicy objects and silently enforces none of them.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  configuration_values        = jsonencode({ enableNetworkPolicy = "true" })
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "eks-gitops-platform-eks-node"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEKS_CNI_Policy",
    "AmazonEC2ContainerRegistryReadOnly",
  ])

  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}

# IMDSv2 only, with a hop limit of 1: the node itself can read instance
# metadata, but a pod (one network hop further) cannot reach it, so pods
# cannot borrow the node's IAM role.
resource "aws_launch_template" "node" {
  name_prefix = "eks-gitops-platform-node-"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "eks-gitops-platform-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = data.terraform_remote_state.vpc.outputs.private_subnet_ids
  instance_types  = [var.node_instance_type]

  launch_template {
    id      = aws_launch_template.node.id
    version = aws_launch_template.node.latest_version
  }

  scaling_config {
    desired_size = 2
    min_size     = 1
    max_size     = 2
  }

  depends_on = [aws_iam_role_policy_attachment.node, aws_eks_addon.vpc_cni]
}
