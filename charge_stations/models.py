from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
from django.conf import settings

User = get_user_model()

class ChargingStation(models.Model):
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Доступна')
        OCCUPIED = 'OCCUPIED', _('Зайнята') 
        RESERVED = 'RESERVED', _('Повністю заброньована') 
        PARTIALLY_RESERVED = 'PARTIALLY_RESERVED', _('Частково заброньована')
        OFFLINE = 'OFFLINE', _('Не в мережі')
        PLANNED = 'PLANNED', _('Планується')
        UNKNOWN = 'UNKNOWN', _('Невідомо')

    name = models.CharField(max_length=255, verbose_name=_("Назва станції"))
    address = models.TextField(verbose_name=_("Адреса"))
    location = gis_models.PointField(verbose_name=_("Розташування"), srid=4326, null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("Опис"))
    photo = models.ImageField(upload_to='station_photos/', blank=True, null=True, verbose_name=_("Фото"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("Активна"))
    is_reservable = models.BooleanField(default=False, verbose_name=_("Можна забронювати"))

    status = models.CharField(
        max_length=25,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.UNKNOWN,
        verbose_name=_("Статус доступності")
    )
    operating_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Години роботи"))
    access_type = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Тип доступу"))
    pricing = models.TextField(blank=True, null=True, verbose_name=_("Інформація про ціни"))
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Ціна за годину (грн)"))

    connections_details = models.JSONField(default=list, blank=True, null=True, verbose_name=_("Деталі конекторів"))

    data_provider = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Постачальник даних"))

    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата створення"))
    date_last_status_update = models.DateTimeField(auto_now=True, verbose_name=_("Дата останнього оновлення статусу"))

    def __str__(self):
        return self.name

    @property
    def coordinates(self):
        if self.location:
            return [self.location.y, self.location.x]
        return None

    @property
    def photo_url(self):
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        return None
        
    class Meta:
        verbose_name = _("Зарядна станція")
        verbose_name_plural = _("Зарядні станції")
        ordering = ['name']


class Booking(models.Model):
    class BookingStatus(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', _('Очікує оплати')
        CONFIRMED = 'CONFIRMED', _('Підтверджено (заброньовано)')
        ACTIVE = 'ACTIVE', _('Активне (використовується)')
        COMPLETED = 'COMPLETED', _('Завершено')
        CANCELLED_USER = 'CANCELLED_USER', _('Скасовано користувачем')
        CANCELLED_SYSTEM = 'CANCELLED_SYSTEM', _('Скасовано системою')
        EXPIRED = 'EXPIRED', _('Прострочено (не використано)')

    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='station_bookings', verbose_name=_("Станція"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_station_bookings', verbose_name=_("Користувач"))
    connector_id = models.CharField(max_length=100, blank=True, null=True, help_text=_("ID заброньованого конектора"))
    start_time = models.DateTimeField(verbose_name=_("Час початку"))
    end_time = models.DateTimeField(verbose_name=_("Час закінчення"))
    
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING_PAYMENT,
        verbose_name=_("Статус бронювання")
    )
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='UAH', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Створено"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Оновлено"))

    def __str__(self):
        return f"Бронювання {self.id} для {self.station.name} ({self.user.username})"

    class Meta:
        verbose_name = _("Бронювання станції")
        verbose_name_plural = _("Бронювання станцій")
        ordering = ['-start_time']
