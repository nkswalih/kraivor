variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "ec2_security_group_id" { type = string }
variable "db_username" { type = string default = "kraivor" }
variable "db_password" { type = string sensitive = true }

# ── DB Subnet Group ─────────────────────────────────────────

resource "aws_db_subnet_group" "this" {
  name       = "kraivor-${var.environment}"
  subnet_ids = var.subnet_ids
  tags       = { Name = "kraivor-${var.environment}" }
}

# ── Security Group (ingress from EC2 on 5432) ──────────────

resource "aws_security_group" "rds" {
  name        = "kraivor-rds-${var.environment}"
  description = "Allow PostgreSQL from EC2"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ec2_security_group_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "kraivor-rds-${var.environment}" }
}

# ── RDS Instance ────────────────────────────────────────────

resource "aws_db_instance" "this" {
  identifier           = "kraivor-${var.environment}"
  engine               = "postgres"
  engine_version       = "15"
  instance_class       = var.environment == "prod" ? "db.r6g.large" : "db.t3.micro"
  allocated_storage    = var.environment == "prod" ? 100 : 20
  db_name              = "kraivor"
  username             = var.db_username
  password             = var.db_password
  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible  = false
  skip_final_snapshot  = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "kraivor-${var.environment}-final" : null
  tags = { Name = "kraivor-${var.environment}" }
}

# ── Outputs ─────────────────────────────────────────────────

output "endpoint" { value = aws_db_instance.this.endpoint }
output "port" { value = aws_db_instance.this.port }
output "db_name" { value = aws_db_instance.this.db_name }
output "security_group_id" { value = aws_security_group.rds.id }
