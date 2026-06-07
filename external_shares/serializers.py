from rest_framework import serializers

from .models import ExternalShare


class ExternalShareSerializer(serializers.ModelSerializer):
    # Optional helper inputs (write-only) used when creating the destination item.
    communityId = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ExternalShare
        fields = [
            "id", "source_platform", "source_url", "source_text", "source_image",
            "source_video", "title", "description", "thumbnail", "destination_type",
            "destination_id", "status", "created_at", "communityId",
        ]
        read_only_fields = ["id", "destination_id", "status", "created_at"]
