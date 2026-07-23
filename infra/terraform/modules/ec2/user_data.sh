#!/bin/bash
set -ex

# ── System Updates ──────────────────────────────────────────
yum update -y
yum install -y docker git curl

# ── Docker ──────────────────────────────────────────────────
systemctl enable docker
systemctl start docker
usermod -a -G docker ec2-user

# ── Docker Compose ──────────────────────────────────────────
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -L "https://github.com/docker/compose/releases/download/$${COMPOSE_VERSION}/docker-compose-$$(uname -s)-$$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── Clone Repo ──────────────────────────────────────────────
cd /home/ec2-user
git clone https://github.com/your-org/kraivor.git
cd kraivor

# ── Create .env from Terraform vars ────────────────────────
cat > .env << ENVEOF
APP_ENV=${environment}
DEBUG=False
DB_HOST=${db_host}
DB_PORT=5432
DB_PASSWORD=${db_password}
REDIS_HOST=${redis_host}
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=${kafka_host}:9092
DYNAMODB_LOCAL=false
DYNAMODB_ENDPOINT=
DYNAMODB_CHAT_TABLE=kraivor-chat-messages
AWS_REGION=us-east-1
ENVEOF

# ── Pull and Start Services ─────────────────────────────────
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "✅ Kraivor deployed at $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
