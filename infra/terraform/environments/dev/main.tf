provider "aws" {
  region = var.aws_region
}

module "eks" {
  source = "../../modules/eks"
  cluster_name = "kraivor-dev"
  environment = "dev"
}

module "rds" {
  source = "../../modules/rds"
  environment = "dev"
}

module "elasticache" {
  source = "../../modules/elasticache"
  environment = "dev"
}

module "s3" {
  source = "../../modules/s3"
  environment = "dev"
}
