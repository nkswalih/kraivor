from rest_framework import serializers

from apps.knowledge.models import KnowledgeSpace
from apps.projects.models import Project, Task
from apps.repositories.models import Repository
from apps.notifications.models import Notification


class SearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    url = serializers.CharField()
    workspace_id = serializers.UUIDField(allow_null=True)
    relevance = serializers.FloatField()
    highlights = serializers.DictField(child=serializers.ListField(child=serializers.CharField()), default=dict)
    metadata = serializers.DictField(default=dict)
    created_at = serializers.DateTimeField(allow_null=True)


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    total_results = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = SearchResultSerializer(many=True)
    facets = serializers.DictField(child=serializers.IntegerField(), default=dict)


class KnowledgeSpaceSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeSpace
        fields = ["id", "name", "description", "workspace_id", "created_at"]


class ProjectSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "workspace_id", "status", "created_at"]


class TaskSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "description", "status", "priority", "project_id", "created_at"]


class RepositorySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ["id", "github_repo", "description", "language", "workspace_id", "created_at"]


class NotificationSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "notification_type", "workspace_id", "user_id", "created_at"]
