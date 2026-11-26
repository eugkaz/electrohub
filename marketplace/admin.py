
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Listing, Category, ListingImage, ListingFeature
from .forms import ListingImageForm, ListingFeatureForm 

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    form = ListingImageForm 
    extra = 1
    fields = ('image', 'display_thumbnail', 'alt_text', 'order')
    readonly_fields = ('display_thumbnail',)
    verbose_name = _("Додаткове зображення")
    verbose_name_plural = _("Додаткові зображення")
    fk_name = "listing"
    ordering = ('order', 'pk',)

    @admin.display(description=_('Попередній перегляд'))
    def display_thumbnail(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="80" height="auto" style="max-height: 80px; object-fit: cover; border-radius: 4px;" /></a>', obj.image.url)
        return _("Немає зображення")

class ListingFeatureInline(admin.TabularInline):
    model = ListingFeature
    form = ListingFeatureForm 
    extra = 1
    fields = ('name', 'value') 
    verbose_name = _("Характеристика")
    verbose_name_plural = _("Характеристики")
    fk_name = "listing"
    ordering = ('name',)

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'display_main_thumbnail', 'title', 'price_display', 'category_link',
        'user_link', 'city', 'status', 'is_active_display', 'updated_at',
    )
    list_filter = (
        'status', 'is_active_display', 'is_negotiable', 'condition',
        'currency', 'category', 'city', ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'title', 'description', 'user__username', 'user__email', 'category__name',
        'city', 'contact_info', 'brand', 'model_name', 'pk' 
    )
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'views_count', 'main_image_preview',
    )
    list_editable = ('status', 'is_active_display')
    list_per_page = 25
    ordering = ('-updated_at',)
    list_select_related = ('user', 'category')
    autocomplete_fields = ('user', 'category')

    fieldsets = (
        (None, {
            'fields': ('title', 'category', 'user', ('status', 'is_active_display')) 
        }),
        (_('Опис та Стан'), {
            'fields': ('description', ('condition', 'is_negotiable')) 
        }),
         (_('Ціна'), {
            'fields': (('price', 'currency'),)
        }),
        (_('Зображення'), {
            'fields': ('main_image', 'main_image_preview')
        }),
        (_('Контактна інформація та Розташування'), {
            'fields': ('contact_name', 'contact_info', 'city')
        }),
         (_('Додаткові деталі'), {
             'classes': ('collapse',),
             'fields': (('brand', 'model_name'), 'year_of_manufacture') 
         }),
        (_('Метадані'), {
            'classes': ('collapse',),
            'fields': ('id', ('created_at', 'updated_at'), 'views_count') 
        }),
    )
    inlines = [ListingImageInline, ListingFeatureInline]

    @admin.display(description=_('Головне фото'))
    def display_main_thumbnail(self, obj):
        if obj.main_image and hasattr(obj.main_image, 'url'):
             return format_html('<a href="{0}" target="_blank"><img src="{0}" width="70" height="auto" style="max-height: 70px; object-fit: cover; border-radius: 4px;" /></a>', obj.main_image.url)
        return "—"

    @admin.display(description=_('Перегляд гол. фото'))
    def main_image_preview(self, obj):
        if obj.main_image and hasattr(obj.main_image, 'url'):
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="250" height="auto" style="max-height: 250px; object-fit: contain; border-radius: 5px;" /></a>', obj.main_image.url)
        return _("Немає головного фото")

    @admin.display(description=_('Ціна'), ordering='price')
    def price_display(self, obj):
        if obj.price is not None:
            price_str = f"{obj.price:g}" if obj.price == int(obj.price) else f"{obj.price:,.2f}".replace(',', ' ')
            return f"{price_str} {obj.currency_symbol}"
        return "—"

    @admin.display(description=_('Категорія'), ordering='category__name')
    def category_link(self, obj):
        if obj.category:
            link = reverse("admin:marketplace_category_change", args=[obj.category.id])
            return format_html('<a href="{}">{}</a>', link, obj.category.name)
        return "—"

    @admin.display(description=_('Автор'), ordering='user__username')
    def user_link(self, obj):
        if obj.user:
            link = reverse("admin:auth_user_change", args=[obj.user.id])
            display_name = obj.user.get_full_name() or obj.user.username
            return format_html('<a href="{}">{}</a>', link, display_name)
        return "—"

    
    

    @admin.action(description=_('Активувати обрані (зробити видимими)'))
    def mark_active(self, request, queryset):
        updated_count = queryset.update(is_active_display=True, status='active')
        self.message_user(request, _('{} оголошень було активовано.').format(updated_count))

    @admin.action(description=_('Деактивувати обрані (приховати)'))
    def mark_inactive(self, request, queryset):
        updated_count = queryset.update(is_active_display=False)
        self.message_user(request, _('{} оголошень було деактивовано.').format(updated_count))

    @admin.action(description=_('Архівувати обрані'))
    def mark_archived(self, request, queryset):
        updated_count = queryset.update(status='archived', is_active_display=False)
        self.message_user(request, _('{} оголошень було переміщено в архів.').format(updated_count))

    @admin.action(description=_('Відмітити обрані як "Продано"'))
    def mark_sold(self, request, queryset):
        updated_count = queryset.update(status='sold', is_active_display=False)
        self.message_user(request, _('{} оголошень було відмічено як "Продано".').format(updated_count))

    actions = ['mark_active', 'mark_inactive', 'mark_sold', 'mark_archived']