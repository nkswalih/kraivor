"""
AWS Lambda handler for Kraivor notification dispatch.

Triggered asynchronously by the Django core service via InvocationType=Event.
Responsible for sending notifications through channels that don't belong in
the request path: email (SES), Slack webhooks, SMS (SNS), etc.

Payload shape:
{
    "user_id": "uuid",
    "notification_type": "workspace.invitation",
    "title": "You've been invited",
    "body": "...",
    "link": "https://...",
    "workspace_id": "uuid | null",
    "actor_id": "uuid | null"
}
"""

import json
import logging
import os
import urllib.request

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sns = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def handler(event: dict, context) -> dict:
    for record in event.get("Records", [event]):
        payload = _parse_payload(record)
        if payload is None:
            continue

        ntype = payload.get("notification_type", "")
        results = {}

        if ntype in ("workspace.invitation", "chat.mention", "system"):
            results["email"] = _send_email(payload)

        if ntype in ("analysis.completed", "analysis.failed", "system"):
            results["slack"] = _send_slack(payload)

        logger.info("lambda.dispatch.complete", extra={"type": ntype, "results": results})

    return {"statusCode": 200, "body": "ok"}


def _parse_payload(record: dict) -> dict | None:
    if "body" in record:
        try:
            return json.loads(record["body"])
        except (TypeError, ValueError):
            logger.exception("lambda.parse_failed", extra={"body": record.get("body", "")})
            return None
    return record


def _send_email(payload: dict) -> str:
    from_email = os.environ.get("SES_FROM_EMAIL", "noreply@kraivor.com")
    to_email = f"{payload['user_id']}@placeholder.com"

    try:
        ses.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": payload.get("title", "")},
                "Body": {"Text": {"Data": payload.get("body", "")}},
            },
        )
        return "sent"
    except Exception:
        logger.exception("ses.send_failed")
        return "failed"


def _send_slack(payload: dict) -> str:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return "skipped_no_webhook"

    try:
        data = json.dumps({"text": f"*{payload.get('title')}*\n{payload.get('body')}"}).encode()
        req = urllib.request.Request(webhook_url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=10)
        return "sent"
    except Exception:
        logger.exception("slack.send_failed")
        return "failed"
