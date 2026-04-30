resource "aws_elasticache_cluster" "this" {
  cluster_id           = "kraivor-${var.environment}"
  engine               = "redis"
  engine_version       = "7"
  node_type            = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_nodes      = var.environment == "prod" ? 2 : 1
  parameter_group_name = "default.redis7"
}

variable "environment" {}
