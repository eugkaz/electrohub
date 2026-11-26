
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify as django_slugify
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError


try:
    from slugify import slugify as awesome_slugify
    print("Using slugify from 'python-slugify' library.")
except ImportError:
    awesome_slugify = django_slugify
    print("Using django.utils.text.slugify. Consider installing 'python-slugify[unidecode]'.")

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Назва"))
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name=_("Посилання (slug)"))

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = awesome_slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('marketplace_category_view', kwargs={'category_slug': self.slug})

    class Meta:
        verbose_name = _('Категорія')
        verbose_name_plural = _('Категорії')
        ordering = ['name']

class Listing(models.Model):
    STATUS_CHOICES = [('active', _('Активно')), ('sold', _('Продано')), ('archived', _('В архіві'))]
    CONDITION_CHOICES = [
        ('new', _('Новий')), ('used_like_new', _('Б/В - як новий')),
        ('used_good', _('Б/В - добрий стан')), ('used_fair', _('Б/В - задовільний стан')),
        ('for_parts', _('На запчастини'))
    ]
    CURRENCY_UAH = 'UAH'; CURRENCY_USD = 'USD'; CURRENCY_EUR = 'EUR'
    CURRENCY_CHOICES = [(CURRENCY_UAH, _('Гривня (UAH)')), (CURRENCY_USD, _('Долар США (USD)')), (CURRENCY_EUR, _('Євро (EUR)'))]
    CURRENCY_SYMBOLS = { CURRENCY_UAH: '₴', CURRENCY_USD: '$', CURRENCY_EUR: '€'}

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings', verbose_name=_("Автор"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=False, verbose_name=_("Категорія*"))

    title = models.CharField(max_length=200, verbose_name=_("Заголовок*"))
    description = models.TextField(verbose_name=_("Детальний опис*"))

    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Ціна*"))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=CURRENCY_UAH, verbose_name=_("Валюта"))
    is_negotiable = models.BooleanField(default=False, verbose_name=_("Можливий торг"))

    condition = models.CharField(max_length=15, choices=CONDITION_CHOICES, default='used_good', verbose_name=_("Стан*"))

    city = models.CharField(max_length=100, verbose_name=_("Місто/Регіон*"))
    contact_name = models.CharField(max_length=100, blank=True, verbose_name=_("Ім'я контактної особи"))
    contact_info = models.CharField(max_length=255, verbose_name=_("Контакт (телефон/email)*"))

    main_image = models.ImageField(upload_to='marketplace/listings/main/', blank=True, null=True, verbose_name=_("Головне зображення"))

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name=_("Статус оголошення"))
    is_active_display = models.BooleanField(default=True, db_index=True, verbose_name=_("Активне (показувати на сайті)"))

    views_count = models.PositiveIntegerField(default=0, editable=False, verbose_name=_("Перегляди"))

    year_of_manufacture = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Рік випуску"))
    brand = models.CharField(max_length=100, blank=True, verbose_name=_("Бренд/Виробник"))
    model_name = models.CharField(max_length=100, blank=True, verbose_name=_("Модель"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата створення"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата оновлення"))

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, self.currency)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('listing_detail', kwargs={'pk': self.pk})

    def get_related_listings(self, count=4):
        return Listing.objects.filter(
            category=self.category, status='active', is_active_display=True
        ).exclude(pk=self.pk).order_by('?')[:count]

    class Meta:
        ordering = ['-updated_at', '-created_at']
        verbose_name = _('Оголошення')
        verbose_name_plural = _('Оголошення')

