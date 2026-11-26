# administration/templatetags/admin_template_tags.py
from django import template
from django.utils.html import escape, mark_safe
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.utils.translation import gettext_lazy as _ # Для _() всередині фільтра, якщо потрібно
import datetime

register = template.Library()

@register.filter(name='get_attribute')
def get_attribute(obj, attr_config_or_name):
    if not obj:
        return ''
    
    attr_name_with_format_str = ""
    
    if isinstance(attr_config_or_name, tuple):
        # Якщо це кортеж ('field_name', 'Display Label'), беремо тільки 'field_name'
        attr_name_with_format_str = str(attr_config_or_name[0])
    elif isinstance(attr_config_or_name, str):
        attr_name_with_format_str = attr_config_or_name
    else:
        # Невідомий тип конфігурації
        return '(невірний тип конфігурації поля)'

    parts = attr_name_with_format_str.split('|')
    attr_name = parts[0]
    date_format_code = None # Використовуємо код формату, наприклад 'SHORT_DATETIME_FORMAT' або 'd.m.Y H:i'

    if len(parts) > 1 and parts[1].startswith("date:"):
        date_format_code = parts[1][5:] # Отримуємо формат після "date:"

    try:
        attr_path = attr_name.split('__') # Для доступу до полів через ForeignKey (напр. 'user__username')
        value = obj
        for part_of_path in attr_path:
            if value is None: 
                return '' # Якщо проміжний об'єкт None
            value = getattr(value, part_of_path)
        
        result = value() if callable(value) else value

        if date_format_code and isinstance(result, (datetime.date, datetime.datetime)):
            try:
                # Використовуємо стандартний форматувальник Django
                # get_format може приймати стандартні імена форматів з settings.py
                # або рядок формату Python
                return DateFormat(result).format(get_format(date_format_code) if date_format_code.isupper() else date_format_code)
            except Exception as e_date:
                # Fallback на стандартний формат, якщо кастомний не спрацював
                # logger.warning(f"Could not format date {result} with {date_format_code}: {e_date}")
                return DateFormat(result).format(get_format('DATETIME_FORMAT')) 
        
        # Для безпеки екрануємо, якщо це не format_html (тобто не mark_safe)
        # None буде перетворено на порожній рядок
        if result is None:
            return ''
        return mark_safe(result) if hasattr(result, '__html__') else escape(result)
        
    except AttributeError:
        # logger.warning(f"Attribute '{attr_name}' not found on object {type(obj)}")
        return f"(атрибут '{attr_name}' не знайдено)" 
    except Exception as e:
        # logger.error(f"Error in get_attribute filter for '{attr_name_with_format_str}' on {obj}: {e}")
        return f"(помилка: {attr_name})"

@register.filter(name='get_field_name')
def get_field_name(field_config):
    """Повертає ім'я поля з конфігурації (рядок або перший елемент кортежу)."""
    if isinstance(field_config, tuple):
        return str(field_config[0]).split('|')[0] # Беремо тільки ім'я поля до фільтра дати
    return str(field_config).split('|')[0]

@register.filter(name='get_field_display_name')
def get_field_display_name(field_config_or_name):
    """Повертає відображувану назву поля."""
    label = ""
    if isinstance(field_config_or_name, tuple):
        label = field_config_or_name[1] # Другий елемент кортежу - це мітка
    else:
        # Спроба автоматично сформувати мітку з імені поля
        raw_name = str(field_config_or_name).split('|')[0] # Беремо ім'я до фільтра
        # Видаляємо типові суфікси/префікси, що використовуються для методів
        label = raw_name.replace("get_", "").replace("_display", "").replace("_admin", "").replace("_formatted", "").replace("_html_small", "").replace("_link", "").replace("_short", "")
        label = label.replace("_", " ")
        # Робимо першу літеру великою, якщо це не абревіатура
        if label and not label.isupper():
            label = label.capitalize()
        elif not label: # Якщо після очищення нічого не залишилося, беремо оригінальне ім'я
            label = raw_name
    return label

@register.filter(name='is_tuple')
def is_tuple(value):
    return isinstance(value, tuple)

# Тег is_active_prefix залишається без змін
@register.simple_tag(takes_context=True)
def is_active_prefix(context, prefix_to_check, url_name_to_check=None):
    request = context.get('request')
    if not request or not hasattr(request, 'resolver_match') or not request.resolver_match:
        return False
    current_url_name = request.resolver_match.url_name
    if url_name_to_check and current_url_name == url_name_to_check:
        return True
    if prefix_to_check and current_url_name and current_url_name.startswith(prefix_to_check):
        return True
    return False

@register.filter(name='get_item') # <-- Убедитесь, что здесь name='get_item'
def get_item_filter_function(dictionary, key): # Имя самой функции Python может быть любым
    """
    Позволяет получить значение из словаря по ключу в шаблоне Django.
    Использование: {{ my_dictionary|get_item:my_key }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None