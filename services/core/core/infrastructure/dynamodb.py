"""
DynamoDB client singleton for the Core Service.

Provides a shared boto3 DynamoDB resource used by apps/chat/ for
message persistence. Supports DynamoDB Local in development (no
AWS account required) and real AWS DynamoDB in production.

Usage:
    from core.infrastructure.dynamodb import get_dynamodb
    table = get_dynamodb().Table("kraivor-chat-messages")
    table.put_item(Item={...})
"""

import boto3
import logging
from botocore.config import Config as BotoConfig
from django.conf import settings

logger = logging.getLogger(__name__)

_resource = None


def get_dynamodb():
    global _resource
    if _resource is None:
        try:
            kwargs = {
                "region_name": getattr(settings, "AWS_REGION", "us-east-1"),
                "config": BotoConfig(
                    retries={"max_attempts": 3, "mode": "adaptive"},
                    connect_timeout=5,
                    read_timeout=10,
                ),
            }
            dynamodb_local = getattr(settings, "DYNAMODB_LOCAL", False)
            if dynamodb_local:
                endpoint = getattr(
                    settings, "DYNAMODB_ENDPOINT", "http://localhost:8000"
                )
                kwargs["endpoint_url"] = endpoint
                kwargs["aws_access_key_id"] = "dummy"
                kwargs["aws_secret_access_key"] = "dummy"
                logger.info("dynamodb.using_local", extra={"endpoint": endpoint})
            _resource = boto3.resource("dynamodb", **kwargs)
            logger.info("dynamodb.initialized", extra={"local": dynamodb_local})
        except Exception as exc:
            logger.error("dynamodb.init_failed", extra={"error": str(exc)})
            raise
    return _resource
