import os
from io import BytesIO
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils.text import slugify
from django.core.files import File
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

try:
   from PIL import Image
   pillow_available = True
except ImportError:
   Image = None
   pillow_available = False



class Brand(models.Model):
   name = models.CharField(max_length=100, unique=True, verbose_name=_("Назва бренду"))
   slug = models.SlugField(unique=True, max_length=110, blank=True)
   logo = models.ImageField(upload_to='uploads/brands/', blank=True, null=True, verbose_name=_("Логотип"))
   description = models.TextField(blank=True, null=True, verbose_name=_("Опис бренду"))

   class Meta:
       verbose_name = _("Бренд")
       verbose_name_plural = _("Бренди")
       ordering = ['name']

   def save(self, *args, **kwargs):
       if not self.slug: self.slug = slugify(self.name)[:110]
       super().save(*args, **kwargs)

   def __str__(self): return self.name

class PartType(models.Model):
   name = models.CharField(max_length=100, unique=True, verbose_name=_("Тип запчастини"))
   slug = models.SlugField(unique=True, max_length=110, blank=True)
   description = models.TextField(blank=True, null=True, verbose_name=_("Опис типу"))

   class Meta:
       verbose_name = _("Тип запчастини")
       verbose_name_plural = _("Типи запчастин")
       ordering = ['name']

   def save(self, *args, **kwargs):
       if not self.slug: self.slug = slugify(self.name)[:110]
       super().save(*args, **kwargs)

   def __str__(self): return self.name

class ElectricVehicleModel(models.Model):
   name = models.CharField(max_length=255, unique=True, verbose_name=_("Назва моделі транспорту"))
   slug = models.SlugField(unique=True, max_length=260, blank=True)

   class Meta:
       verbose_name = _("Модель електротранспорту")
       verbose_name_plural = _("Моделі електротранспорту")
       ordering = ['name']

   def save(self, *args, **kwargs):
       if not self.slug: self.slug = slugify(self.name)[:260]
       super().save(*args, **kwargs)

   def __str__(self): return self.name

class Category(models.Model):
   name = models.CharField(max_length=255, verbose_name=_("Назва категорії"))
   slug = models.SlugField(unique=True, max_length=260, help_text=_("Унікальний ідентифікатор для URL (генерується автоматично)"))
   parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL, verbose_name=_("Батьківська категорія"))
   image = models.ImageField(upload_to='uploads/categories/', blank=True, null=True, verbose_name=_("Зображення категорії"))
   description = models.TextField(blank=True, null=True, verbose_name=_("Опис категорії"))
   is_active = models.BooleanField(default=True, verbose_name=_("Активна"))

   class Meta:
       ordering = ('name',)
       verbose_name = _('Категорія')
       verbose_name_plural = _('Категорії')

   def _generate_unique_slug(self):
       if self.slug: base_slug = self.slug
       elif self.name: base_slug = slugify(self.name)
       else: base_slug = 'category'
       if not base_slug: base_slug = 'category'
       unique_slug = base_slug[:250]; counter = 1
       while Category.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
           unique_slug = f'{base_slug[:250]}-{counter}'; counter += 1
           if len(unique_slug) > 260: unique_slug = unique_slug[:260]; break
       return unique_slug

   def save(self, *args, **kwargs):
       self.slug = self._generate_unique_slug()
       super().save(*args, **kwargs)

   def get_absolute_url(self):
       return reverse('shop') + f'?category={self.slug}'

   def __str__(self):
       full_path = [self.name]; k = self.parent
       while k is not None: full_path.append(k.name); k = k.parent
       return ' -> '.join(full_path[::-1])


