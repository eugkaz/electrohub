# vivasonya/asgi.py
import os
import django # Импортируем django, чтобы можно было вызвать setup()

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vivasonya.settings')

# Явно инициализируем настройки Django
django.setup() # Это ключевой момент!

# Теперь, когда Django настроен, можно импортировать остальные части
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Импортируем маршруты из вашего приложения marketplace ПОСЛЕ django.setup()
import marketplace.routing # Теперь этот импорт безопасен

# Получаем HTTP ASGI приложение
django_http_app = get_asgi_application() # Теперь это тоже безопасно

application = ProtocolTypeRouter({
    "http": django_http_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                marketplace.routing.websocket_urlpatterns
            )
        )
    ),
})