class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, related_name="additional_images", on_delete=models.CASCADE, verbose_name=_("Оголошення"))
    image = models.ImageField(upload_to='marketplace/listings/additional/', verbose_name=_("Файл зображення"))
    alt_text = models.CharField(max_length=150, blank=True, verbose_name=_("Альтернативний текст (SEO)"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок"))

    def __str__(self):
        try: return f"Image {self.id} for {self.listing_id}"
        except: return f"Image {self.id}"

    class Meta:
        verbose_name = _('Додаткове зображення')
        verbose_name_plural = _('Додаткові зображення')
        ordering = ['order', 'pk']

class ListingFeature(models.Model):
    listing = models.ForeignKey(Listing, related_name="features", on_delete=models.CASCADE, verbose_name=_("Оголошення"))
    name = models.CharField(max_length=100, verbose_name=_("Назва характеристики"))
    value = models.CharField(max_length=255, verbose_name=_("Значення"))
    icon_svg = models.TextField(blank=True, null=True, verbose_name=_("SVG іконка (опціонально)"))

    def __str__(self):
        return f"{self.name}: {self.value} ({self.listing_id})"

    class Meta:
        verbose_name = _('Характеристика')
        verbose_name_plural = _('Характеристики')
        ordering = ['name']
        unique_together = ['listing', 'name']

class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='chat_rooms', verbose_name=_("Оголошення"))
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bought_chat_rooms', verbose_name=_("Покупець"))
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sold_chat_rooms', verbose_name=_("Продавець"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    buyer_hidden = models.BooleanField(default=False)
    seller_hidden = models.BooleanField(default=False)

    class Meta:
        unique_together = ('listing', 'buyer')
        ordering = ['-updated_at']
        verbose_name = _('Чат-кімната')
        verbose_name_plural = _('Чат-кімнати')

    def hide_for_user(self, user):
        updated_fields = []
        if user == self.buyer:
            self.buyer_hidden = True
            updated_fields.append('buyer_hidden')
        elif user == self.seller:
            self.seller_hidden = True
            updated_fields.append('seller_hidden')
        else:
            return False
        if updated_fields:
            self.save(update_fields=updated_fields)
        return True

    @property
    def is_hidden_for_buyer(self):
        return self.buyer_hidden

    @property
    def is_hidden_for_seller(self):
        return self.seller_hidden

    def __str__(self):
        return f"Chat about '{self.listing.title[:20]}' between {self.buyer.username} and {self.seller.username}"

    @property
    def room_group_name(self):
        return f'chat_{self.id}'

    def save(self, *args, **kwargs):
        if not self.seller_id and self.listing_id:
            if self.listing and hasattr(self.listing, 'user'):
                 self.seller = self.listing.user
            else:
                raise ValueError(_("Неможливо визначити продавця: оголошення або користувач оголошення не встановлені."))
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name=_("Кімната"))
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name=_("Відправник"))
    content = models.TextField(verbose_name=_("Текст повідомлення/Підпис до зображення"), blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False, verbose_name=_("Прочитано"))

    is_deleted_by_sender = models.BooleanField(default=False, verbose_name=_("Видалено відправником"))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Час видалення"))
    is_edited = models.BooleanField(default=False, verbose_name=_("Відредаговано"))
    original_content = models.TextField(blank=True, null=True, verbose_name=_("Оригінальний текст (до редагування)"))

    MESSAGE_TYPE_CHOICES = [
        ('text', _('Текст')),
        ('image', _('Зображення')),
    ]
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        verbose_name=_("Тип повідомлення")
    )
    image = models.ImageField(
        upload_to='chat_images/%Y/%m/%d/',
        null=True, blank=True,
        verbose_name=_("Прикріплене зображення")
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name = _('Повідомлення чату')
        verbose_name_plural = _('Повідомлення чатів')

    def mark_as_deleted(self, user):
        if self.sender == user:
            self.is_deleted_by_sender = True
            self.deleted_at = timezone.now()


            self.save(update_fields=['is_deleted_by_sender', 'deleted_at'])
            return True
        return False

    def edit_message(self, user, new_content):
        if self.sender == user and not self.is_deleted_by_sender:
            if not self.is_edited:
                self.original_content = self.content
            
            self.content = new_content
            self.is_edited = True
            


            self.save(update_fields=['content', 'is_edited', 'original_content'])
            return True
        return False

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        super().clean()
        if self.message_type == 'image' and not self.image:
            raise ValidationError({'image': _("Для повідомлення типу 'зображення' файл є обов'язковим.")})



    def save(self, *args, **kwargs):
        self.full_clean()
        is_new_message = self.pk is None
        super().save(*args, **kwargs)
        if is_new_message or ('update_fields' in kwargs and 'content' in kwargs['update_fields']):
            ChatRoom.objects.filter(pk=self.room_id).update(updated_at=timezone.now())