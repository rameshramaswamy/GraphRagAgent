provider "aws" {
  region = var.region
}

# 1. VPC (Network)
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "rag-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
}

# 2. EKS Cluster (Compute)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.15.0"

  cluster_name    = "enterprise-rag-cluster"
  cluster_version = "1.27"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Worker Nodes
  eks_managed_node_groups = {
    general = {
      desired_size = 2
      min_size     = 1
      max_size     = 5

      instance_types = ["t3.xlarge"]
      capacity_type  = "ON_DEMAND"
    }
  }
}

# 3. Neo4j (Self-Hosted on K8s or use AuraDB Peering)
# For Enterprise, usually we use Neo4j Aura (SaaS). 
# Here we just output the EKS endpoint to configure kubectl.
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}