"""
Knowledge Space serializers — KRV-022 (Knowledge Workspace / Infinite Canvas).

Serializer contract:
  - Validate and coerce input
  - Never enforce authorization (that's permissions + service layer)
  - Never call external services (that's the service layer)
  - Output shape is the API contract — change carefully

KnowledgeSpaceListSerializer   — list responses (no canvas_data; can be large)
KnowledgeSpaceSerializer       — detail / create responses (full, with canvas_data)
KnowledgeSpaceCreateSerializer — POST input
KnowledgeSpaceUpdateSerializer — PUT input
"""

from rest_framework import serializers

from .models import KnowledgeSpace

# ─── Output Serializers ───────────────────────────────────────────────────────


class KnowledgeSpaceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.

    canvas_data is intentionally excluded: the canvas state can be arbitrarily
    large (entire infinite canvas) and is only needed when the user opens a
    specific space. Clients fetch the full representation via GET /knowledge/{id}/.

    Mirrors the WorkspaceListSerializer pattern (no members list) vs
    WorkspaceDetailSerializer (full members list).
    """

    workspace_id = serializers.UUIDField()

    class Meta:
        model = KnowledgeSpace
        fields = [
            "id",
            "workspace_id",
            "name",
            "description",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KnowledgeSpaceSerializer(serializers.ModelSerializer):
    """
    Full knowledge space representation including canvas_data.

    Returned by:
      - POST /workspaces/{id}/knowledge/    (create response)
      - GET  /knowledge/{id}/               (retrieve)
      - PUT  /knowledge/{id}/               (update response)
    """

    workspace_id = serializers.UUIDField()

    class Meta:
        model = KnowledgeSpace
        fields = [
            "id",
            "workspace_id",
            "name",
            "description",
            "canvas_data",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# ─── Input Serializers ────────────────────────────────────────────────────────


class KnowledgeSpaceCreateSerializer(serializers.Serializer):
    """
    POST /workspaces/{id}/knowledge/

    name is required — a knowledge space must have a human-readable label.
    description and canvas_data are optional at creation time; the canvas
    starts empty and fills as the team adds items.
    """

    name = serializers.CharField(
        max_length=255,
        help_text="Name for this canvas (e.g. 'Authentication System').",
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        help_text="Optional description of the canvas purpose and scope.",
    )
    canvas_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Initial canvas state. Defaults to an empty canvas ({}).",
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError("Name must not be blank.")
        return value

    def validate_canvas_data(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "canvas_data must be a JSON object, not an array or scalar."
            )
        return value


class KnowledgeSpaceUpdateSerializer(serializers.Serializer):
    """
    PUT /knowledge/{id}/

    PUT semantics: name is always required.
    description and canvas_data are optional — if absent from the request,
    the existing values are preserved. This is a practical concession for
    canvas_data which can be arbitrarily large; clients should not be
    forced to round-trip the full canvas state when only renaming a space.
    """

    name = serializers.CharField(
        max_length=255,
        help_text="Updated name for this canvas.",
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Updated description. Omit to keep the existing value.",
    )
    canvas_data = serializers.JSONField(
        required=False,
        help_text=(
            "Full canvas state replacement. Omit to keep the existing canvas. "
            "When provided, replaces the entire canvas_data atomically."
        ),
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError("Name must not be blank.")
        return value

    def validate_canvas_data(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "canvas_data must be a JSON object, not an array or scalar."
            )
        return value
