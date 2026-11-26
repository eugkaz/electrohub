from rest_framework import serializers
from .models import Listing

class ListingSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source="owner.username")  # Отображаем имя владельца

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "price", "city", "category",
            "is_active", "created_at", "owner", "owner_username"
        ]
        read_only_fields = ["id", "is_active", "created_at", "owner"]