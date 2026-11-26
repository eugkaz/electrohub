
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChargingStationViewSet, BookingViewSet, get_route_view


booking_initiate_payment_view = BookingViewSet.as_view({'post': 'initiate_payment'})
booking_confirm_view = BookingViewSet.as_view({'post': 'confirm_booking'})
booking_list_view = BookingViewSet.as_view({'get': 'list'})
booking_detail_view = BookingViewSet.as_view({'get': 'retrieve'})


router = DefaultRouter()
router.register(r'stations', ChargingStationViewSet, basename='chargingstation')


urlpatterns = [
    path('', include(router.urls)), 
    path('route/', get_route_view, name='get_route'),


    path('bookings/initiate-payment/', booking_initiate_payment_view, name='booking-initiate-payment'),
    path('bookings/<int:pk>/confirm-booking/', booking_confirm_view, name='booking-confirm-booking'),
    

    path('bookings/', booking_list_view, name='booking-list'),
    path('bookings/<int:pk>/', booking_detail_view, name='booking-detail'),
]