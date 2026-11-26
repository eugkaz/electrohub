
from django import template
from urllib.parse import parse_qs, urlencode as urllib_parse_urlencode
from django.utils.safestring import mark_safe
from django.utils.text import slugify # Додано для можливих майбутніх фільтрів


try:

    from product.models import Category as ProductCategory, Brand as ProductBrand, Review as ProductReview
except ImportError:
    ProductCategory = None; ProductBrand = None; ProductReview = None
    print("ПОПЕРЕДЖЕННЯ: Не вдалося імпортувати моделі з 'product' у custom_filters.py")
try:
    from marketplace.models import Category as MarketplaceCategory, Listing
except ImportError:
    MarketplaceCategory = None; Listing = None
    print("ПОПЕРЕДЖЕННЯ: Не вдалося імпортувати моделі з 'marketplace' у custom_filters.py")

register = template.Library()

@register.filter(name='to_int')
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):



        return 0 


@register.filter(name='has_non_page_params')
def has_non_page_params(querydict):
    """Перевіряє, чи є у QueryDict параметри, окрім 'page'."""
    if not querydict: return False
    return any(key != 'page' for key in querydict.keys())

@register.filter(name='remove_param_value')
def remove_param_value(querydict_str, param_info):
    """Видаляє конкретне значення конкретного параметра з рядка запиту."""
    if not isinstance(querydict_str, str) or ':' not in param_info: return querydict_str
    key_to_remove, value_to_remove = param_info.split(':', 1)
    params = parse_qs(querydict_str, keep_blank_values=True)
    if key_to_remove in params:
        params[key_to_remove] = [v for v in params[key_to_remove] if v != value_to_remove]
        if not params[key_to_remove]: del params[key_to_remove]
    return urllib_parse_urlencode(params, doseq=True)

@register.filter(name='remove_param')
def remove_param(querydict_str, param_key):
    """Видаляє весь параметр (ключ та всі його значення) з рядка запиту."""
    if not isinstance(querydict_str, str): return querydict_str
    params = parse_qs(querydict_str, keep_blank_values=True)
    params.pop(param_key, None)
    return urllib_parse_urlencode(params, doseq=True)


@register.filter(name='get_filter_display_value')
def get_filter_display_value(value, key):
    """Повертає читабельне значення для фільтра."""
    display_value = value

    if key == 'category' and value and ProductCategory: # Для Магазину (використовуємо slug)
        try: cat = ProductCategory.objects.filter(slug=value).first(); display_value = cat.name if cat else value
        except: pass
    elif key == 'brand' and value and ProductBrand: # Для Магазину (використовуємо slug)
        try: brand = ProductBrand.objects.filter(slug=value).first(); display_value = brand.name if brand else value
        except: pass

    elif key == 'marketplace_category' and value and MarketplaceCategory: # Окремий ключ для Маркетплейсу (використовуємо ID)
         try: cat = MarketplaceCategory.objects.filter(id=value).first(); display_value = cat.name if cat else value
         except: pass

    elif key == 'sort':
        sort_options = {
            '-created_at': 'За замовчуванням (новіші)', 'price_asc': 'Ціна: від низької',
            'price_desc': 'Ціна: від високої', 'rating_desc': 'Рейтинг: від високого',
            'newest': 'Дата: новіші', 'oldest': 'Дата: старіші',
            'name_asc': 'Назва: А-Я', 'name_desc': 'Назва: Я-А',

            'marketplace_default': 'За замовчуванням (новіші оголошення)',
            'marketplace_price_asc': 'Ціна: від низької (оголошення)',
            'marketplace_price_desc': 'Ціна: від високої (оголошення)',
        }
        display_value = sort_options.get(value, value)

    elif key == 'condition' and Listing: # Використовуємо модель Listing для отримання choices
        try: display_value = dict(Listing.CONDITION_CHOICES).get(value, value)
        except: pass # На випадок, якщо Listing не імпортовано

    return display_value

@register.filter(name='get_brand_name_by_slug')
def get_brand_name_by_slug(slug):
    if not slug or not ProductBrand: return slug
    try: brand = ProductBrand.objects.filter(slug=slug).first(); return brand.name if brand else slug
    except: return slug

@register.filter(name='get_marketplace_category_name_by_id')
def get_marketplace_category_name_by_id(category_id):
    """Отримує назву категорії маркетплейсу за її ID."""
    if not category_id or not MarketplaceCategory: return category_id
    try: cat = MarketplaceCategory.objects.filter(id=category_id).first(); return cat.name if cat else category_id
    except: return category_id



@register.filter(name='get_item')
def get_item(container, key):
    if isinstance(container, dict): return container.get(key)
    try: return key in container
    except TypeError: return None

@register.filter(name='widget_type')
def widget_type(field):
    from django.forms import CheckboxInput, Textarea, Select, FileInput, RadioSelect, CheckboxSelectMultiple, SelectMultiple
    widget = field.field.widget; # ... (решта коду без змін) ...
    if isinstance(widget, Textarea): return 'textarea'
    if isinstance(widget, CheckboxInput): return 'checkbox'
    if isinstance(widget, RadioSelect): return 'radio'
    if isinstance(widget, CheckboxSelectMultiple): return 'checkbox-multiple'
    if isinstance(widget, SelectMultiple): return 'select-multiple'
    if isinstance(widget, Select): return 'select'
    if isinstance(widget, FileInput): return 'file'
    return getattr(widget, 'input_type', 'text')


@register.simple_tag(takes_context=True, name='query_params')
def query_params_tag(context, **kwargs):
    request = context.get('request')
    if not request: return ""
    updated_params = request.GET.copy(); has_changed_non_page = False
    for key, value in kwargs.items():
        if key != 'page':
            current_value_list = updated_params.getlist(key)
            new_value_str = str(value) if value is not None else None
            if new_value_str is None and key in updated_params: has_changed_non_page = True; break
            elif new_value_str is not None and (key not in updated_params or [new_value_str] != current_value_list): has_changed_non_page = True; break
            elif isinstance(value, (list, tuple)) and sorted([str(v) for v in value]) != sorted(current_value_list): has_changed_non_page = True; break
    if has_changed_non_page: updated_params.pop('page', None)
    for key, value in kwargs.items():
        if value is None or str(value) == '': updated_params.pop(key, None)
        elif isinstance(value, (list, tuple)):
             updated_params.setlist(key, [str(v) for v in value if v is not None and str(v) != ''])
             if not updated_params.getlist(key): updated_params.pop(key, None)
        else: updated_params[key] = str(value)
    if not updated_params: return ""
    return "?" + urllib_parse_urlencode(updated_params, doseq=True)


@register.simple_tag
def user_has_reviewed(product, user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated: return False
    if not product or not ProductReview: print(f"ПОМИЛКА в тезі user_has_reviewed: ..."); return False
    try: return ProductReview.objects.filter(product_id=product.id, user_id=user.id).exists()
    except Exception as e: print(f"Помилка перевірки відгуку: {e}"); return False