resource "aws_db_instance" "this" {
  identifier        = "kraivor-${var.environment}"
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = var.environment == "prod" ? "db.r6g.large" : "db.t3.micro"
  allocated_storage = var.environment == "prod" ? 100 : 20
  db_name           = "kraivor"
  username          = var.db_username
  password          = var.db_password
  
  skip_final_snapshot = true
}

variable "environment" {}
variable "db_username" {
  default = "kraivor"
}
variable "db_password" {}
