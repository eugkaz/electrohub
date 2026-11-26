from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import ElectricVehicle, VehicleReport

# --- НОВЫЙ КАСТОМНЫЙ ФИЛЬТР ---
class VehicleOwnerFilter(admin.SimpleListFilter):
    """
    Кастомный фильтр для отображения транспорта с владельцем или без.
    """
    title = _('Статус прив\'язки')
    parameter_name = 'owner_status'

    def lookups(self, request, model_admin):
        return (
            ('assigned', _('Прив\'язані до користувача')),
            ('unassigned', _('Вільні (не прив\'язані)')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'assigned':
            return queryset.filter(user__isnull=False)
        if self.value() == 'unassigned':
            return queryset.filter(user__isnull=True)
        return queryset


@admin.register(ElectricVehicle)
class ElectricVehicleAdmin(admin.ModelAdmin):
    # --- СТРУКТУРА ПОЛЕЙ НА СТРАНИЦЕ РЕДАКТИРОВАНИЯ ---
    fieldsets = (
        (_('Основна інформація'), {
            'fields': ('name', 'model', 'vehicle_type', 'user')
        }),
        (_('Ідентифікатори'), {
            'fields': ('unique_vehicle_id', 'ble_mac_address'),
        }),
        (_('Технічний стан'), {
            'fields': ('battery_capacity', 'current_charge', 'location')
        }),
        (_('Статус'), {
            'fields': ('is_connected', 'is_locked')
        }),
        (_('Дати'), {
            'fields': ('created_at', 'last_updated')
        }),
    )

    # --- ОТОБРАЖЕНИЕ В СПИСКЕ ---
    list_display = (
        'name', 'model', 'vehicle_type', 'user', 'battery_percentage', 
        'is_connected', 'is_locked', 'created_at'
    )
    list_editable = ('is_connected', 'is_locked')
    list_filter = ('vehicle_type', VehicleOwnerFilter, 'is_connected', 'is_locked', 'model')
    search_fields = ('name', 'model', 'user__username', 'unique_vehicle_id', 'ble_mac_address')
    
    # Поля, которые нельзя редактировать напрямую
    readonly_fields = ('unique_vehicle_id', 'created_at', 'last_updated', 'battery_percentage')
    
    # Для ускорения загрузки, особенно поля user
    list_select_related = ('user',)
    
    # Поля для автозаполнения (удобно при выборе пользователя)
    autocomplete_fields = ['user']

    # Кастомная колонка для отображения battery_percentage, если она вам нужна
    # У вас уже есть метод в модели, так что это просто для примера
    @admin.display(description='Заряд', ordering='current_charge')
    def battery_percentage_display(self, obj):
        return f"{obj.battery_percentage()}%"

@admin.register(VehicleReport)
class VehicleReportAdmin(admin.ModelAdmin):
    list_display = ('get_vehicle_name', 'generated_at', 'charge_at_report', 'location_at_report', 'ai_summary_preview')
    list_filter = ('generated_at', 'vehicle__vehicle_type') # Фільтруємо за типом транспорту
    search_fields = ('vehicle__name', 'vehicle__model', 'ai_summary')
    
    # Для ускорения загрузки данных о транспорте
    list_select_related = ('vehicle',) 
    
    # Делаем все поля только для чтения, т.к. отчеты не должны меняться
    readonly_fields = [f.name for f in VehicleReport._meta.fields]

    @admin.display(description='Транспорт', ordering='vehicle__name')
    def get_vehicle_name(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        # Ссылка на страницу редактирования ElectricVehicle
        url = reverse('admin:transport_electricvehicle_change', args=[obj.vehicle.pk])
        return format_html('<a href="{}">{}</a>', url, obj.vehicle)

    @admin.display(description='AI Звіт (початок)')
    def ai_summary_preview(self, obj):
        return obj.ai_summary[:80] + '...' if len(obj.ai_summary) > 80 else obj.ai_summary
    
    # Запрещаем добавление отчетов через админку, они должны создаваться автоматически
    def has_add_permission(self, request):
        return False