variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "ssh_key_name" {
  description = "EC2 SSH key pair name"
  type        = string
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "use_upstash_kafka" {
  description = "Use Upstash Kafka (free) instead of self-hosted"
  type        = bool
  default     = true
}

variable "upstash_host" {
  description = "Upstash Kafka bootstrap server (if use_upstash_kafka=true)"
  type        = string
  default     = ""
}