class Product(models.Model):
   category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT, verbose_name=_("Категорія"))
   name = models.CharField(max_length=255, db_index=True, verbose_name=_("Назва"))
   slug = models.SlugField(unique=True, max_length=260, blank=True, verbose_name=_("Slug (для URL)"), help_text=_("Генерується автоматично з назви"))
   sku = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True, verbose_name=_("Артикул"))
   description = models.TextField(blank=True, null=True, verbose_name=_("Повний опис"))
   short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Короткий опис"))
   price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name=_("Поточна ціна"))
   original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Оригінальна ціна (до знижки)"))
   in_stock = models.BooleanField(default=True, db_index=True, verbose_name=_("В наявності"))
   stock_quantity = models.PositiveIntegerField(default=0, verbose_name=_("Кількість на складі"), help_text=_("0 означає 'Немає в наявності', якщо in_stock=False"))
   image = models.ImageField(upload_to='uploads/products/', blank=True, null=True, verbose_name=_("Головне зображення"))
   thumbnail = models.ImageField(upload_to='uploads/products/thumbnails/', blank=True, null=True, editable=False, verbose_name=_("Мініатюра"))
   created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата створення"))
   updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата оновлення"))
   part_type = models.ForeignKey(PartType, null=True, blank=True, on_delete=models.SET_NULL, related_name='products', verbose_name=_("Тип запчастини"))
   brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name='products', verbose_name=_("Бренд"))
   compatible_models = models.ManyToManyField(ElectricVehicleModel, blank=True, related_name='compatible_parts', verbose_name=_("Сумісні моделі транспорту"))
   favorites = models.ManyToManyField(User, related_name='favorite_products', blank=True, verbose_name=_("В обраному у користувачів"))
   is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Активний"))

   class Meta:
       ordering = ('-created_at',)
       verbose_name = _("Товар")
       verbose_name_plural = _("Товари")
       indexes = [
           models.Index(fields=['slug']), models.Index(fields=['sku']), models.Index(fields=['name']),
           models.Index(fields=['-created_at']), models.Index(fields=['category']), models.Index(fields=['brand']),
           models.Index(fields=['is_active', 'in_stock']),
       ]

   def get_absolute_url(self): return reverse('product:product_detail', kwargs={'slug': self.slug})
   @property
   def on_sale(self): return self.original_price is not None and self.original_price > self.price
   @property
   def discount_percent(self):
       if self.on_sale:
           try: return int(round(((self.original_price - self.price) / self.original_price) * 100))
           except: return 0
       return 0
   def get_display_price(self): return f"{self.price:.2f}"
   def get_display_original_price(self): return f"{self.original_price:.2f}" if self.on_sale else None
   def get_average_rating(self):
       avg = self.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
       return round(avg, 1) if avg is not None else None
   def __str__(self): return self.name

   def _make_thumbnail(self, image_field, size=(300, 300)):
       if not pillow_available: return None
       if not image_field or not hasattr(image_field, 'path'): return None
       try:
           if not os.path.exists(image_field.path): return None
           img = Image.open(image_field.path); img = img.convert('RGB'); img.thumbnail(size, Image.Resampling.LANCZOS)
           thumb_io = BytesIO(); img.save(thumb_io, 'JPEG', quality=85); thumb_io.seek(0)
           base_name = os.path.splitext(os.path.basename(image_field.name))[0]; thumb_name = f'{base_name}_thumb.jpg'
           return File(thumb_io, name=thumb_name)
       except Exception as e: print(f"Error creating thumbnail for Product ID {self.pk}: {e}"); return None

   def get_thumbnail(self):
       placeholder_url = 'https://via.placeholder.com/300x300.jpg?text=No+Image'
       if self.thumbnail and hasattr(self.thumbnail, 'url'):
           try:
               if self.thumbnail.storage.exists(self.thumbnail.name): return self.thumbnail.url
               else: self.thumbnail = None; Product.objects.filter(pk=self.pk).update(thumbnail=None)
           except Exception as e: print(f"Error accessing thumbnail storage for product {self.pk}: {e}")
       if self.image and hasattr(self.image, 'url'):
           try:
               if not self.image.storage.exists(self.image.name): return placeholder_url
               thumbnail_file = self._make_thumbnail(self.image)
               if thumbnail_file:
                   self.thumbnail.save(thumbnail_file.name, thumbnail_file, save=False)
                   Product.objects.filter(pk=self.pk).update(thumbnail=self.thumbnail.name)
                   return self.thumbnail.url
               else: return self.image.url
           except Exception as e: print(f"Error during thumbnail gen/saving for product {self.pk}: {e}"); return self.image.url
       return placeholder_url

   def clean(self):
       super().clean()
       if self.original_price is not None and self.price >= self.original_price: raise ValidationError({'price': _('Поточна ціна зі знижкою має бути меншою за оригінальну ціну.')})
       if not self.in_stock and self.stock_quantity > 0: self.stock_quantity = 0
       elif self.in_stock and self.stock_quantity <= 0: self.in_stock = False

   def save(self, *args, **kwargs):
       if not self.slug: self.slug = self._generate_unique_slug()
       self.clean()
       super().save(*args, **kwargs)
   def _generate_unique_slug(self):
       if self.slug: base_slug = self.slug
       elif self.name: base_slug = slugify(self.name)
       else: base_slug = 'product'
       if not base_slug: base_slug = 'product'
       unique_slug = base_slug[:250]; counter = 1
       while Product.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
           unique_slug = f'{base_slug[:250]}-{counter}'; counter += 1
           if len(unique_slug) > 260: unique_slug = unique_slug[:260]; break
       return unique_slug




class ProductFeature(models.Model):
   product = models.ForeignKey(Product, related_name='features', on_delete=models.CASCADE, verbose_name=_("Товар"))
   name = models.CharField(max_length=255, verbose_name=_("Назва характеристики"))
   value = models.CharField(max_length=255, verbose_name=_("Значення"))
   class Meta: verbose_name=_("Характеристика"); verbose_name_plural=_("Характеристики"); ordering=['name']; unique_together=('product','name')
   def __str__(self): return f"{self.product.name} - {self.name}: {self.value}"

class ProductImage(models.Model):
   product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, verbose_name=_("Товар"))
   image = models.ImageField(upload_to='uploads/products/additional/', verbose_name=_("Додаткове зображення"))
   alt_text = models.CharField(max_length=255, blank=True, verbose_name=_("Альт. текст (опис)"))
   class Meta: verbose_name=_("Дод. зображення"); verbose_name_plural=_("Дод. зображення"); ordering=['id']
   def __str__(self): base_name=os.path.basename(self.image.name) if self.image else 'No Image'; return f"Image for {self.product.name} ({self.alt_text or base_name})"

class Review(models.Model):
   RATING_CHOICES = [(i, f"{i} ★") for i in range(1, 6)]
   product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE, verbose_name=_("Товар"))
   user = models.ForeignKey(User, related_name='product_reviews', on_delete=models.CASCADE, verbose_name=_("Користувач"))
   text = models.TextField(verbose_name=_("Текст відгуку"))
   rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5, verbose_name=_("Рейтинг"))
   created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата створення"))
   is_approved = models.BooleanField(default=True, verbose_name=_("Схвалено"))
   class Meta: ordering=('-created_at',); verbose_name=_("Відгук"); verbose_name_plural=_("Відгуки"); unique_together=('product','user')
   def __str__(self): return f"Відгук від {self.user.username} на {self.product.name} ({self.rating} ★)"