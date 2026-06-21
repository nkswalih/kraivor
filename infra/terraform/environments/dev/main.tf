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

module "lambda_notifications" {
  source = "../../modules/lambda-notifications"
  environment  = "dev"
  aws_region   = var.aws_region
  ses_from_email = "noreply@kraivor.com"
}

module "sqs" {
  source              = "../../modules/sqs"
  environment         = "dev"
  lambda_function_arn = module.lambda_notifications.function_arn
}
