from django.urls import path
from .views import product, create_review

app_name = 'product'

urlpatterns = [
  path('<slug:slug>/', product, name='product_detail'),
  path('<int:product_id>/review/create/', create_review, name='create_review'),
]