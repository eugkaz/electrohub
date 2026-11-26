
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Product, ProductFeature, ProductImage, Review,
    Brand, PartType, ElectricVehicleModel
)



class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1
    fields = ('name', 'value')
    verbose_name = "Характеристика"
    verbose_name_plural = "Характеристики"

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'display_thumbnail')
    readonly_fields = ('display_thumbnail',)
    verbose_name = "Додаткове зображення"
    verbose_name_plural = "Додаткові зображення"

    def display_thumbnail(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 80px; max-width: 100px;" /></a>', obj.image.url)
        return "Немає зображення"
    display_thumbnail.short_description = 'Перегляд'

class ReviewInline(admin.StackedInline):
    model = Review
    extra = 0
    fields = ('user_link', 'rating', 'text', 'is_approved', 'created_at')
    readonly_fields = ('user_link', 'rating', 'text', 'created_at')
    can_delete = True
    show_change_link = True
    verbose_name = "Відгук"
    verbose_name_plural = "Відгуки"
    ordering = ('-created_at',)

    def user_link(self, obj):
        if obj.user:
            link = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', link, obj.user.username)
        return "-"
    user_link.short_description = "Користувач"



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('indented_name', 'slug', 'parent', 'is_active', 'product_count')
    list_filter = ('parent', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('product_count',)
    list_editable = ('is_active',)
    actions = ['make_active', 'make_inactive']

    def indented_name(self, obj):
        level = 0
        k = obj.parent
        while k:
            level += 1
            k = k.parent
        indent = '    ' * level
        return format_html('{}{}', mark_safe(indent), obj.name)
    indented_name.short_description = 'Назва категорії'

    def product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    product_count.short_description = 'К-ть активних товарів'

    @admin.action(description='Зробити вибрані категорії активними')
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Зробити вибрані категорії неактивними')
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    
    list_display = (
        'display_thumbnail',
        'name_link',
        'sku',
        'category_link',
        'price',            
        'original_price',   
        
        'in_stock',
        'is_active',
        'created_at'
    )
    
    list_editable = ('price', 'original_price', 'in_stock', 'is_active')

    list_filter = (
        'is_active',
        'in_stock',
        'category',
        'brand',
        'part_type',
        ('created_at', admin.DateFieldListFilter)
    )
    search_fields = (
        'name', 'sku', 'description', 'short_description',
        'category__name', 'brand__name', 'part_type__name'
    )
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = (
        'created_at', 'updated_at',
        'thumbnail_preview', 'thumbnail',
        'get_average_rating',
    )
    inlines = [ProductFeatureInline, ProductImageInline, ReviewInline]
    list_per_page = 20
    actions = ['mark_in_stock', 'mark_out_of_stock', 'make_active', 'make_inactive']
    save_on_top = True
    list_select_related = ('category', 'brand')

    fieldsets = (
        ('Основна інформація', {
            'fields': ('is_active', 'name', 'slug', 'sku', 'short_description', 'description')
        }),
        ('Категоризація та Тип', {
            'fields': ('category', 'brand', 'part_type', 'compatible_models')
        }),
        ('Ціна та Наявність', {
            'fields': (('price', 'original_price'), ('in_stock', 'stock_quantity'))
        }),
        ('Зображення', {
            'fields': ('image', ('thumbnail', 'thumbnail_preview'))
        }),
         ('Рейтинг та Обране', {
             'classes': ('collapse',),
             'fields': ('get_average_rating', 'favorites')
         }),
        ('Метадані', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    filter_horizontal = ('compatible_models', 'favorites',)

    
    def display_thumbnail(self, obj):
        url = obj.get_thumbnail()
        if url and 'via.placeholder.com' not in url:
            edit_url = reverse('admin:product_product_change', args=[obj.pk])
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 60px; max-width: 80px;" /></a>', url, url)
        return "Немає фото"
    display_thumbnail.short_description = 'Фото'

    def thumbnail_preview(self, obj):
        url = obj.get_thumbnail()
        if url and 'via.placeholder.com' not in url:
            img_link = obj.image.url if obj.image and hasattr(obj.image, 'url') else '#'
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 150px; max-width: 200px;" /></a>', img_link, url)
        return "Немає фото / Не створена"
    thumbnail_preview.short_description = 'Перегляд мініатюри'

    def name_link(self, obj):
        link = reverse('admin:product_product_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', link, obj.name)
    name_link.short_description = 'Назва'
    name_link.admin_order_field = 'name'

    def category_link(self, obj):
        if obj.category:
            link = reverse('admin:product_category_change', args=[obj.category.pk])
            return format_html('<a href="{}">{}</a>', link, obj.category.name)
        return "-"
    category_link.short_description = 'Категорія'
    category_link.admin_order_field = 'category__name'

    
    def price_display(self, obj):
        if obj.on_sale:
            return format_html(
                '<span style="font-weight: bold;">{:.2f} ₴</span> <br>'
                '<span style="text-decoration: line-through; color: grey; font-size: 0.9em;">{:.2f} ₴</span> (-{}%)',
                obj.price, obj.original_price, obj.discount_percent
            )
        return f"{obj.price:.2f} ₴"
    price_display.short_description = 'Ціна (Знижка)'
    price_display.admin_order_field = 'price'

    
    @admin.action(description='Відмітити вибрані як "В наявності"')
    def mark_in_stock(self, request, queryset):
        queryset.update(in_stock=True)

    @admin.action(description='Відмітити вибрані як "Немає в наявності"')
    def mark_out_of_stock(self, request, queryset):
        queryset.update(in_stock=False)

    @admin.action(description='Зробити вибрані товари активними')
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Зробити вибрані товари неактивними')
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_logo')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('display_logo',)

    def display_logo(self, obj):
         if obj.logo and hasattr(obj.logo, 'url'):
             return format_html('<img src="{}" style="max-height: 40px;" />', obj.logo.url)
         return "-"
    display_logo.short_description = 'Логотип'

@admin.register(PartType)
class PartTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ElectricVehicleModel)
class ElectricVehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product_link', 'user_link', 'rating', 'is_approved', 'created_at', 'preview_text')
    list_filter = ('rating', 'is_approved', 'created_at', 'product__category')
    search_fields = ('text', 'user__username', 'product__name')
    readonly_fields = ('product', 'user', 'text', 'rating', 'created_at')
    list_editable = ('is_approved',)
    list_per_page = 30
    actions = ['approve_reviews', 'unapprove_reviews']
    date_hierarchy = 'created_at'
    list_select_related = ('product', 'user')

    def preview_text(self, obj):
        return obj.text[:70] + '...' if len(obj.text) > 70 else obj.text
    preview_text.short_description = 'Текст (початок)'

    def product_link(self, obj):
        link = reverse('admin:product_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', link, obj.product.name)
    product_link.short_description = 'Товар'

    def user_link(self, obj):
        link = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', link, obj.user.username)
    user_link.short_description = 'Користувач'

    @admin.action(description='Схвалити вибрані відгуки')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='Відхилити вибрані відгуки')
    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)