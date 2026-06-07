"""
Management command to create the DynamoDB chat messages table.

Usage:
    python manage.py create_chat_table

Creates the kraivor-chat-messages table with the expected schema:
    PK: room_id (String)
    SK: message_id (String)

Optional GSI for querying by sender:
    GSI1: sender_id (PK) → created_at (SK)

Designed to work with both DynamoDB Local (dev) and real AWS DynamoDB (prod).
"""

import logging
from typing import Any

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from core.infrastructure.dynamodb import get_dynamodb

logger = logging.getLogger(__name__)

TABLE_NAME: str = ""
TABLE_SCHEMA: dict[str, Any] = {
    "TableName": "",
    "KeySchema": [
        {"AttributeName": "room_id", "KeyType": "HASH"},
        {"AttributeName": "message_id", "KeyType": "RANGE"},
    ],
    "AttributeDefinitions": [
        {"AttributeName": "room_id", "AttributeType": "S"},
        {"AttributeName": "message_id", "AttributeType": "S"},
        {"AttributeName": "sender_id", "AttributeType": "S"},
        {"AttributeName": "created_at", "AttributeType": "S"},
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "user_messages",
            "KeySchema": [
                {"AttributeName": "sender_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
    ],
    "BillingMode": "PAY_PER_REQUEST",
}


class Command(BaseCommand):
    help = f"Create the {TABLE_NAME} DynamoDB table for chat messages"

    def handle(self, *args, **options):
        table_name = settings.DYNAMODB_CHAT_TABLE
        TABLE_SCHEMA["TableName"] = table_name

        try:
            dynamodb = get_dynamodb()
            existing_tables = dynamodb.meta.client.list_tables()["TableNames"]

            if table_name in existing_tables:
                self.stdout.write(f"Table '{table_name}' already exists.")
                return

            table = dynamodb.create_table(**TABLE_SCHEMA)
            table.wait_until_exists()
            self.stdout.write(self.style.SUCCESS(f"Table '{table_name}' created successfully."))

        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ResourceInUseException":
                self.stdout.write(f"Table '{table_name}' already exists (concurrent creation).")
            else:
                self.stderr.write(self.style.ERROR(f"Failed to create table: {exc}"))
                raise
