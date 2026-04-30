provider "aws" {
  region = var.aws_region
}

module "eks" {
  source = "../../modules/eks"
  cluster_name = "kraivor-prod"
  environment = "prod"
}

module "rds" {
  source = "../../modules/rds"
  environment = "prod"
}

module "elasticache" {
  source = "../../modules/elasticache"
  environment = "prod"
}

module "s3" {
  source = "../../modules/s3"
  environment = "prod"
}
