"""
Repository serializers — KRV-021 (Repository Metadata Management).

Serializer contract:
  - Validate and coerce input
  - Never enforce authorization (that's permissions + service layer)
  - Never call external services (that's the service layer)
  - Output shape is the API contract — change carefully

RepositoryConnectSerializer  — POST /workspaces/{id}/repos/  (input)
RepositorySerializer         — all response shapes            (output)
"""

import re

from rest_framework import serializers

from .models import Repository


# ─── Output Serializer ────────────────────────────────────────────────────────

class RepositorySerializer(serializers.ModelSerializer):
    """
    Full repository representation returned by list and connect responses.

    workspace_id is exposed as a top-level field (Django stores it as the FK
    column workspace_id on the model) for convenient client use without having
    to unwrap a nested workspace object.

    status reflects the soft-delete lifecycle state; active repos are "connected".
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = [
            "id",
            "workspace_id",
            "github_repo",
            "github_id",
            "default_branch",
            "language",
            "description",
            "is_private",
            "last_analyzed_at",
            "last_analysis_score",
            "indexed",
            "connected_by_id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status(self, obj: Repository) -> str:
        return "disconnected" if obj.is_deleted else "connected"


# ─── Input Serializer ─────────────────────────────────────────────────────────

class RepositoryConnectSerializer(serializers.Serializer):
    """
    POST /workspaces/{id}/repos/

    Validates the connect-repository request body.

    github_repo: target repository in "owner/repo" format.
      - Whitespace is stripped
      - Both owner and repo segments must be non-empty and contain only characters
        GitHub allows in usernames and repository names
      - Length is bounded at 255 characters total (matching model field)

    The canonical github_repo string returned by the GitHub API (stored on the
    model) may differ in case from the input — we pass the raw input to the
    service which passes it to GitHub; GitHub resolves casing and returns the
    authoritative full_name.
    """

    github_repo = serializers.CharField(
        max_length=255,
        help_text="GitHub repository in 'owner/repo' format (e.g. 'acme/api').",
    )

    # GitHub naming rules: letters, digits, hyphens, underscores, dots.
    # Owner and repo are separated by exactly one slash.
    _GITHUB_REPO_RE = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?/[a-zA-Z0-9._-]+$"
    )

    def validate_github_repo(self, value: str) -> str:
        value = value.strip()
        if not self._GITHUB_REPO_RE.match(value):
            raise serializers.ValidationError(
                "Must be in 'owner/repo' format. "
                "Both owner and repo may only contain letters, digits, hyphens, "
                "underscores, and dots (e.g. 'acme/my-api')."
            )
        return value