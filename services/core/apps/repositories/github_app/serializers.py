from rest_framework import serializers

from .models import GitHubAppInstallation, GitHubAppInstallationRepo


class GitHubAppInstallationRepoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubAppInstallationRepo
        fields = [
            "id",
            "github_id",
            "github_repo",
            "default_branch",
            "is_private",
            "description",
            "language",
        ]


class GitHubAppInstallationSerializer(serializers.ModelSerializer):
    repos = GitHubAppInstallationRepoSerializer(many=True, read_only=True)

    class Meta:
        model = GitHubAppInstallation
        fields = [
            "id",
            "installation_id",
            "github_account_id",
            "github_account_login",
            "github_account_type",
            "installed_by_id",
            "repositories_synced_at",
            "repos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GitHubAppInstallInitiateSerializer(serializers.Serializer):
    """
    Response serializer for the installation initiate endpoint.

    Returns GitHub App URLs for installation or reconfiguration.
    - installation_url: set when no installation_id was provided (first-time install)
    - configure_url:   set when installation_id was provided (reconfigure existing)
    """

    installation_url = serializers.URLField(
        help_text="URL to install the GitHub App (null when reconfiguring).",
        allow_null=True,
        default=None,
    )
    configure_url = serializers.URLField(
        help_text=(
            "GitHub URL to change which repos the installation can access."
            " Null when installing for the first time."
        ),
        allow_null=True,
        default=None,
    )


class InstallationRepoItemSerializer(serializers.Serializer):
    """
    Matches the shape the frontend repo picker expects.

    Same fields as the existing GitHubRepo interface so the frontend
    doesn't need to change its rendering logic.
    """

    full_name = serializers.CharField(source="github_repo")
    name = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    private = serializers.BooleanField(source="is_private")
    description = serializers.CharField(allow_null=True, allow_blank=True)
    language = serializers.CharField(allow_null=True, allow_blank=True)
    default_branch = serializers.CharField()
    updated_at = serializers.DateTimeField(allow_null=True)

    def get_name(self, obj: GitHubAppInstallationRepo) -> str:
        return (
            obj.github_repo.split("/")[-1]
            if "/" in obj.github_repo
            else obj.github_repo
        )

    def get_owner(self, obj: GitHubAppInstallationRepo) -> str:
        return obj.github_repo.split("/")[0] if "/" in obj.github_repo else ""


class GitHubAppInstallationListViewSerializer(serializers.Serializer):
    """
    Shape returned by the installations list endpoint.

    Used by frontend to show which GitHub accounts have installed the app.
    """

    installations = GitHubAppInstallationSerializer(many=True)
