# Файл: product/management/commands/fetch_images.py

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urljoin, quote_plus
from django.core.management.base import BaseCommand
from django.conf import settings
from product.models import Product # Убедись, что путь к модели Product верный

# --- Конфигурация ---
UMSERVICE_BASE_URL = "https://umservice.com.ua/"
# --- ИЗМЕНЕНО: Обновленный URL поиска на основе предоставленного ---
UMSERVICE_SEARCH_URL_FORMAT = "https://umservice.com.ua/products?keyword={query}" # Убрали category_id, т.к. он был пуст
# --- КОНЕЦ ИЗМЕНЕНИЙ ---
REQUEST_DELAY_SECONDS = (2, 4)
REQUEST_TIMEOUT_SECONDS = 15
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    # Добавим Referer, иногда помогает
    'Referer': UMSERVICE_BASE_URL
}
# Фильтр для товаров, которые нужно обновить
PRODUCT_FILTER = {'image_ondeploy__startswith': 'https://via.placeholder.com'}
# PRODUCT_FILTER = None # Для обработки всех товаров

# CSS селекторы для поиска *ссылки* на товар в результатах поиска
# Оставляем тот, что ты нашел, он может быть правильным для /products
PRODUCT_LINK_SELECTOR_IN_SEARCH = 'a.image__inner.js-image'
# Альтернативный селектор, если первый не сработает
# PRODUCT_LINK_SELECTOR_IN_SEARCH_ALT = '.product-layout .product-thumb .caption h4 a'

# CSS селекторы для поиска *основной картинки* на странице товара
IMAGE_SELECTORS_ON_PRODUCT_PAGE = [
    '#content .thumbnails .image a[href]', # Этот селектор очень зависит от темы OpenCart/CMS
    '.js-product-gallery .slick-list .slick-slide:not(.slick-cloned) a', # Пробуем селектор для галерей на Slick Slider
    'ul.thumbnails li.image-additional a[href]', # Старый вариант
    '.product-image-thumb a[href]', # Старый вариант
    '#content img[itemprop="image"]', # Прямой поиск картинки
    '#content .product-image img', # Общий случай
]
OG_IMAGE_SELECTOR_ON_PRODUCT_PAGE = 'meta[property="og:image"]'

