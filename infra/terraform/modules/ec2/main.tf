variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_id" { type = string }
variable "ssh_key_name" { type = string }
variable "db_host" { type = string }
variable "db_password" { type = string sensitive = true }
variable "redis_host" { type = string }
variable "kafka_host" { type = string }
variable "allowed_ssh_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

# ── Security Group ──────────────────────────────────────────

resource "aws_security_group" "ec2" {
  name        = "kraivor-ec2-${var.environment}"
  description = "Allow HTTP, HTTPS, SSH"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "kraivor-ec2-${var.environment}" }
}

# ── EC2 Instance ────────────────────────────────────────────

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = "t2.micro"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = var.ssh_key_name
  associate_public_ip    = true

  root_block_device {
    volume_size = 30
    volume_type = "gp2"
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    db_host     = var.db_host
    db_password = var.db_password
    redis_host  = var.redis_host
    kafka_host  = var.kafka_host
    environment = var.environment
  }))

  tags = { Name = "kraivor-${var.environment}" }
}

# ── Outputs ─────────────────────────────────────────────────

output "instance_id" { value = aws_instance.app.id }
output "public_ip" { value = aws_instance.app.public_ip }
output "public_dns" { value = aws_instance.app.public_dns }
output "security_group_id" { value = aws_security_group.ec2.id }
