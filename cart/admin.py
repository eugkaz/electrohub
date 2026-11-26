from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_price', 'status', 'payment_method']
    list_filter = ['status', 'payment_method']
    search_fields = ['user__username']
    actions = ['confirm_order']

    def confirm_order(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, "Заказы успешно подтверждены")

    confirm_order.short_description = "Подтвердить выбранные заказы"