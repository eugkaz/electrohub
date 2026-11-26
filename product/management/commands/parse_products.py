# product/management/commands/parse_products.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
from decimal import Decimal, InvalidOperation
import hashlib
import re
import traceback # Для детальной отладки ошибок

# Django imports
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.db import transaction, IntegrityError
from django.conf import settings

# Models
try:
    from product.models import (
        Category, Product, ProductImage, ProductFeature,
        ElectricVehicleModel, PartType, Brand
    )
except ImportError as e:
    print(f"[ERROR] Не удалось импортировать модели Django: {e}")
    print("Убедитесь, что вы запускаете команду в окружении Django и модели существуют.")
    # Заглушки для возможности запуска вне Django (для тестов)
    class MockModelManager:
        def get_or_create(self, *args, **kwargs): return MockModel(), True
        def filter(self, *args, **kwargs): return self
        def delete(self): pass
        def clear(self): pass
        def add(self, *args): pass
        def set(self, *args): pass # Mock set() for M2M
        def bulk_create(self, *args, **kwargs): pass
    class MockModel:
        objects = MockModelManager()
        compatible_models = MockModelManager() # Mock M2M manager
        image = None # Mock ImageField
        def save(self, *args, **kwargs): pass
        def delete(self, *args, **kwargs): pass
        def __init__(self, **kwargs):
             for k, v in kwargs.items():
                 setattr(self, k, v)
    Category, Product, ProductImage, ProductFeature, ElectricVehicleModel, PartType, Brand = (MockModel,) * 7


try:
    from PIL import Image
except ImportError:
    Image = None
    print("[WARNING] Pillow не установлен. Обработка изображений ограничена.")

# --- Конфигурация парсера ---
BASE_URL = 'https://umservice.com.ua'

# --- ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ ---
# Селектор для блока (карточки) каждого товара в списке
PRODUCT_LIST_SELECTOR = 'div.products__item.js-product'
# Селектор для ссылки на страницу товара ВНУТРИ карточки товара
PRODUCT_LINK_SELECTOR = 'div.product-preview__name a.product-preview__link'
# Селектор для кнопки "Следующая страница"
PRODUCT_NEXT_PAGE_SELECTOR = 'a.js-page-next'
# --- КОНЕЦ ИСПРАВЛЕННЫХ СЕЛЕКТОРОВ ---

# Селекторы страницы товара (остаются как были)
PRODUCT_NAME_SELECTOR = 'h1.product__title' # На странице товара, а не в списке
PRODUCT_SKU_SELECTOR = 'div.product__article'
PRODUCT_PRICE_SELECTOR = 'div.product__price'
PRODUCT_AVAILABILITY_SELECTOR = 'div.product__available'
PRODUCT_DESCRIPTION_SELECTOR = 'div.product__description'
PRODUCT_FEATURES_SELECTOR = 'div.product__props li.prop__item'
PRODUCT_FEATURE_NAME_SELECTOR = 'span.prop__name'
PRODUCT_FEATURE_VALUE_SELECTOR = 'span.prop__value'
PRODUCT_IMAGES_SELECTOR = 'div.product__images img' # Для детальной страницы товара

# Настройки
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'uk-UA,uk;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6',
}
REQUEST_DELAY = 1.5 # Задержка между запросами в секундах
MAX_RETRIES = 3

