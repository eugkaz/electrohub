from django.shortcuts import render
from charge_stations.models import ChargingStation

def map_view(request):
    """Отображение карты"""
    return render(request, 'map.html')

def charging_stations(request):
    stations = ChargingStation.objects.all()
    return render(request, 'charge_stations.html', {'stations': stations})

def charging_stations_list(request):
    stations = ChargingStation.objects.filter(is_active=True)
    return render(request, 'charge_stations_list.html', {'stations': stations})