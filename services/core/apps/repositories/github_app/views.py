"""
GitHub App installation views — APIView-based REST endpoints.

Endpoints:
  GET /api/workspaces/{workspace_pk}/repos/github/install/
      — Initiate installation (returns GitHub installation URL)

  GET /api/github-app/callback/
      — Handle GitHub's installation callback

  GET /api/workspaces/{workspace_pk}/repos/github/installations/
      — List workspace installations

  POST /api/workspaces/{workspace_pk}/repos/github/installations/{id}/refresh/
      — Refresh installation repos

  DELETE /api/workspaces/{workspace_pk}/repos/github/installations/{id}/
      — Remove installation (soft-delete)
"""

import logging
from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.views import WorkspaceContextMixin

from .client import GitHubAppAPIError, GitHubAppAuthError, GitHubAppError
from .serializers import (
    GitHubAppInstallationSerializer,
    GitHubAppInstallInitiateSerializer,
)
from .services import GitHubAppInstallationService

logger = logging.getLogger(__name__)


class GitHubAppInstallInitiateView(WorkspaceContextMixin, APIView):
    """
    GET /api/workspaces/{workspace_pk}/repos/github/install/
    GET /api/workspaces/{workspace_pk}/repos/github/install/?installation_id={id}

    Returns the GitHub App installation or reconfiguration URL.

    Without installation_id:
      First-time install URL.
      Response: { "installation_url": "https://github.com/apps/{slug}/installations/new?...",
                  "configure_url": null }

    With installation_id:
      Reconfigure URL for an existing installation.
      Response: { "installation_url": null,
                  "configure_url": "https://github.com/apps/{slug}/installations/{id}" }

    The user must be a workspace admin/owner to initiate installation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise PermissionDenied(
                "Only workspace admins and owners can manage GitHub App installations."
            )

        if not getattr(settings, "GITHUB_APP_SLUG", ""):
            raise ValidationError(
                {
                    "detail": "GitHub App integration is not configured on this server.",
                    "code": "github_app_not_configured",
                }
            )

        installation_id = request.query_params.get("installation_id")

        try:
            service = GitHubAppInstallationService()

            if installation_id:
                configure_url = service.get_configure_url(
                    installation_id=int(installation_id),
                    workspace=workspace,
                    actor_id=actor_id,
                )
                return Response(
                    GitHubAppInstallInitiateSerializer(
                        {"installation_url": None, "configure_url": configure_url}
                    ).data
                )
            else:
                installation_url = service.initiate_installation(
                    workspace=workspace, actor_id=actor_id
                )
                return Response(
                    GitHubAppInstallInitiateSerializer(
                        {"installation_url": installation_url, "configure_url": None}
                    ).data
                )
        except GitHubAppError as exc:
            raise ValidationError({"detail": str(exc)}) from exc


class GitHubAppInstallCallbackView(APIView):
    """
    GET /api/github-app/callback/

    Called by GitHub after the user completes the App installation.

    Query params: installation_id, setup_action, state

    Validates the state token, creates/updates the installation record,
    syncs accessible repos, and redirects the user back to the frontend.

    This view does NOT require authentication — the state token serves
    as the auth proof (it encodes workspace_id and user_id).
    """

    # No authentication required — state token proves intent
    permission_classes = []

    def get(self, request):
        installation_id_raw = request.query_params.get("installation_id")
        setup_action = request.query_params.get("setup_action", "install")
        state = request.query_params.get("state")

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost")

        def error_redirect(detail: str):
            return redirect(
                f"{frontend_url}/oauth/success"
                f"?github_app_install_error=1"
                f"&detail={quote(detail)}"
            )

        if not installation_id_raw:
            return error_redirect("Missing installation_id.")

        try:
            installation_id = int(installation_id_raw)
        except (ValueError, TypeError):
            return error_redirect("Invalid installation_id.")

        # Missing state is non-fatal — log it but try to process
        if not state:
            logger.warning(
                "github_app.callback.no_state",
                extra={
                    "installation_id": installation_id,
                    "note": "Setup URL may lack state param. "
                    "Webhook should have handled this.",
                },
            )
            return redirect(
                f"{frontend_url}/oauth/success"
                f"?github_app_installed=1"
                f"&installation_id={installation_id}"
                f"&no_state=1"
            )

        try:
            service = GitHubAppInstallationService()
            result = service.complete_installation(
                state=state, installation_id=installation_id, setup_action=setup_action
            )
        except GitHubAppError as exc:
            logger.error(
                "github_app.callback.error",
                extra={"error": str(exc), "installation_id": installation_id},
            )
            return error_redirect(str(exc))

        return redirect(
            f"{frontend_url}/oauth/success"
            f"?github_app_installed=1"
            f"&workspace_id={result['workspace_id']}"
            f"&installation_id={result['installation_id']}"
            f"&account={quote(result['account_login'])}"
        )


class GitHubAppInstallationImportView(WorkspaceContextMixin, APIView):
    """
    POST /api/workspaces/{workspace_pk}/repos/github/installations/import/

    Manually imports a GitHub App installation that was not captured via callback.
    Use case: Setup URL redirect failed / state expired / installation existed before
    Kraivor was configured.

    Body: { "installation_id": 12345678 }

    Admin only. Fetches installation info from GitHub API, creates/updates the DB
    record, and syncs repos immediately.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise PermissionDenied("Only workspace admins can import installations.")

        installation_id_raw = request.data.get("installation_id")
        if not installation_id_raw:
            raise ValidationError({"detail": "installation_id is required."})

        try:
            installation_id = int(installation_id_raw)
        except (ValueError, TypeError):
            raise ValidationError(
                {"detail": "installation_id must be an integer."}
            ) from None

        try:
            from .client import GitHubAppClient, GitHubAppError
            from .models import GitHubAppInstallation
            from .services import GitHubAppInstallationService

            client = GitHubAppClient()
            install_info = client.get_installation_info(installation_id)
            account = install_info.get("account", {})

            installation, created = GitHubAppInstallation.objects.update_or_create(
                installation_id=installation_id,
                defaults={
                    "workspace": workspace,
                    "github_account_id": account.get("id", 0),
                    "github_account_login": account.get("login", "unknown"),
                    "github_account_type": account.get("type", "User"),
                    "installed_by_id": actor_id,
                    "deleted_at": None,
                },
            )

            GitHubAppInstallationService()._sync_repos(installation)

            logger.info(
                "github_app.installation.imported",
                extra={
                    "installation_id": installation_id,
                    "workspace_id": str(workspace.id),
                    "created": created,
                },
            )

            return Response(
                GitHubAppInstallationSerializer(installation).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except GitHubAppError as exc:
            raise ValidationError({"detail": str(exc)}) from exc


class GitHubAppInstallationListView(WorkspaceContextMixin, APIView):
    """
    GET /api/workspaces/{workspace_pk}/repos/github/installations/

    List all GitHub App installations for the workspace.
    Any workspace member may view installations.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()
        actor_member = workspace.get_member(actor_id)
        can_admin = actor_member and actor_member.can_admin

        service = GitHubAppInstallationService()
        installations = service.list_installations(workspace)

        return Response(
            {
                "installations": GitHubAppInstallationSerializer(
                    installations, many=True
                ).data,
                "can_admin": can_admin,
            }
        )


class GitHubAppInstallationRefreshView(WorkspaceContextMixin, APIView):
    """
    POST /api/workspaces/{workspace_pk}/repos/github/installations/{id}/refresh/

    Refresh the accessible repo list for an installation.
    Admin/owner only.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_pk=None, installation_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise PermissionDenied(
                "Only workspace admins and owners can refresh installations."
            )

        try:
            service = GitHubAppInstallationService()
            installation = service.refresh_installation(int(installation_pk))
        except GitHubAppError as exc:
            raise NotFound(str(exc)) from exc
        except (GitHubAppAPIError, GitHubAppAuthError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(GitHubAppInstallationSerializer(installation).data)


class GitHubAppInstallationRemoveView(WorkspaceContextMixin, APIView):
    """
    DELETE /api/workspaces/{workspace_pk}/repos/github/installations/{id}/

    Remove a GitHub App installation from the workspace (soft-delete).
    Admin/owner only.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, workspace_pk=None, installation_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise PermissionDenied(
                "Only workspace admins and owners can remove installations."
            )

        try:
            service = GitHubAppInstallationService()
            service.remove_installation(
                installation_id=int(installation_pk), workspace=workspace
            )
        except GitHubAppError as exc:
            raise NotFound(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)
