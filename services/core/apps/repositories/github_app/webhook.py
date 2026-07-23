"""
GitHub App webhook handler.

Handles installation events from GitHub. This is the reliable path for
syncing installation state — it fires even when the Setup URL redirect fails.

Endpoint: POST /api/github-app/webhook/
"""

import json

import hashlib
import hmac
import logging
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook signature using HMAC-SHA256."""
    secret = getattr(settings, "GITHUB_APP_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("github_app.webhook.no_secret — skipping signature check")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = (
        "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature_header)


@csrf_exempt
@require_POST
def github_app_webhook(request):
    """
    POST /api/github-app/webhook/

    Handles installation and installation_repositories events from GitHub.
    No authentication required — verified via HMAC signature.
    """
    body = request.body
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    if not _verify_signature(body, signature):
        logger.warning("github_app.webhook.invalid_signature")
        return HttpResponse(status=401)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    action = payload.get("action", "")
    installation_data = payload.get("installation", {})
    installation_id = installation_data.get("id")

    if not installation_id:
        return HttpResponse(status=200)

    logger.info(
        "github_app.webhook.received",
        extra={
            "event": event_type,
            "action": action,
            "installation_id": installation_id,
        },
    )

    if event_type == "installation" and action in (
        "created",
        "new_permissions_accepted",
    ):
        _handle_installation_created(payload, installation_id)

    elif event_type == "installation" and action == "deleted":
        _handle_installation_deleted(installation_id)

    elif event_type == "installation_repositories" and action in ("added", "removed"):
        _handle_repos_changed(installation_id)

    return HttpResponse(status=200)


def _handle_installation_created(payload: dict, installation_id: int) -> None:
    """
    Sync a new installation from webhook data.

    NOTE: Webhooks don't carry workspace context (no state parameter).
    We sync the installation record keyed on installation_id and mark it
    as workspace=None. When the callback URL fires (even late), it will
    update the workspace FK. Frontend polling will detect this and prompt.

    For the workspace association path: see GitHubAppInstallCallbackView.
    """
    from .client import GitHubAppClient, GitHubAppError
    from .models import GitHubAppInstallation
    from .services import GitHubAppInstallationService

    account = payload.get("installation", {}).get("account", {})

    try:
        client = GitHubAppClient()
        service = GitHubAppInstallationService(client=client)

        existing = GitHubAppInstallation.objects.filter(
            installation_id=installation_id, deleted_at__isnull=True
        ).first()

        if existing:
            service._sync_repos(existing)
            logger.info(
                "github_app.webhook.repos_synced",
                extra={
                    "installation_id": installation_id,
                    "workspace_id": str(existing.workspace_id),
                },
            )
        else:
            logger.info(
                "github_app.webhook.no_workspace_yet",
                extra={
                    "installation_id": installation_id,
                    "account": account.get("login", "unknown"),
                },
            )
    except GitHubAppError as exc:
        logger.error("github_app.webhook.sync_failed", extra={"error": str(exc)})


def _handle_installation_deleted(installation_id: int) -> None:
    from .client import _token_cache
    from .models import GitHubAppInstallation

    GitHubAppInstallation.objects.filter(
        installation_id=installation_id, deleted_at__isnull=True
    ).update(deleted_at=timezone.now())

    _token_cache.invalidate(installation_id)

    logger.info(
        "github_app.webhook.installation_deleted",
        extra={"installation_id": installation_id},
    )


def _handle_repos_changed(installation_id: int) -> None:
    from .models import GitHubAppInstallation
    from .services import GitHubAppInstallationService

    installation = GitHubAppInstallation.objects.filter(
        installation_id=installation_id, deleted_at__isnull=True
    ).first()

    if installation:
        try:
            GitHubAppInstallationService()._sync_repos(installation)
            logger.info(
                "github_app.webhook.repos_synced_on_change",
                extra={"installation_id": installation_id},
            )
        except Exception as exc:
            logger.error(
                "github_app.webhook.sync_failed_on_change", extra={"error": str(exc)}
            )
