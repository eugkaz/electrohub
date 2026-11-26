from django.urls import path
from .views import map_view, charging_stations, charging_stations_list

urlpatterns = [
    path('map/', map_view, name='map_view'),  
    path('stations/', charging_stations, name='charging_stations'),  
    path('stations_list/', charging_stations_list, name='charge_stations_list'),  
]