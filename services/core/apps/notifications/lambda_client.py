import json

import boto3
import logging
from botocore.config import Config
from django.conf import settings

logger = logging.getLogger(__name__)


def invoke_notification_lambda(payload: dict) -> dict | None:
    function_name = settings.AWS_LAMBDA_NOTIFICATION_FN
    if not function_name:
        logger.info(
            "lambda.disabled", extra={"reason": "AWS_LAMBDA_NOTIFICATION_FN not set"}
        )
        return None

    try:
        client = boto3.client(
            "lambda",
            region_name=settings.AWS_REGION,
            config=Config(
                retries={"max_attempts": 2, "mode": "standard"},
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps(payload, default=str),
        )
        logger.info(
            "lambda.invoked",
            extra={"function": function_name, "status_code": response["StatusCode"]},
        )
        return {"status": "invoked", "status_code": response["StatusCode"]}
    except Exception:
        logger.exception("lambda.invoke_failed", extra={"function": function_name})
        return None
