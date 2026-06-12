"""
Firebase Cloud Messaging wrapper for push notifications.

Uses firebase-admin SDK. In dev (no credentials configured), logs
notifications instead of sending them.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_sdk_initialized = False


def _reset():
    global _sdk_initialized
    _sdk_initialized = False


def _initialize():
    global _sdk_initialized
    if _sdk_initialized:
        return True

    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
    if not cred_path:
        logger.info(
            "firebase.disabled", extra={"reason": "FIREBASE_CREDENTIALS_PATH not set"}
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _sdk_initialized = True
        logger.info("firebase.initialized")
        return True
    except Exception as exc:
        logger.error("firebase.init_failed", extra={"error": str(exc)})
        return False


def send_push_notification(
    *, token: str, title: str, body: str, data: dict | None = None
) -> dict:
    if not _initialize():
        logger.info(
            "push.dev_fallback",
            extra={"token": token[:20], "title": title, "body": body},
        )
        return {"status": "dev_fallback"}

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        response = messaging.send(message)
        logger.info("push.sent", extra={"response": response})
        return {"status": "sent", "response": response}
    except Exception as exc:
        logger.error("push.failed", extra={"error": str(exc)})
        return {"status": "failed", "error": str(exc)}
