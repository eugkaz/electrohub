

from rest_framework import serializers
from .models import ElectricVehicle

class ElectricVehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricVehicle
        fields = ['id', 'name', 'model', 'battery_level', 'last_location_lat', 'last_location_lon', 'last_reported']