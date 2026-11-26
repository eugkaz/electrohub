
from django.db import models
from django.contrib.auth import get_user_model
from product.models import Product 
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

class Order(models.Model):
    class PaymentChoices(models.TextChoices):
        CASH = 'cash', _('Готівка при отриманні')
        CARD = 'card', _('Картка онлайн')

    class OrderStatus(models.TextChoices):
        PENDING = 'pending', _('Очікує обробки/оплати')
        PROCESSING = 'processing', _('В обробці') 
        PAYMENT_FAILED = 'payment_failed', _('Помилка оплати')
        PAID = 'paid', _('Оплачено')
        CONFIRMED_BY_MANAGER = 'confirmed_by_manager', _('Підтверджено менеджером')
        SHIPPED = 'shipped', _('Відправлено')
        COMPLETED = 'completed', _('Завершено')
        CANCELLED = 'cancelled', _('Скасовано')
        REFUNDED = 'refunded', _('Повернено кошти')

    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Користувач"))
    first_name = models.CharField(_("Ім'я"), max_length=100)
    last_name = models.CharField(_("Прізвище"), max_length=100)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Телефон"), max_length=20)
    address = models.CharField(_("Адреса"), max_length=250)
    city = models.CharField(_("Місто"), max_length=100)
    zipcode = models.CharField(_("Поштовий індекс"), max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Оновлено"), auto_now=True)
    
    total_price = models.DecimalField(_("Загальна сума замовлення"), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(
        _("Спосіб оплати"),
        max_length=10, 
        choices=PaymentChoices.choices, 
        default=PaymentChoices.CASH
    )
    status = models.CharField(
        _("Статус замовлення"),
        max_length=30, 
        choices=OrderStatus.choices, 
        default=OrderStatus.PENDING
    )
    
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name=_("ID сесії Stripe Checkout"))
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name=_("ID Payment Intent (Stripe)"))

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _("Замовлення")
        verbose_name_plural = _("Замовлення")

    def __str__(self):
        return f"Замовлення {self.id} від {self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_order_total_cost(self):
        return self.total_price 

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name=_("Замовлення"))
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.PROTECT, verbose_name=_("Товар")) 
    price_at_purchase = models.DecimalField(_("Ціна на момент покупки"), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_("Кількість"), default=1)

    class Meta:
        verbose_name = _("Позиція замовлення")
        verbose_name_plural = _("Позиції замовлення")
        unique_together = ('order', 'product') 

    def __str__(self):
        return f"{self.quantity} x {self.product.name} у замовленні {self.order.id}"

    def get_cost(self) -> Decimal:
        return self.price_at_purchase * self.quantity