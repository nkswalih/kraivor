variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "ec2_security_group_id" { type = string }
variable "redis_auth_token" {
  type      = string
  sensitive = true
  default   = ""
}

# ── Subnet Group ────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "this" {
  name       = "kraivor-${var.environment}"
  subnet_ids = var.subnet_ids
  tags       = { Name = "kraivor-${var.environment}" }
}

# ── Security Group (ingress from EC2 on 6379) ──────────────

resource "aws_security_group" "redis" {
  name        = "kraivor-redis-${var.environment}"
  description = "Allow Redis from EC2"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.ec2_security_group_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "kraivor-redis-${var.environment}" }
}

# ── ElastiCache Cluster ────────────────────────────────────

resource "aws_elasticache_cluster" "this" {
  cluster_id           = "kraivor-${var.environment}"
  engine               = "redis"
  engine_version       = "7"
  node_type            = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_nodes      = var.environment == "prod" ? 2 : 1
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [aws_security_group.redis.id]
  port                 = 6379
  tags = { Name = "kraivor-${var.environment}" }
}

# ── Outputs ─────────────────────────────────────────────────

output "endpoint" { value = aws_elasticache_cluster.this.cache_nodes[0].address }
output "port" { value = aws_elasticache_cluster.this.cache_nodes[0].port }
output "security_group_id" { value = aws_security_group.redis.id }
