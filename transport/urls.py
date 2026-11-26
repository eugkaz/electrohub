from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    path('api/update/<int:vehicle_id>/', views.update_vehicle_status, name='update_vehicle_status'),

    path('', views.vehicle_list, name='vehicle_list'),
    path('connect/', views.connect_vehicle, name='connect_vehicle'),
    
    path('find-vehicle/', views.find_vehicle, name='find_vehicle'),

    path('<int:pk>/', views.vehicle_details, name='vehicle_details'),
    path('<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('<int:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),

    path('<int:pk>/toggle_lock/', views.toggle_lock, name='toggle_lock'),
    path('<int:pk>/generate_report/', views.generate_ai_report_view, name='generate_ai_report'),

    path('report/<int:report_id>/download/', views.download_report_pdf, name='download_report_pdf'),
]