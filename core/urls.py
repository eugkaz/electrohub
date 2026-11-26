
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView


urlpatterns = [
   path('', views.frontpage, name='frontpage'),
   path('shop/', views.shop, name='shop'),


   path('signup/', views.signup, name='signup'),
   path('login/', views.login, name='login'), 
   path('logout/', auth_views.LogoutView.as_view(), name='logout'),


   path('password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='core/password_reset_form.html',
            email_template_name='core/password_reset_email.html',
            subject_template_name='core/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done')
        ),
        name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='core/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='core/password_reset_confirm.html',
             success_url=reverse_lazy('password_reset_complete') 
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='core/password_reset_complete.html'
         ),
         name='password_reset_complete'),

   path('user/<str:username>/', views.public_user_profile, name='user_profile_view'),
   path('myaccount/', views.myaccount, name='myaccount'),
   path('myaccount/edit/', views.edit_myaccount, name='edit_myaccount'),
   path('aboutus/', views.aboutus, name='aboutus'),
   path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'), 
   path('favorites/', views.favorites, name='favorites'),
   path('favorites/preview/', views.favorites_preview, name='favorites_preview'),
   path('favorites/count/', views.favorites_count, name='favorites_count'),
   path('product/<int:product_id>/favorite/toggle/', views.toggle_favorite, name='toggle_favorite'), 
   
   path('help/', 
         TemplateView.as_view(template_name="core/static_pages/help.html"), 
         name='help'),

    path('terms/', 
         TemplateView.as_view(template_name="core/static_pages/terms.html"), 
         name='terms'),

    path('privacy/', 
         TemplateView.as_view(template_name="core/static_pages/privacy.html"), 
         name='privacy'),

    path('shipping/', 
         TemplateView.as_view(template_name="core/static_pages/shipping.html"), 
         name='shipping'),

    path('returns/', 
         TemplateView.as_view(template_name="core/static_pages/returns.html"), 
         name='returns'),

]


