variable "environment" { type = string }
variable "vpc_cidr" { type = string default = "10.0.0.0/16" }

data "aws_availability_zones" "available" { state = "available" }

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
  public_cidrs  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i)]
  private_cidrs = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i + 10)]
  database_cidrs    = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i + 20)]
  elasticache_cidrs = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i + 30)]
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "kraivor-${var.environment}" }
}

# ── Internet Gateway ────────────────────────────────────────

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "kraivor-${var.environment}" }
}

# ── Public Subnets (EC2, NAT Gateway) ──────────────────────

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.this.id
  cidr_block              = local.public_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "kraivor-${var.environment}-public-${local.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = { Name = "kraivor-${var.environment}-public" }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ── NAT Gateway (single AZ — saves ~$32/mo vs 3 AZs) ───────

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "kraivor-${var.environment}-nat" }
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "kraivor-${var.environment}" }
}

# ── Private Subnets (app containers, outbound via NAT) ──────

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.this.id
  cidr_block        = local.private_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = { Name = "kraivor-${var.environment}-private-${local.azs[count.index]}" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }
  tags = { Name = "kraivor-${var.environment}-private" }
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ── Database Subnets (RDS — isolated, no internet route) ────

resource "aws_subnet" "database" {
  count             = 3
  vpc_id            = aws_vpc.this.id
  cidr_block        = local.database_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = { Name = "kraivor-${var.environment}-db-${local.azs[count.index]}" }
}

resource "aws_route_table" "database" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "kraivor-${var.environment}-db" }
}

resource "aws_route_table_association" "database" {
  count          = 3
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

# ── ElastiCache Subnets (Redis — isolated) ─────────────────

resource "aws_subnet" "elasticache" {
  count             = 3
  vpc_id            = aws_vpc.this.id
  cidr_block        = local.elasticache_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = { Name = "kraivor-${var.environment}-cache-${local.azs[count.index]}" }
}

resource "aws_route_table" "elasticache" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "kraivor-${var.environment}-cache" }
}

resource "aws_route_table_association" "elasticache" {
  count          = 3
  subnet_id      = aws_subnet.elasticache[count.index].id
  route_table_id = aws_route_table.elasticache.id
}

# ── Outputs ─────────────────────────────────────────────────

output "vpc_id" { value = aws_vpc.this.id }
output "public_subnets" { value = aws_subnet.public[*].id }
output "private_subnets" { value = aws_subnet.private[*].id }
output "database_subnets" { value = aws_subnet.database[*].id }
output "elasticache_subnets" { value = aws_subnet.elasticache[*].id }
output "nat_gateway_ip" { value = aws_eip.nat.public_ip }
