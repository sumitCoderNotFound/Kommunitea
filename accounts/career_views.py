"""Favourites + Highlights viewsets (kept separate to avoid touching the large accounts/views)."""
from rest_framework import viewsets, permissions, serializers
from .models import Favourite, Highlight


class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourite
        fields = ["id", "kind", "target_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class HighlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Highlight
        fields = ["id", "title", "icon", "cover_url", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class FavouriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavouriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    filterset_fields = ["kind"]

    def get_queryset(self):
        return Favourite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # idempotent: re-favouriting the same target updates created_at instead of erroring
        Favourite.objects.filter(user=self.request.user,
                                  kind=serializer.validated_data["kind"],
                                  target_id=serializer.validated_data["target_id"]).delete()
        serializer.save(user=self.request.user)


class HighlightViewSet(viewsets.ModelViewSet):
    serializer_class = HighlightSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.query_params.get("user")
        if user_id:
            return Highlight.objects.filter(user_id=user_id)
        return Highlight.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