class Command(BaseCommand):
    help = 'Fetches main product image URLs from umservice.com.ua based on product name search.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of products to process.',
        )
        parser.add_argument(
            '--start-id',
            type=int,
            help='Product ID to start processing from.',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Fetch images even if image_ondeploy is not a placeholder.',
        )

    def get_product_page_url(self, product_name):
        """Ищет товар на сайте и возвращает URL его страницы."""

        name_parts = product_name.split()
        simple_search_term = " ".join(name_parts[:4]) # Берем первые 4 слова
        # quote_plus заменит пробелы на '+', что соответствует новому URL
        search_query = quote_plus(simple_search_term.encode('utf-8'))
        self.stdout.write(f"  Simplified search term: '{simple_search_term}'")

        # Используем обновленный URL
        search_url = UMSERVICE_SEARCH_URL_FORMAT.format(query=search_query)
        self.stdout.write(f"  Searching URL: {search_url}")

        try:
            with requests.Session() as session:
                session.headers.update(HEADERS)
                response = session.get(search_url, timeout=REQUEST_TIMEOUT_SECONDS)

            # Теперь ожидаем статус 200 OK, а не 404
            response.raise_for_status()
            time.sleep(random.uniform(*REQUEST_DELAY_SECONDS))

            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем ссылку на товар в результатах поиска (используем селектор, который ты нашел)
            product_link_element = soup.select_one(PRODUCT_LINK_SELECTOR_IN_SEARCH)

            # if not product_link_element: # Можно раскомментировать для пробы альтернативного селектора
            #     product_link_element = soup.select_one(PRODUCT_LINK_SELECTOR_IN_SEARCH_ALT)

            if product_link_element and product_link_element.get('href'):
                relative_product_url = product_link_element['href']
                product_url = urljoin(UMSERVICE_BASE_URL, relative_product_url)

                # Проверка на то, что это страница продукта (может быть /products/.... или содержать ID)
                if '/products/' in product_url:
                    self.stdout.write(self.style.SUCCESS(f"  Found product page link: {product_url}"))
                    return product_url
                else:
                    self.stdout.write(self.style.WARNING(f"  Found link, but it doesn't look like a product page (/products/): {product_url}"))
                    return None
            else:
                # Проверяем наличие сообщения о пустых результатах (селектор может быть другим для /products!)
                no_results_selector = '#content p, .content p, .search-results-empty p' # Пробуем несколько вариантов
                no_results_text = soup.select_one(no_results_selector)
                if no_results_text and ('не знайдено' in no_results_text.text.lower() or 'не найдено' in no_results_text.text.lower() or 'empty' in no_results_text.get('class', [])):
                     self.stdout.write(self.style.WARNING(f"  Search page loaded, but no products found matching '{simple_search_term}'."))
                else:
                     self.stdout.write(self.style.WARNING(f"  No product link found in search results (using selector '{PRODUCT_LINK_SELECTOR_IN_SEARCH}'). Check selector or if page structure for '{search_url}' is different?"))
                return None

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 'N/A'
            self.stderr.write(self.style.ERROR(f"  Search request failed (Status: {status_code}): {e}"))
            # Если получаем 404 здесь, значит даже новый URL не работает или нас блокируют
            return None
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Error parsing search results: {e}"))
            import traceback
            traceback.print_exc()
            return None


    def get_image_url_from_page(self, product_page_url):
        """Извлекает URL главной картинки со страницы товара."""
        if not product_page_url:
            return None

        self.stdout.write(f"  Fetching product page: {product_page_url}")
        try:
            with requests.Session() as session:
                session.headers.update(HEADERS)
                session.headers['Referer'] = product_page_url
                response = session.get(product_page_url, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                time.sleep(random.uniform(*REQUEST_DELAY_SECONDS))

                soup = BeautifulSoup(response.text, 'html.parser')
                image_url = None

                for selector in IMAGE_SELECTORS_ON_PRODUCT_PAGE:
                    img_element = soup.select_one(selector)
                    if not img_element:
                        continue

                    potential_url = None
                    if img_element.name == 'a' and img_element.get('href'):
                        potential_url = img_element.get('href')
                        self.stdout.write(f"    Found potential URL in href of <a> using '{selector}'")
                    elif img_element.name == 'img':
                        potential_url = img_element.get('data-src') or img_element.get('src')
                        self.stdout.write(f"    Found potential URL in src/data-src of <img> using '{selector}'")

                    if potential_url and any(potential_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '?']):
                        is_thumbnail = False
                        if 'x' in potential_url:
                            try:
                                parts = potential_url.split('/')[-1].split('.')[0].split('-')
                                if len(parts) > 1 and 'x' in parts[-1]:
                                    dims = parts[-1].split('x')
                                    if len(dims) == 2 and int(dims[0]) < 400 and int(dims[1]) < 400:
                                        is_thumbnail = True
                            except ValueError:
                                pass
                        if is_thumbnail or any(size in potential_url for size in ['290x290', '100x100', '80x80', '_thumb', '/thumb/']):
                            self.stdout.write(f"      ...but it looks like a thumbnail ({potential_url}). Skipping.")
                            continue

                        image_url = potential_url
                        self.stdout.write(f"  Found image via selector '{selector}': {image_url}")
                        break

                if not image_url:
                    og_image_tag = soup.select_one(OG_IMAGE_SELECTOR_ON_PRODUCT_PAGE)
                    if og_image_tag and og_image_tag.get('content'):
                        image_url = og_image_tag['content']
                        self.stdout.write(f"  Found image via og:image tag: {image_url}")

                if image_url:
                    absolute_image_url = urljoin(UMSERVICE_BASE_URL, image_url)
                    return absolute_image_url
                else:
                    self.stdout.write(self.style.WARNING("  Main image URL not found on product page. Check IMAGE_SELECTORS_ON_PRODUCT_PAGE?"))
                    return None

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 'N/A'
            self.stderr.write(self.style.ERROR(f"  Product page request failed (Status: {status_code}): {e}"))
            return None
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Error parsing product page: {e}"))
            import traceback
            traceback.print_exc()
            return None


    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.SUCCESS("Starting to fetch product images..."))

        products_to_process = Product.objects.all()

        if not options['overwrite'] and PRODUCT_FILTER:
            products_to_process = products_to_process.filter(**PRODUCT_FILTER)
            self.stdout.write(f"Filtering products where image_ondeploy starts with '{PRODUCT_FILTER.get('image_ondeploy__startswith', 'N/A')}'")

        if options['start_id']:
            products_to_process = products_to_process.filter(id__gte=options['start_id'])
            self.stdout.write(f"Starting processing from Product ID: {options['start_id']}")

        products_to_process = products_to_process.order_by('id')
        total_products = products_to_process.count()

        limit = options['limit']
        if limit:
            products_to_process = products_to_process[:limit]
            self.stdout.write(f"Processing limit set to: {limit} products")
            total_products = products_to_process.count() # Обновляем общее количество

        self.stdout.write(f"Found {total_products} products to process.")

        processed_count = 0
        updated_count = 0
        failed_count = 0

        for product in products_to_process:
            processed_count += 1
            self.stdout.write(f"\n[{processed_count}/{total_products}] Processing Product ID: {product.id}, Name: {product.name}")

            # 1. Найти URL страницы товара через поиск
            product_page_url = self.get_product_page_url(product.name)

            if not product_page_url:
                self.stderr.write(self.style.ERROR(f"  Could not find product page for '{product.name}'. Skipping."))
                failed_count += 1
                continue # Переходим к следующему товару

            # 2. Получить URL картинки с найденной страницы
            image_url = self.get_image_url_from_page(product_page_url)

            if image_url:
                # 3. Обновить товар в базе данных
                if product.image_ondeploy != image_url:
                    product.image_ondeploy = image_url
                    product.save(update_fields=['image_ondeploy'])
                    self.stdout.write(self.style.SUCCESS(f"  Updated product {product.id} with image URL: {image_url}"))
                    updated_count += 1
                else:
                     self.stdout.write(self.style.NOTICE(f"  Image URL is already up-to-date for product {product.id}."))
            else:
                self.stderr.write(self.style.ERROR(f"  Could not retrieve image URL for product {product.id}. Skipping update."))
                failed_count += 1


        # --- Финальное Сообщение ---
        end_time = time.time()
        total_time = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f"\nImage fetching finished in {total_time:.2f} seconds."))
        self.stdout.write(f"Total products processed: {processed_count}")
        self.stdout.write(self.style.SUCCESS(f"Products updated: {updated_count}"))
        self.stdout.write(self.style.ERROR(f"Products failed/skipped: {failed_count}"))