# --- Вспомогательные функции ---
def get_soup(url, retry=0):
    """Загружает и парсит HTML-страницу."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == 'iso-8859-1':
            response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        time.sleep(REQUEST_DELAY)
        return soup
    except requests.exceptions.Timeout:
        if retry < MAX_RETRIES:
             print(f"[WARNING] Таймаут при запросе {url}. Повторная попытка ({retry+1}/{MAX_RETRIES})...")
             time.sleep(REQUEST_DELAY * (retry + 2))
             return get_soup(url, retry + 1)
        print(f"[ERROR] Не удалось получить {url} из-за таймаута после {MAX_RETRIES} попыток.")
        return None
    except requests.exceptions.RequestException as e:
        if retry < MAX_RETRIES:
            print(f"[WARNING] Ошибка сети при запросе {url}: {str(e)}. Повторная попытка ({retry+1}/{MAX_RETRIES})...")
            time.sleep(REQUEST_DELAY * (retry + 2))
            return get_soup(url, retry + 1)
        print(f"[ERROR] Не удалось получить {url} после {MAX_RETRIES} попыток: {str(e)}")
        return None
    except Exception as e:
        print(f"[ERROR] Неожиданная ошибка при обработке {url}: {str(e)}")
        traceback.print_exc()
        return None

def clean_text(text):
    """Удаляет лишние пробелы и переносы строк."""
    return re.sub(r'\s+', ' ', text).strip() if text else ''

def clean_price(price_str):
    """Извлекает числовое значение цены из строки."""
    if not price_str: return 0
    try:
        # Удаляем все нецифровые символы, кроме точки и запятой
        cleaned = ''.join(c for c in price_str if c.isdigit() or c in ['.', ','])
        # Заменяем запятую на точку для Decimal
        cleaned = cleaned.replace(',', '.')
        # Убираем пробелы, если они попали (хотя предыдущий шаг должен был их убрать)
        cleaned = cleaned.replace(' ', '')
        # Преобразуем в Decimal, берем целую часть и затем в int
        return int(Decimal(cleaned).to_integral_value(rounding='ROUND_DOWN'))
    except (InvalidOperation, ValueError, TypeError) as e:
        print(f"[WARNING] Не удалось распознать цену из '{price_str}': {e}")
        return 0
# --- Конец вспомогательных функций ---


# --- Основной класс парсера ---
class Command(BaseCommand):
    help = 'Парсер товаров с сайта umservice.com.ua с заполнением всех полей Product'

    def add_arguments(self, parser):
        parser.add_argument('--start-category', required=True,
                          help='URL стартовой категории для парсинга (например, https://umservice.com.ua/catalog/zapchasti-dlya-elektrotransporta)')
        parser.add_argument('--update-existing', action='store_true',
                          help='Обновить информацию для уже существующих товаров (найденных по SKU)')
        parser.add_argument('--skip-images', action='store_true',
                          help='Не загружать изображения товаров')
        parser.add_argument('--max-pages', type=int, default=0,
                          help='Максимальное количество страниц для парсинга в категории (0 - без ограничений)')
        parser.add_argument('--max-products', type=int, default=0,
                          help='Максимальное общее количество товаров для парсинга (0 - без ограничений)')

    def handle(self, *args, **options):
        self.config = {
            'start_url': options['start_category'],
            'update_existing': options['update_existing'],
            'skip_images': options['skip_images'],
            'max_pages': options['max_pages'] if options['max_pages'] > 0 else float('inf'),
            'max_products': options['max_products'] if options['max_products'] > 0 else float('inf'),
            'processed_products': 0,
            'processed_pages': 0
        }
        if not urlparse(self.config['start_url']).scheme in ['http', 'https']:
            self.stderr.write(self.style.ERROR("Ошибка: --start-category должен быть полным URL (например, https://...)"))
            return

        self.stdout.write(self.style.SUCCESS("=== Запуск парсера ==="))
        self.stdout.write(f"Стартовая категория: {self.config['start_url']}")
        self.stdout.write(f"Обновлять существующие: {'Да' if self.config['update_existing'] else 'Нет'}")
        self.stdout.write(f"Пропускать изображения: {'Да' if self.config['skip_images'] else 'Нет'}")
        self.stdout.write(f"Максимум страниц: {'Без ограничений' if self.config['max_pages'] == float('inf') else self.config['max_pages']}")
        self.stdout.write(f"Максимум товаров: {'Без ограничений' if self.config['max_products'] == float('inf') else self.config['max_products']}")

        try:
            self.parse_category(self.config['start_url'])
            self.stdout.write(self.style.SUCCESS(f"\n=== Парсинг завершен. Обработано товаров: {self.config['processed_products']} ==="))
        except KeyboardInterrupt:
             self.stdout.write(self.style.WARNING("\n=== Парсинг прерван пользователем ==="))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'\nКритическая ошибка во время парсинга: {str(e)}'))
            traceback.print_exc()
            raise CommandError(f'Парсинг прерван из-за ошибки: {str(e)}')


    def parse_category(self, category_url):
        """Парсит товары из указанной категории, включая пагинацию."""
        self.stdout.write(f"\n=== Начало парсинга категории: {category_url} ===")
        current_url = category_url
        self.config['processed_pages'] = 0
        category_obj = None

        while current_url and self.config['processed_pages'] < self.config['max_pages']:
            if self.config['processed_products'] >= self.config['max_products']:
                self.stdout.write(self.style.WARNING("\nДостигнут лимит максимального количества товаров."))
                break

            self.config['processed_pages'] += 1
            self.stdout.write(f"\n--- Обработка страницы {self.config['processed_pages']}: {current_url} ---")

            soup = get_soup(current_url)
            if not soup:
                self.stdout.write(self.style.ERROR(f"Не удалось загрузить страницу категории: {current_url}. Пропуск."))
                break # Прерываем для этой категории

            # Определяем категорию на первой странице
            if category_obj is None:
                category_obj = self.get_or_create_category(soup, category_url)
                if not category_obj:
                    self.stdout.write(self.style.ERROR("Не удалось определить или создать категорию. Прерывание парсинга этой категории."))
                    break

            # Ищем блоки товаров
            products_on_page = soup.select(PRODUCT_LIST_SELECTOR)
            self.stdout.write(f"Найдено блоков товаров на странице: {len(products_on_page)}")

            if not products_on_page and self.config['processed_pages'] == 1:
                 self.stdout.write(self.style.WARNING("Не найдено товаров на первой странице. Проверьте селектор PRODUCT_LIST_SELECTOR или URL категории."))

            for item_index, item in enumerate(products_on_page):
                if self.config['processed_products'] >= self.config['max_products']:
                     self.stdout.write(self.style.WARNING("Достигнут лимит товаров при обработке страницы."))
                     break # Выходим из цикла по товарам

                # Ищем ссылку на товар внутри блока
                link_tag = item.select_one(PRODUCT_LINK_SELECTOR)

                # Проверяем, найдена ли ссылка и есть ли у нее 'href'
                if not link_tag or 'href' not in link_tag.attrs:
                    self.stdout.write(self.style.WARNING(f"  Не найдена ссылка на товар в блоке #{item_index+1} (селектор: '{PRODUCT_LINK_SELECTOR}'). Пропускаем блок."))
                    # Отладка: вывести HTML проблемного блока
                    # self.stdout.write("--- HTML проблемного блока ---")
                    # self.stdout.write(item.prettify()[:500] + "...") # Выводим начало HTML
                    # self.stdout.write("--- Конец проблемного блока ---")
                    continue

                product_url = urljoin(BASE_URL, link_tag['href'])
                self.parse_product(product_url, category_obj) # Передаем объект категории

            # Проверка лимита товаров еще раз после обработки страницы
            if self.config['processed_products'] >= self.config['max_products']:
                break

            # Ищем ссылку на следующую страницу
            next_page_tag = soup.select_one(PRODUCT_NEXT_PAGE_SELECTOR)
            if next_page_tag and 'href' in next_page_tag.attrs:
                next_page_url = urljoin(BASE_URL, next_page_tag['href'])
                if next_page_url != current_url:
                    current_url = next_page_url
                else:
                    self.stdout.write(self.style.WARNING("Ссылка на следующую страницу ведет на текущую. Остановка пагинации."))
                    current_url = None
            else:
                self.stdout.write(f"\nСсылок на следующую страницу ({PRODUCT_NEXT_PAGE_SELECTOR}) не найдено. Завершение парсинга категории.")
                current_url = None

        if self.config['processed_pages'] >= self.config['max_pages'] and current_url: # Если вышли по лимиту страниц, а не по отсутствию кнопки
             self.stdout.write(self.style.WARNING(f"\nДостигнут лимит ({self.config['max_pages']}) страниц для категории {category_url}."))


    def get_or_create_category(self, soup, url):
        """Получает или создает категорию в БД."""
        try:
            name = ""
            # Сначала ищем H1
            title_tag = soup.select_one('h1.title') # Используем h1.title как в HTML
            if title_tag:
                name = clean_text(title_tag.text)

            # Если H1 не найден или пуст, пробуем хлебные крошки
            if not name:
                 breadcrumbs = soup.select('.breadcrumbs p > span > span') # Последний span внутри последнего p
                 if breadcrumbs:
                     name = clean_text(breadcrumbs[-1].text)

            # Если все еще нет имени, берем из URL
            if not name:
                self.stdout.write(self.style.WARNING(f"Не удалось найти имя категории в H1 или крошках на {url}. Использую часть URL."))
                parsed_url = urlparse(url)
                # Берем последний значащий сегмент пути
                path_parts = [part for part in parsed_url.path.split('/') if part]
                name = path_parts[-1] if path_parts else "default-category"
                name = name.replace('-', ' ').capitalize()

            if not name: # Крайний случай
                self.stdout.write(self.style.ERROR(f"Не удалось определить имя категории для {url}."))
                return None

            slug = slugify(name)[:255] # Ограничиваем длину slug
            if not slug: slug = hashlib.md5(name.encode()).hexdigest()[:10]

            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name[:255]} # Ограничиваем длину имени
            )
            action = "Создана" if created else "Найдена"
            self.stdout.write(self.style.SUCCESS(f"{action} категория: '{category.name}' (slug: {category.slug})"))
            return category

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при получении/создании категории для URL {url}: {str(e)}"))
            traceback.print_exc()
            return None

    # --- Методы, связанные с парсингом продукта ---

    def parse_product(self, url, category):
        """Парсит данные одного товара и сохраняет их в БД, заполняя все поля."""
        self.stdout.write(f"  Парсинг товара: {url}")
        soup = get_soup(url)
        if not soup:
            self.stdout.write(self.style.ERROR(f"  Не удалось загрузить страницу товара: {url}"))
            return

        # --- Извлечение данных ---
        extracted_data = {}
        try:
            name_tag = soup.select_one(PRODUCT_NAME_SELECTOR)
            extracted_data['name'] = clean_text(name_tag.text) if name_tag else f"Товар {hashlib.md5(url.encode()).hexdigest()[:8]}"

            extracted_data['sku'] = self.get_sku(soup, url)

            price_tag = soup.select_one(PRODUCT_PRICE_SELECTOR)
            extracted_data['price'] = clean_price(price_tag.text) if price_tag else 0

            availability_tag = soup.select_one(PRODUCT_AVAILABILITY_SELECTOR)
            extracted_data['in_stock'] = False
            if availability_tag:
                availability_text = clean_text(availability_tag.text).lower()
                if 'є в наявності' in availability_text or 'в наличии' in availability_text:
                    extracted_data['in_stock'] = True

            extracted_data['description'] = self.get_description(soup)
            extracted_data['features'] = self.get_features(soup)
            extracted_data['part_type_obj'] = self.get_or_create_part_type(extracted_data['features'])
            extracted_data['brand_obj'] = self.get_or_create_brand(extracted_data['features'])

            image_urls_data = self.get_image_urls(soup) # Получаем список словарей {'url': ..., 'alt': ...}
            extracted_data['image_urls_data'] = image_urls_data
            extracted_data['main_image_url'] = image_urls_data[0]['url'] if image_urls_data else None

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка при извлечении базовых данных товара {url}: {str(e)}"))
            traceback.print_exc()
            return # Не продолжаем, если не смогли получить основные данные

        # --- Подготовка данных для сохранения ---
        product_data_defaults = {
            'name': extracted_data['name'][:255], # Ограничение длины
            'price': extracted_data['price'],
            'category': category,
            'in_stock': extracted_data['in_stock'],
            'discription': extracted_data['description'], # Поле модели называется 'discription'
            'image_ondeploy': extracted_data['main_image_url'][:500] if extracted_data['main_image_url'] else None, # Ограничение длины
            'part_type': extracted_data['part_type_obj'],
            'brand': extracted_data['brand_obj'],
            # slug генерируется моделью, но можно и здесь для update_or_create
            'slug': slugify(f"{extracted_data['sku']}-{extracted_data['name']}")[:255]
        }

        # --- Сохранение в БД ---
        product = None
        created = False
        try:
            # Используем transaction.atomic для гарантии целостности
            with transaction.atomic():
                # Сначала ищем по SKU
                product, created = Product.objects.update_or_create(
                    sku=extracted_data['sku'],
                    defaults=product_data_defaults
                )

                action = "Создан" if created else "Обновлен"

                # Если товар найден, но обновление запрещено, выходим
                if not created and not self.config['update_existing']:
                    self.stdout.write(f"  Товар {extracted_data['sku']} уже существует. Пропуск обновления.")
                    self.config['processed_products'] += 1 # Считаем обработанным
                    return

                # Обновляем характеристики (ProductFeature)
                self.update_features(product, extracted_data['features'])

                # Обновляем совместимость (ManyToManyField compatible_models)
                compatibility_list = self.parse_compatibility(extracted_data['features'])
                self.update_compatibility(product, compatibility_list)

                # Загружаем изображения (Product.image и ProductImage)
                if not self.config['skip_images']:
                     # Удаляем старые доп. изображения только при обновлении
                    if not created:
                        try:
                            ProductImage.objects.filter(product=product).delete()
                        except Exception as img_del_err:
                            self.stdout.write(self.style.ERROR(f"  Ошибка при удалении старых доп. изображений для {product.sku}: {img_del_err}"))
                    # Передаем список словарей {'url': ..., 'alt': ...}
                    self.process_images(product, extracted_data['image_urls_data'], url)

                # Инкрементируем счетчик только после успешной обработки
                self.config['processed_products'] += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  {action} товар: {product.sku} - {product.name}"
                ))

        except IntegrityError as e:
            # Частая причина - неуникальный slug, который мог быть сгенерирован для другого товара с похожим именем/sku
            self.stdout.write(self.style.ERROR(f"  Ошибка целостности БД при сохранении товара {extracted_data.get('sku', 'N/A')} ({url}): {str(e)}"))
            self.stdout.write(self.style.WARNING(f"  Возможно, проблема с уникальностью SKU ({extracted_data.get('sku')}) или Slug ({product_data_defaults.get('slug')})."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Неожиданная ошибка при сохранении товара {extracted_data.get('sku', 'N/A')} ({url}): {str(e)}"))
            traceback.print_exc()


    def get_sku(self, soup, url):
        """Извлекает артикул (SKU) или генерирует хеш."""
        try:
            sku_tag = soup.select_one(PRODUCT_SKU_SELECTOR)
            if not sku_tag: raise ValueError("Тег артикула не найден")

            # Ищем текст после "Артикул:" и убираем лишнее
            sku_text = clean_text(sku_tag.text)
            match_simple = re.search(r'(?i)(?:Артикул|Код товару)[:\s]*([a-zA-Z0-9-]+)', sku_text)

            if match_simple and match_simple.group(1).strip():
                sku = match_simple.group(1).strip()
            else:
                 # Если не нашли "Артикул:", пробуем найти любое число/код в тексте
                 match_fallback = re.search(r'([a-zA-Z0-9-]+)', sku_text)
                 if not match_fallback or not match_fallback.group(1).strip():
                      raise ValueError("Артикул не найден в тексте тега")
                 sku = match_fallback.group(1).strip()

            if not sku: raise ValueError("Извлеченный артикул пуст")
            return sku[:100] # Ограничиваем длину SKU по модели
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Не удалось получить SKU со стр. {url} ({e}). Генерация хеша."))
            return hashlib.md5(url.encode()).hexdigest()[:12]


    def get_description(self, soup):
        """Извлекает и очищает описание товара."""
        desc_tag = soup.select_one(PRODUCT_DESCRIPTION_SELECTOR)
        # Получаем текст, сохраняя переносы строк, и очищаем лишние пробелы
        return clean_text(desc_tag.get_text(separator='\n', strip=True)) if desc_tag else ''


    def get_features(self, soup):
        """Извлекает характеристики товара в виде словаря."""
        features = {}
        feature_items = soup.select(PRODUCT_FEATURES_SELECTOR)
        for item in feature_items:
            try:
                name_tag = item.select_one(PRODUCT_FEATURE_NAME_SELECTOR)
                value_tag = item.select_one(PRODUCT_FEATURE_VALUE_SELECTOR)
                if name_tag and value_tag:
                    # Очищаем имя от двоеточия и пробелов
                    name = clean_text(name_tag.text).replace(':', '').strip()
                    value = clean_text(value_tag.text)
                    if name and value: features[name] = value
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Ошибка парсинга характеристики: {e}"))
        return features


    def get_or_create_part_type(self, features):
        """Находит или создает PartType на основе характеристик."""
        type_keys = ['Тип товару', 'Тип запчастини', 'Тип']
        type_name = None
        for key in type_keys:
            if key in features:
                type_name = features[key].strip()
                if type_name: break # Нашли непустое - выходим

        if type_name:
            try:
                # Ограничиваем длину и создаем slug
                name_cleaned = type_name[:100]
                slug = slugify(name_cleaned)[:100]
                if not slug: slug = hashlib.md5(name_cleaned.encode()).hexdigest()[:10]

                part_type, created = PartType.objects.get_or_create(
                    slug=slug, # Ищем по slug
                    defaults={'name': name_cleaned}
                )
                if created:
                    self.stdout.write(f"      Создан новый тип запчасти: {name_cleaned}")
                return part_type
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"      Ошибка при создании PartType '{type_name}': {e}"))
        return None


    def get_or_create_brand(self, features):
        """Находит или создает Brand на основе характеристик."""
        brand_keys = ['Бренд', 'Виробник', 'Производитель']
        brand_name = None
        for key in brand_keys:
            if key in features:
                raw_name = features[key].strip()
                # Пропускаем неинформативные бренды
                if raw_name.lower() not in ['generic', 'no name', 'noname', 'китай', 'china', '-', '']:
                     brand_name = raw_name
                if brand_name: break # Нашли непустое - выходим

        if brand_name:
             try:
                 name_cleaned = brand_name[:100]
                 slug = slugify(name_cleaned)[:100]
                 if not slug: slug = hashlib.md5(name_cleaned.encode()).hexdigest()[:10]

                 brand, created = Brand.objects.get_or_create(
                     slug=slug, # Ищем по slug
                     defaults={'name': name_cleaned}
                 )
                 if created:
                     self.stdout.write(f"      Создан новый бренд: {name_cleaned}")
                 return brand
             except Exception as e:
                 self.stdout.write(self.style.ERROR(f"      Ошибка при создании Brand '{brand_name}': {e}"))
        return None


    def parse_compatibility(self, features):
        """Извлекает список совместимых моделей из характеристик."""
        compatibility_list = []
        compatibility_keys = ['Сумісність', 'Підходить для', 'Моделі', 'Совместимость']
        raw_string = ""
        for key in compatibility_keys:
            if key in features:
                raw_string += features[key] + ", "

        if raw_string:
            compatibility_list = [model.strip() for model in raw_string.split(',') if model.strip()]
        return list(set(compatibility_list)) # Уникальные значения


    def update_features(self, product, features):
        """Обновляет ProductFeature для товара."""
        try:
            # Удаляем старые одним запросом
            ProductFeature.objects.filter(product=product).delete()
            # Готовим новые для bulk_create
            features_to_create = []
            for name, value in features.items():
                 # Обрезаем до длины полей модели
                features_to_create.append(
                    ProductFeature(
                        product=product,
                        name=name[:255],
                        value=value[:255] # В модели ProductFeature value тоже 255
                    )
                )
            if features_to_create:
                ProductFeature.objects.bulk_create(features_to_create, ignore_conflicts=True)
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"    Ошибка при обновлении характеристик для {product.sku}: {e}"))


    def update_compatibility(self, product, models_list):
        """Обновляет связи Product с ElectricVehicleModel."""
        if not models_list:
            try:
                product.compatible_models.clear()
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"    Ошибка при очистке совместимости для {product.sku}: {e}"))
            return

        models_to_set = []
        for model_name in models_list:
            if not model_name: continue
            try:
                name_cleaned = model_name[:255] # По модели ElectricVehicleModel
                slug = slugify(name_cleaned)[:255]
                if not slug: slug = hashlib.md5(name_cleaned.encode()).hexdigest()[:10]

                model, created = ElectricVehicleModel.objects.get_or_create(
                    slug=slug,
                    defaults={'name': name_cleaned}
                )
                models_to_set.append(model)
                if created:
                    self.stdout.write(f"      Создана совместимая модель: {name_cleaned}")
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"      Ошибка при создании/получении ElectricVehicleModel '{model_name}': {e}"))

        if models_to_set:
            try:
                product.compatible_models.set(models_to_set) # set() - эффективный способ обновления M2M
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"    Ошибка при установке связей совместимости для {product.sku}: {e}"))


    # --- Методы для обработки изображений ---

    def get_image_urls(self, soup):
        """Находит все URL изображений и их alt тексты на странице товара."""
        image_data = []
        # Ищем изображения внутри блока div.product__images
        image_tags = soup.select('div.product__images img')
        if not image_tags: # Запасной вариант, если структура иная
             image_tags = soup.select(PRODUCT_IMAGES_SELECTOR) # Используем старый селектор

        for img_tag in image_tags:
            src = img_tag.get('src') or img_tag.get('data-src') # Учитываем lazy load
            if src:
                full_url = urljoin(BASE_URL, src)
                # Фильтруем заглушки и слишком короткие URL
                if 'placeholder' not in full_url.lower() and 'logo' not in full_url.lower() and len(full_url) > len(BASE_URL) + 5:
                    alt_text = clean_text(img_tag.get('alt', ''))
                    # Добавляем только уникальные URL
                    if not any(d['url'] == full_url for d in image_data):
                        image_data.append({'url': full_url, 'alt': alt_text})
        return image_data


    def process_images(self, product, image_data_list, product_url):
        """Запускает загрузку основного и дополнительных изображений."""
        if not image_data_list:
            self.stdout.write(self.style.WARNING(f"    Изображения не найдены или не прошли фильтр для товара {product.sku} на {product_url}"))
            return

        # Первое изображение - основное
        main_image_data = image_data_list[0]
        success = self.download_image(product, main_image_data, product_url, is_main=True)

        # Если основное загрузилось, грузим остальные
        if success:
            for img_data in image_data_list[1:]:
                self.download_image(product, img_data, product_url, is_main=False)
        else:
             self.stdout.write(self.style.WARNING(f"    Основное изображение не загружено, пропуск остальных для {product.sku}."))


    def download_image(self, product, image_data, product_url, is_main=False):
        """Загружает одно изображение и сохраняет его."""
        url = image_data['url']
        # Используем alt из HTML или генерируем из имени товара/SKU
        alt_text = image_data['alt'] or f"{product.name} - {product.sku}"

        try:
            response = requests.get(url, headers=HEADERS, stream=True, timeout=45, allow_redirects=True) # Увеличен таймаут
            response.raise_for_status()
            content_type = response.headers.get('content-type')
            if not content_type or not content_type.lower().startswith('image/'):
                 self.stdout.write(self.style.WARNING(f"    URL {url} не изображение ({content_type}). Пропуск."))
                 return False

            # Определение расширения файла
            file_ext = '.jpg' # Default
            try: # Пытаемся получить из URL
                path_ext = os.path.splitext(urlparse(url).path)[1]
                if path_ext and 1 < len(path_ext) <= 5: file_ext = path_ext.lower()
            except: pass # Игнорируем ошибки парсинга URL

            # Генерируем имя файла
            file_name = f"{product.sku}_{hashlib.md5(url.encode()).hexdigest()[:8]}{file_ext}"
            image_file = ContentFile(response.content, name=file_name)
            if image_file.size < 100: # Проверка на слишком маленький размер (вероятно, ошибка)
                self.stdout.write(self.style.WARNING(f"    Загружен слишком маленький файл ({image_file.size} байт) для {url}. Пропуск."))
                return False

            # Сохранение
            if is_main:
                # Удаляем старое основное изображение ПЕРЕД сохранением нового
                # Это важно, чтобы избежать конфликтов имен, если оно то же самое
                if product.image:
                    try:
                        product.image.delete(save=False) # Не сохраняем модель здесь
                    except Exception as img_del_err:
                         self.stdout.write(self.style.ERROR(f"    Не удалось удалить старое основное изображение {product.image.name}: {img_del_err}"))
                # Сохраняем новое изображение и обновляем запись Product
                product.image.save(file_name, image_file, save=True)
                self.stdout.write(f"    Загружено основное изображение: {file_name}")
            else:
                 # Создаем запись для доп. изображения
                 ProductImage.objects.create(
                     product=product,
                     image=image_file,
                     alt_text=alt_text[:255] # Обрезаем alt_text по модели
                 )
                 self.stdout.write(f"    Загружено доп. изображение: {file_name}")
            return True

        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR(f"    Таймаут ({response.elapsed.total_seconds()} сек) при загрузке {url} для {product.sku}"))
            return False
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"    Ошибка сети при загрузке {url} для {product.sku}: {str(e)}"))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Ошибка загрузки/сохранения {url} для {product.sku} ({product_url}): {str(e)}"))
            traceback.print_exc() # Поможет отловить неочевидные ошибки Pillow или Django
            return False

# --- Конец класса Command ---

# Блок if __name__ == '__main__': остается без изменений
if __name__ == '__main__':
    print("Этот скрипт предназначен для запуска как Django management command:")
    print("python manage.py parse_products --start-category <URL> [options]")