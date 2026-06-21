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

module "lambda_notifications" {
  source = "../../modules/lambda-notifications"
  environment  = "prod"
  aws_region   = var.aws_region
  ses_from_email = "noreply@kraivor.com"
}

module "sqs" {
  source              = "../../modules/sqs"
  environment         = "prod"
  lambda_function_arn = module.lambda_notifications.function_arn
}
