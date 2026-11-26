from baton.autodiscover import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
    path('cart/', include('cart.urls')),
    path('admin/', admin.site.urls),
    path('baton/', include('baton.urls')),
    path('order/', include('order.urls')),
    path('api/', include('api.urls')),
    path('charge/', include('charge_stations.urls')),
    path('marketplace/', include("marketplace.urls")),
    path('forum/', include('forum.urls')),
    path('product/', include('product.urls')),
    path('transport/', include('transport.urls')),
    path('admin-panel/', include('administration.urls', namespace='administration')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
