# charge_stations/admin.py
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin # Ви використовуєте GISModelAdmin, а не OSMGeoAdmin
from django.urls import reverse
from django.utils.html import format_html, escape
from django.utils.http import urlencode # Для формування URL з параметрами
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q # Для аннотації кількості бронювань, якщо потрібно
from .models import ChargingStation, Booking
import json
import logging
# from decimal import Decimal # Не використовується тут напряму
logger = logging.getLogger(__name__)
# Визначення координат центру Одеси та бажаного зуму
ODESSA_LAT = 46.4825
ODESSA_LON = 30.7233
DEFAULT_ZOOM = 11

@admin.register(ChargingStation)
class ChargingStationAdmin(GISModelAdmin):
    """Налаштування адмін-панелі для Зарядних Станцій."""

    gis_widget_kwargs = {
        "attrs": {
            "default_lat": ODESSA_LAT,
            "default_lon": ODESSA_LON,
            "default_zoom": DEFAULT_ZOOM,
            "map_width": 800, # Ширина карти в адмінці
            "map_height": 500, # Висота карти в адмінці
        }
    }

    list_display = (
        'name',
        'address',
        'status',
        'price_per_hour_display', 
        'is_active',
        'is_reservable',
        'display_location_list', # Координати в списку
        # 'ocm_id', # ВИДАЛЕНО
        'bookings_count_link' 
    )
    list_filter = ('is_active', 'status', 'is_reservable', 'data_provider')
    search_fields = ('name', 'address', 'description') # 'ocm_id' ВИДАЛЕНО
    list_per_page = 25
    ordering = ('name',)

    readonly_fields = (
        # 'ocm_id', # ВИДАЛЕНО
        'photo_preview',
        'display_coordinates', # Координати для форми редагування
        'display_connections_details_formatted',
        'date_last_status_update', # Дата створення та оновлення статусу зазвичай readonly
        'date_created', # Додано date_created, якщо воно є в моделі
    )

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'address',
                'location', # Поле для введення на карті
                'display_coordinates' # Текстове відображення для зручності
            )
        }),
        (_('Статус и Доступ'), {
            'fields': (
                'is_active',
                'status',
                'is_reservable',
                'price_per_hour', 
                'operating_hours',
                'access_type',
                'pricing', 
                'date_last_status_update',
            )
        }),
        (_('Фото'), {
            'fields': ('photo', 'photo_preview') # photo_url - це property, не поле для редагування
        }),
        (_('Технические детали'), {
            'classes': ('collapse',), # Сховати за замовчуванням
            'fields': ('description', 'connections_details', 'display_connections_details_formatted')
        }),
        (_('Источник данных и Даты'), { # Змінено назву секції
             'fields': ('data_provider', 'date_created') # 'ocm_id' ВИДАЛЕНО, додано date_created
        }),
    )

    @admin.display(description=_('Фото'))
    def photo_preview(self, obj):
        # Ваша логіка для photo_url тут не потрібна, бо photo_url - це property
        # і зазвичай не використовується для відображення в readonly_fields, якщо є саме поле photo
        if obj.photo and hasattr(obj.photo, 'url'):
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 100px; max-width: 150px; vertical-align: middle;" /></a>',
                obj.photo.url
            )
        elif obj.photo_url: # Якщо є окреме поле photo_url (не property)
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 100px; max-width: 150px; vertical-align: middle;" /></a> (URL)',
                obj.photo_url
            )
        return _("Немає фото")

    @admin.display(description=_('Координати [Lat, Lon]'), ordering='location')
    def display_location_list(self, obj):
         if obj.location:
             # Форматуємо до 4 знаків після коми для списку
             return f"[{obj.location.y:.4f}, {obj.location.x:.4f}]"
         return _("Не вказано")

    @admin.display(description=_('Координати [Широта, Довгота]'))
    def display_coordinates(self, obj):
        if obj.location:
            return f"{obj.location.y}, {obj.location.x}" # Повні координати для форми
        return _("Не вказано")

    @admin.display(description=_('Деталі конекторів (формат.)'))
    def display_connections_details_formatted(self, obj):
         if obj.connections_details:
             try:
                 # Використовуємо ensure_ascii=False для коректного відображення кирилиці
                 formatted_json = json.dumps(obj.connections_details, indent=2, ensure_ascii=False)
                 return format_html('<pre style="white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 5px; background-color: #f8f8f8; font-size: 0.9em;">{}</pre>', formatted_json)
             except Exception as e:
                 return _("Помилка форматування JSON: {}").format(escape(str(e)))
         return _("Немає даних")

    @admin.display(description=_('Ціна за годину'), ordering='price_per_hour')
    def price_per_hour_display(self, obj):
        if obj.price_per_hour is not None:
            return f"{obj.price_per_hour} грн" # Припускаємо, що валюта грн
        return _("Не вказано")

    @admin.display(description=_('Бронювання'))
    def bookings_count_link(self, obj):
        if not obj.pk: # Об'єкт ще не збережено
             return "-"
        count = obj.bookings.count() # Рахуємо всі бронювання для цієї станції
        
        # Створюємо URL для фільтрації бронювань за цією станцією в адмінці Booking
        url = (
            reverse("admin:charge_stations_booking_changelist") # Правильний namespace для Booking
            + "?"
            + urlencode({"station__id__exact": f"{obj.id}"})
        )
        
        if count == 0:
            link_text = _("Немає бронювань")
        else:
            # Використовуємо ngettext_lazy для правильного відмінювання
            link_text = ngettext_lazy(
                "%(count)d бронювання", "%(count)d бронювань", count
            ) % {"count": count}
        return format_html('<a href="{}">{}</a>', url, link_text)
    # bookings_count_link.admin_order_field = 'booking_count_ann' # Потрібно, якщо використовуєте анотацію


    @admin.action(description=_('Активувати вибрані станції'))
    def make_active(self, request, queryset):
        updated_count = queryset.update(is_active=True)
        self.message_user(request, ngettext_lazy(
            '%(count)d станція була активована.',
            '%(count)d станцій було активовано.',
            updated_count
        ) % {'count': updated_count})

    @admin.action(description=_('Деактивувати вибрані станції'))
    def make_inactive(self, request, queryset):
        updated_count = queryset.update(is_active=False)
        self.message_user(request, ngettext_lazy(
            '%(count)d станція була деактивована.',
            '%(count)d станцій було деактивовано.',
            updated_count
        ) % {'count': updated_count})

    actions = ['make_active', 'make_inactive']

    # Якщо ви захочете сортувати за кількістю бронювань, розкоментуйте це
    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     qs = qs.annotate(booking_count_ann=Count('bookings')) # Анотуємо кількість
    #     return qs


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'station_link',
        'user_link',
        'connector_id', # Додано відображення ID порту
        'start_time',
        'end_time',
        'status_display_with_color', 
        'total_amount_display',
        'payment_intent_id_short',
        'created_at'
    )
    list_filter = (
        'status', 
        'station',
        'user',
        ('start_time', admin.DateFieldListFilter), # Фільтр по даті
        ('created_at', admin.DateFieldListFilter)
    )
    search_fields = ('station__name', 'user__username', 'user__email', 'id', 'payment_intent_id', 'connector_id')
    autocomplete_fields = ['station', 'user'] # Для зручного вибору
    list_select_related = ('station', 'user') # Оптимізація запитів
    date_hierarchy = 'start_time' # Навігація по даті
    list_per_page = 30
    ordering = ('-start_time',)

    # Поля, які не можна редагувати в адмінці (зазвичай генеруються системою)
    readonly_fields = ('created_at', 'updated_at', 'payment_intent_id', 'total_amount', 'currency') 

    fieldsets = (
        (None, {
            'fields': ('user', 'station', 'connector_id') # Додано connector_id
        }),
        (_('Час та тривалість'), {
            'fields': ('start_time', 'end_time')
        }),
        (_('Статус та Оплата'), {
            'fields': ('status', 'total_amount', 'currency', 'payment_intent_id')
        }),
        (_('Системна інформація'), {
            'fields': ('created_at', 'updated_at'), # Додано updated_at
            'classes': ('collapse',) # Сховати за замовчуванням
        }),
    )

    @admin.display(description=_('Станція'), ordering='station__name')
    def station_link(self, obj):
        if obj.station:
            link = reverse("admin:charge_stations_chargingstation_change", args=[obj.station.id])
            return format_html('<a href="{}">{}</a>', link, escape(obj.station.name))
        return "-"

    @admin.display(description=_('Користувач'), ordering='user__username')
    def user_link(self, obj):
        if obj.user:
            # Переконайтеся, що `auth` - це правильна назва додатку для моделі User
            # Зазвичай це `auth`, але може бути іншим, якщо у вас кастомна модель User в іншому додатку.
            link = reverse("admin:auth_user_change", args=[obj.user.id]) 
            return format_html('<a href="{}">{}</a>', link, escape(obj.user.get_username()))
        return "-"

    @admin.display(description=_('Сума'), ordering='total_amount')
    def total_amount_display(self, obj):
        if obj.total_amount is not None and obj.currency:
            return f"{obj.total_amount} {obj.currency.upper()}"
        return _("N/A")

    @admin.display(description=_('ID платежу (Stripe)'))
    def payment_intent_id_short(self, obj):
        if obj.payment_intent_id:
            pi_id_short = obj.payment_intent_id[:12] + "..." # Коротка версія ID
            stripe_dashboard_url = "https://dashboard.stripe.com/"
            # Визначаємо, чи це тестовий платіж за префіксом ID
            if obj.payment_intent_id.startswith("pi_test_") or obj.payment_intent_id.startswith("pi_3"): 
                 stripe_dashboard_url += "test/"
            stripe_dashboard_url += f"payments/{obj.payment_intent_id}"

            return format_html('<a href="{}" target="_blank" title="{}">{}</a>',
                               stripe_dashboard_url,
                               escape(obj.payment_intent_id), # Повний ID у title
                               escape(pi_id_short)) # Коротка версія для відображення
        return "-"

    @admin.display(description=_('Статус'), ordering='status')
    def status_display_with_color(self, obj):
        status_val = obj.status
        status_display_text = obj.get_status_display() # Отримуємо читабельний статус
        color = "black" # Колір за замовчуванням
        
        status_colors = {
            Booking.BookingStatus.CONFIRMED: "green",
            Booking.BookingStatus.PENDING_PAYMENT: "orange",
            Booking.BookingStatus.CANCELLED_USER: "red",
            Booking.BookingStatus.CANCELLED_SYSTEM: "maroon", # Темно-червоний
            Booking.BookingStatus.COMPLETED: "blue",
            Booking.BookingStatus.ACTIVE: "darkcyan",
            Booking.BookingStatus.EXPIRED: "grey",
        }
        color = status_colors.get(status_val, "black")
        
        return format_html('<strong style="color: {};">{}</strong>', color, escape(status_display_text))

    # Дії для адмінки бронювань
    @admin.action(description=_('Відмітити як Завершено'))
    def mark_completed(self, request, queryset):
        # Можна завершувати тільки активні або підтверджені бронювання
        updated_count = queryset.filter(
            Q(status=Booking.BookingStatus.CONFIRMED) | Q(status=Booking.BookingStatus.ACTIVE)
        ).update(status=Booking.BookingStatus.COMPLETED)
        
        # TODO: Після завершення, можливо, потрібно оновити статус станції/порту на AVAILABLE
        for booking in queryset.filter(pk__in=queryset.values_list('pk', flat=True)): # Отримуємо оновлені об'єкти
            if booking.status == Booking.BookingStatus.COMPLETED:
                # Логіка оновлення статусу станції (спрощена)
                station = booking.station
                # Потрібна більш складна логіка для визначення нового статусу станції
                # Наприклад, перевірити, чи є інші активні бронювання для цієї станції/портів
                # Поки що просто припускаємо, що може стати доступною
                if station.status in [ChargingStation.AvailabilityStatus.RESERVED, ChargingStation.AvailabilityStatus.PARTIALLY_RESERVED]:
                    # Тут потрібна перевірка, чи немає інших активних/підтверджених бронювань
                    # Якщо немає, то станція AVAILABLE
                    # Якщо є, то PARTIALLY_RESERVED або залишається RESERVED
                    # Це спрощення, для повноцінної логіки потрібен окремий метод оновлення статусу станції
                    pass # Поки не змінюємо статус станції автоматично тут

        self.message_user(request, ngettext_lazy(
            '%(count)d бронювання було відмічено як завершене.',
            '%(count)d бронювань було відмічено як завершені.',
            updated_count
        ) % {'count': updated_count})

    @admin.action(description=_('Скасувати бронювання (системно)'))
    def cancel_system(self, request, queryset):
        # Дозволяємо скасовувати тільки ті, що очікують оплати або підтверджені
        # Для підтверджених може знадобитися повернення коштів!
        cancellable_statuses = [
            Booking.BookingStatus.PENDING_PAYMENT, 
            Booking.BookingStatus.CONFIRMED # Обережно: скасування підтвердженого потребує повернення!
        ]
        updated_count = 0
        for booking in queryset.filter(status__in=cancellable_statuses):
            if booking.status == Booking.BookingStatus.CONFIRMED:
                # TODO: Ініціювати повернення коштів через Stripe для booking.payment_intent_id
                logger.warning(f"System cancellation of CONFIRMED booking {booking.id}. REFUND NEEDED for PI: {booking.payment_intent_id}")
                # Поки що просто змінюємо статус. У реальному додатку потрібен процес повернення.
            
            booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
            booking.save(update_fields=['status'])
            updated_count += 1
            
            # TODO: Оновити статус станції/порту, якщо бронювання скасовано
            # Логіка схожа на ту, що в mark_completed

        if updated_count > 0:
            self.message_user(request, ngettext_lazy(
                '%(count)d бронювання було скасовано системою.',
                '%(count)d бронювань було скасовано системою.',
                updated_count
            ) % {'count': updated_count})
        else:
            self.message_user(request, _("Не було обрано бронювань для скасування або вони не в потрібному статусі."), level='WARNING')


    actions = ['mark_completed', 'cancel_system']

# Для перекладу ngettext_lazy, якщо він не імпортований глобально
from django.utils.translation import ngettext_lazy