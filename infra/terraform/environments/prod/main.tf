provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source      = "../../modules/vpc"
  environment = "prod"
}

module "rds" {
  source                = "../../modules/rds"
  environment           = "prod"
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.database_subnets
  ec2_security_group_id = module.ec2.security_group_id
  db_password           = var.db_password
}

module "elasticache" {
  source                = "../../modules/elasticache"
  environment           = "prod"
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.elasticache_subnets
  ec2_security_group_id = module.ec2.security_group_id
}

module "ec2" {
  source      = "../../modules/ec2"
  environment = "prod"
  vpc_id      = module.vpc.vpc_id
  subnet_id   = module.vpc.public_subnets[0]
  ssh_key_name       = var.ssh_key_name
  db_host            = module.rds.endpoint
  db_password        = var.db_password
  redis_host         = module.elasticache.endpoint
  kafka_host         = var.use_upstash_kafka ? var.upstash_host : module.ec2.public_ip
}

# ── Outputs ─────────────────────────────────────────────────

output "ec2_public_ip" { value = module.ec2.public_ip }
output "ec2_public_dns" { value = module.ec2.public_dns }
output "rds_endpoint" { value = module.rds.endpoint }
output "redis_endpoint" { value = module.elasticache.endpoint }
output "vpc_id" { value = module.vpc.vpc_id }
