
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='cart'), 
    path('success/', views.success, name='success'), 
    path('cancel/', views.payment_cancel, name='payment_cancel'), 
    
    path('checkout/', views.checkout_page_view, name='checkout_page'),
    path('checkout/process/', views.process_checkout, name='checkout_process'),

    
    path('hx/menu-cart/', views.hx_menu_cart, name='hx_menu_cart'), 
    path('hx/summary-total/', views.hx_cart_summary_total, name='hx_cart_summary_total'), 

    
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update/<int:product_id>/<str:action>/', views.update_cart, name='update_cart'),
    
    
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),
]