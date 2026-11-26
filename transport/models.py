import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class VehicleType(models.TextChoices):
    CAR = 'CAR', _('Електромобіль')
    SCOOTER = 'SCOOTER', _('Електросамокат')
    BIKE = 'BIKE', _('Електровелосипед')
    MOPED = 'MOPED', _('Електромопед')
    MONOWHEEL = 'MONOWHEEL', _('Моноколесо')
    OTHER = 'OTHER', _('Інше')

class ElectricVehicle(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="vehicles",
        verbose_name=_("Власник"),
        null=True,
        blank=True
    )
    vehicle_type = models.CharField(
        max_length=10,
        choices=VehicleType.choices,
        default=VehicleType.SCOOTER,
        verbose_name=_("Тип транспорту")
    )
    unique_vehicle_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("Унікальний ID (UUID)") # Уточнена назва
    )

    # --- НОВЕ ПОЛЕ ---
    ble_mac_address = models.CharField(
        max_length=17, # Формат MAC: XX:XX:XX:XX:XX:XX
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("BLE MAC-адрес"),
        help_text=_("Унікальний MAC-адрес Bluetooth-модуля пристрою. Можна залишити пустим.")
    )
    # --- КІНЕЦЬ НОВОГО ПОЛЯ ---

    name = models.CharField(max_length=255, verbose_name=_("Псевдонім (назва)"))
    model = models.CharField(max_length=255, verbose_name=_("Модель"))
    battery_capacity = models.FloatField(help_text=_("Максимальна ємність батареї (кВт·год)"), verbose_name=_("Ємність батареї"))
    current_charge = models.FloatField(help_text=_("Поточний заряд батареї (кВт·год)"), verbose_name=_("Поточний заряд"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Дата створення")
    )
    location = models.CharField(max_length=255, blank=True, help_text=_("Поточне місцезнаходження (текст або координати)"), verbose_name=_("Місцезнаходження"))
    is_connected = models.BooleanField(default=False, verbose_name=_("Підключено до мережі"))
    is_locked = models.BooleanField(default=False, verbose_name=_("Заблоковано"))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_("Останнє оновлення даних"))

    def battery_percentage(self):
        if not self.battery_capacity or self.battery_capacity == 0:
            return 0
        percentage = (self.current_charge / self.battery_capacity) * 100
        return round(max(0, min(percentage, 100)))

    def __str__(self):
        username = self.user.username if self.user else "Не прив'язано"
        return f"{self.get_vehicle_type_display()}: {self.name} ({self.model}) - {username}"

    class Meta:
        verbose_name = _("Електротранспорт")
        verbose_name_plural = _("Електротранспорт")
        ordering = ['-last_updated']

class VehicleReport(models.Model):
    # Ця модель залишається без змін
    vehicle = models.ForeignKey(ElectricVehicle, on_delete=models.CASCADE, related_name="reports", verbose_name=_("Транспорт"))
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата генерації"))
    ai_summary = models.TextField(blank=True, verbose_name=_("AI Звіт / Рекомендації"))
    charge_at_report = models.FloatField(null=True, blank=True, verbose_name=_("Заряд під час звіту (%)"))
    location_at_report = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Локація під час звіту"))

    def __str__(self):
        return f"Звіт для {self.vehicle.name} від {self.generated_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = _("Звіт по транспорту")
        verbose_name_plural = _("Звіти по транспорту")
        ordering = ['-generated_at']