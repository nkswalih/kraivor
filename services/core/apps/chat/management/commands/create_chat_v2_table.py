"""
Management command to create the DynamoDB Chat v2 single table.

Usage:
    python manage.py create_chat_v2_table

Creates the kraivor-chat-v2 table with schema:
  PK: room_id (String) — partition key
  SK: sort_key  (String) — type-discriminated sort key

No GSIs needed — all access patterns use PK+SK queries.
"""

from typing import Any

import logging
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from core.infrastructure.dynamodb import get_dynamodb

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create the DynamoDB table for Chat v2"

    def handle(self, *args, **options):
        table_name = settings.DYNAMODB_CHAT_V2_TABLE
        schema: dict[str, Any] = {
            "TableName": table_name,
            "KeySchema": [
                {"AttributeName": "room_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "room_id", "AttributeType": "S"},
                {"AttributeName": "sort_key", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        }

        try:
            dynamodb = get_dynamodb()
            existing_tables = dynamodb.meta.client.list_tables()["TableNames"]

            if table_name in existing_tables:
                self.stdout.write(f"Table '{table_name}' already exists.")
                return

            dynamodb.create_table(**schema)
            self.stdout.write(
                self.style.SUCCESS(f"Table '{table_name}' created successfully.")
            )

        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ResourceInUseException":
                self.stdout.write(
                    f"Table '{table_name}' already exists (concurrent creation)."
                )
            else:
                self.stderr.write(self.style.ERROR(f"Failed to create table: {exc}"))
                raise
