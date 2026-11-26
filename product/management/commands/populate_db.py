# Файл: product/management/commands/populate_db.py

import random
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
# Заменили импорт slugify!
# from django.utils.text import slugify
from slugify import slugify # Используем улучшенную версию из python-slugify

# Замените 'product' на имя вашего приложения, если оно другое
from product.models import Category, Product, PartType, Brand, ElectricVehicleModel, ProductFeature

# --- Конфигурация Генерации ---
NUM_CATEGORIES = 15 # Сколько категорий выбрать из списка ниже
NUM_PRODUCTS_PER_CATEGORY = 20
USE_PLACEHOLDER_IMAGES = True # Использовать https://via.placeholder.com

# --- Определения Данных ---

# 1. Типы запчастей
PART_TYPE_NAMES = [
    "Аксесуар", "Акумулятор", "Блок живлення", "Вилка", "Двигун", "Дека/Корпус",
    "Дисплей", "Камера", "Колесо", "Контролер", "Курок газу/гальма", "Механізм складання",
    "Наклейка", "Підніжка", "Покришка", "Проводка", "Кермо/Рульова", "Ручка гальма",
    "Гріпса", "Гальмівна система", "Ліхтар/Стоп-сигнал", "Кріплення", "Інше"
]

# 2. Бренды
BRAND_NAMES = [
    "Kugoo", "Xiaomi", "Ninebot", "Generic", "Dualtron", "Speedway", "Crosser",
    "Like.Bike", "Ultron", "Atlas", "OKAI", "CST", "UMService", "Zero", "Generic OEM",
    "Bosch", "Samsung", "LG Chem", "Panasonic"
]

# 3. Модели Электротранспорта
EV_MODEL_NAMES = [
    "Kugoo M4", "Kugoo M4 Pro", "Kugoo S1", "Kugoo S3", "Kugoo S3 Pro",
    "Kugoo G-Booster", "Kugoo G2 Pro", "Kugoo Kirin G3", "Kugoo M5", "Kugoo C1",
    "Xiaomi M365", "Xiaomi M365 Pro", "Xiaomi Pro 2", "Xiaomi 1S", "Xiaomi Essential", "Xiaomi Mi 3",
    "Xiaomi 4 Pro", "Xiaomi 4 Lite", "Xiaomi 4 Ultra",
    "Ninebot Max G30", "Ninebot Max G30P", "Ninebot Max G30LE", "Ninebot ES1", "Ninebot ES2",
    "Ninebot ES4", "Ninebot E22", "Ninebot E25", "Ninebot F20", "Ninebot F30", "Ninebot F40",
    "Ninebot F2", "Ninebot F2 Pro", "Ninebot G2",
    "Dualtron Thunder", "Dualtron Spider", "Dualtron Eagle Pro", "Dualtron Mini",
    "Speedway 4", "Speedway 5", "Speedway Leger",
    "Like.Bike SEEV", "Like.Bike Bolt", "Like.Bike Neo",
    "Crosser T4", "Crosser E9", "Crosser T8",
    "Ultron T108", "Ultron T11",
    "Zero 10X", "Zero 8",
    "Універсальний", "Інша модель"
]

# 4. Определения Категорий (выберем NUM_CATEGORIES из них)
# Добавлен 'related_part_type_name' для связи с типом
CATEGORY_DEFINITIONS_ALL = [
    {"name": "Аксесуари", "slug": "aksesuari", "related_part_type_name": "Аксесуар"},
    {"name": "Акумулятори (АКБ)", "slug": "akumulyatori-akb", "related_part_type_name": "Акумулятор"},
    {"name": "Блоки живлення (зарядні)", "slug": "bloki-zhivlennya-zaryadni", "related_part_type_name": "Блок живлення"},
    {"name": "Вилки", "slug": "vilki", "related_part_type_name": "Вилка"},
    {"name": "Двигуни (мотор-колеса)", "slug": "dviguni-motor-kolesa", "related_part_type_name": "Двигун"},
    {"name": "Деки, корпуси, кришки", "slug": "deki-korpusi-krishki", "related_part_type_name": "Дека/Корпус"},
    {"name": "Дисплеї та бортові комп'ютери", "slug": "displei-ta-bortovi-kompyuteri", "related_part_type_name": "Дисплей"},
    {"name": "Дрібні запчастини", "slug": "dribni-zapchastini", "related_part_type_name": "Інше"},
    {"name": "Камери", "slug": "kameri", "related_part_type_name": "Камера"},
    {"name": "Колеса в зборі", "slug": "kolesa-v-zbori", "related_part_type_name": "Колесо"},
    {"name": "Контролери", "slug": "kontroleri", "related_part_type_name": "Контролер"},
    {"name": "Кріплення та з'єднання", "slug": "kriplennya-ta-zyednannya", "related_part_type_name": "Кріплення"},
    {"name": "Курки газу та гальма", "slug": "kurki-gazu-ta-galma", "related_part_type_name": "Курок газу/гальма"},
    {"name": "Механізми складання", "slug": "mekhanizmi-skladannya", "related_part_type_name": "Механізм складання"},
    {"name": "Наклейки та декор", "slug": "nakleiki-ta-dekor", "related_part_type_name": "Наклейка"},
    {"name": "Підніжки", "slug": "pidnizhki", "related_part_type_name": "Підніжка"},
    {"name": "Покришки", "slug": "pokrishki", "related_part_type_name": "Покришка"},
    {"name": "Проводка та роз'єми", "slug": "provodka-ta-rozjemi", "related_part_type_name": "Проводка"},
    {"name": "Рульова колонка та кермо", "slug": "rulyova-kolonka-ta-kermo", "related_part_type_name": "Кермо/Рульова"},
    {"name": "Ручки гальма", "slug": "ruchki-galma", "related_part_type_name": "Ручка гальма"},
    {"name": "Ручки керма (гріпси)", "slug": "ruchki-kerma-gripsi", "related_part_type_name": "Гріпса"},
    {"name": "Системи гальмування", "slug": "sistemi-galmuvannya", "related_part_type_name": "Гальмівна система"},
    {"name": "Стоп-сигнали та ліхтарі", "slug": "stop-signali-ta-likhtari", "related_part_type_name": "Ліхтар/Стоп-сигнал"},
]

# Перемешиваем и выбираем нужное количество категорий
random.shuffle(CATEGORY_DEFINITIONS_ALL)
CATEGORY_DEFINITIONS = CATEGORY_DEFINITIONS_ALL[:NUM_CATEGORIES]

class Command(BaseCommand):
    help = 'Populates the database with sample product data.'

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.SUCCESS("Starting database population..."))

        try:
            with transaction.atomic(): # Используем транзакцию для скорости и целостности

                # --- Шаг 1: Создание/Получение Вспомогательных Объектов ---
                self.stdout.write("Creating/Fetching Part Types...")
                part_types = {}
                for name in PART_TYPE_NAMES:
                    slug = slugify(name) # Генерируем слаг заранее
                    if not slug: # На случай, если имя пустое или содержит только невалидные символы
                        self.stderr.write(self.style.WARNING(f"  Could not generate slug for PartType name: '{name}'. Skipping."))
                        continue
                    pt, created = PartType.objects.get_or_create(
                        slug=slug,              # Ищем по слагу
                        defaults={'name': name} # Если не найдено, создаем с этим именем (слаг уже есть)
                    )
                    part_types[name] = pt
                    # if created: self.stdout.write(f"  Created PartType: {name}")

                self.stdout.write("Creating/Fetching Brands...")
                brands = {}
                for name in BRAND_NAMES:
                    slug = slugify(name)
                    if not slug:
                        self.stderr.write(self.style.WARNING(f"  Could not generate slug for Brand name: '{name}'. Skipping."))
                        continue
                    b, created = Brand.objects.get_or_create(
                        slug=slug,
                        defaults={'name': name}
                    )
                    brands[name] = b
                    # if created: self.stdout.write(f"  Created Brand: {name}")

                self.stdout.write("Creating/Fetching Electric Vehicle Models...")
                ev_models = {}
                for name in EV_MODEL_NAMES:
                    slug = slugify(name)
                    if not slug:
                        self.stderr.write(self.style.WARNING(f"  Could not generate slug for EV Model name: '{name}'. Skipping."))
                        continue
                    evm, created = ElectricVehicleModel.objects.get_or_create(
                        slug=slug,
                        defaults={'name': name}
                    )
                    ev_models[name] = evm
                    # if created: self.stdout.write(f"  Created EV Model: {name}")

                ev_model_list = list(ev_models.values()) # Список для случайного выбора

                # --- Шаг 2: Создание/Получение Категорий ---
                self.stdout.write(f"Creating/Fetching {len(CATEGORY_DEFINITIONS)} Categories...")
                parent_cat, p_created = Category.objects.get_or_create(
                    slug='zapchasti-dlya-elektrotransporta',
                    defaults={'name': "Запчастини для електротранспорту", 'parent': None}
                )
                # if p_created: self.stdout.write(f"  Created Parent Category: {parent_cat.name}")

                categories_to_populate = {}
                for i, cat_def in enumerate(CATEGORY_DEFINITIONS):
                    # Используем slugify для получения слага из имени, если он не задан явно
                    cat_slug = cat_def.get('slug') or slugify(cat_def['name'])
                    if not cat_slug:
                        self.stderr.write(self.style.WARNING(f"  Could not generate slug for Category name: '{cat_def['name']}'. Skipping category definition."))
                        continue

                    cat, created = Category.objects.get_or_create(
                        slug=cat_slug,
                        defaults={'name': cat_def['name'], 'parent': parent_cat}
                    )
                    # Обновляем имя/родителя, если категория уже существовала, но данные отличаются
                    if not created and (cat.name != cat_def['name'] or cat.parent != parent_cat):
                        cat.name = cat_def['name']
                        cat.parent = parent_cat
                        cat.save()

                    # Связываем категорию с типом запчасти (для генерации товаров)
                    # Убедимся, что тип "Інше" точно есть в part_types
                    fallback_part_type = part_types.get("Інше")
                    if not fallback_part_type:
                        # Если "Інше" не создался (что маловероятно теперь), создаем его принудительно
                        fallback_slug = slugify("Інше")
                        fallback_part_type, _ = PartType.objects.get_or_create(slug=fallback_slug, defaults={'name': "Інше"})
                        part_types["Інше"] = fallback_part_type
                        self.stdout.write(self.style.WARNING("  Fallback PartType 'Інше' was missing and created now."))


                    related_part_type = part_types.get(cat_def['related_part_type_name'], fallback_part_type)
                    categories_to_populate[cat_slug] = {
                        'object': cat,
                        'part_type': related_part_type
                    }
                    # if created: self.stdout.write(f"  Created Category: {cat.name}")


                # --- Шаг 3: Генерация и Добавление Продуктов ---
                self.stdout.write(f"\nGenerating {NUM_PRODUCTS_PER_CATEGORY} products for each of the {len(categories_to_populate)} categories...")
                product_counter = 0
                total_products_to_create = len(categories_to_populate) * NUM_PRODUCTS_PER_CATEGORY

                for cat_slug, cat_data in categories_to_populate.items():
                    current_category = cat_data['object']
                    default_part_type = cat_data['part_type']
                    self.stdout.write(f"\n--- Processing Category: {current_category.name} ---")

                    for i in range(1, NUM_PRODUCTS_PER_CATEGORY + 1):
                        product_counter += 1

                        # Выбираем случайный бренд и модели
                        random_brand = random.choice(list(brands.values()))
                        num_compatible = random.randint(1, min(4, len(ev_model_list))) # 1-4 совместимые модели
                        random_models = random.sample(ev_model_list, k=num_compatible)

                        # Увеличиваем шанс выбора модели, соответствующей бренду
                        if random_brand.name in ["Xiaomi", "Kugoo", "Ninebot"] and random.random() < 0.7:
                            matching_models = [m for m in ev_model_list if m.name.startswith(random_brand.name)]
                            if matching_models and matching_models[0] not in random_models:
                                if len(random_models) < num_compatible: random_models.append(matching_models[0])
                                else: random_models[0] = matching_models[0] # Заменяем первую

                        model_names_list = sorted([m.name for m in random_models if m.name != "Універсальний"])
                        has_universal = "Універсальний" in [m.name for m in random_models]

                        if not model_names_list or (len(model_names_list) > 2 and random.random() < 0.5): # Если много моделей или нет конкретных
                             model_compatibility_str = f"для {random_brand.name}" + (" та інших" if len(model_names_list)>1 else "") + (" (Універсальний)" if has_universal else "")
                        elif has_universal:
                             model_compatibility_str = f"для {' / '.join(model_names_list)} (та Універсальний)"
                        else:
                             model_compatibility_str = f"для {' / '.join(model_names_list)}"


                        # Генерируем Название, Характеристики, Цену
                        base_name = default_part_type.name
                        product_name = f"{base_name} {random_brand.name} "
                        features = {}
                        price = random.randint(50, 500) # Базовая цена

                        if base_name == "Акумулятор":
                            voltage = random.choice([36, 48, 52, 60])
                            capacity = random.choice([7.8, 10, 10.4, 12, 13, 15, 16, 18, 20, 21, 25, 30])
                            cell_brand = random.choice(["LG", "Samsung", "Panasonic", "Generic Cells"])
                            product_name += f"{voltage}V {capacity}Ah {model_compatibility_str}"
                            features["Напруга"] = f"{voltage}V"
                            features["Ємність"] = f"{capacity}Ah"
                            features["Елементи"] = cell_brand
                            price = random.randint(2500, 18000)
                        elif base_name == "Двигун":
                            power = random.choice([250, 300, 350, 500, 600, 800, 1000, 1200, 1600])
                            size = random.choice([6.5, 8, 8.5, 10, 11])
                            voltage_req = random.choice([36, 48, 52, 60])
                            product_name += f"{size}\" {power}W {voltage_req}V {model_compatibility_str}"
                            features["Потужність ном."] = f"{power}W"
                            features["Розмір колеса"] = f"{size} дюймів"
                            features["Напруга"] = f"{voltage_req}V"
                            price = random.randint(1500, 9000)
                        elif base_name == "Покришка":
                            size = random.choice(["8 1/2x2", "10x2.0", "10x2.125", "10x2.5", "10x3.0", "11 дюймів", "200x50"])
                            tire_type = random.choice(["Пневматична", "Безкамерна", "Литий (Суцільна)"])
                            tread = random.choice(["Шосейна", "Універсальна", "Позашляхова", "Слік"])
                            product_name += f"{size} {tire_type} {tread} {model_compatibility_str}"
                            features["Розмір"] = size
                            features["Тип"] = tire_type
                            features["Протектор"] = tread
                            price = random.randint(250, 900)
                        elif base_name == "Камера":
                             size = random.choice(["8 1/2x2", "10x2.0", "10x2.125", "10x2.5", "10x3.0", "200x50"])
                             valve = random.choice(["Прямий TR13", "Вигнутий 45°", "Вигнутий 90° TR87"])
                             product_name += f"{size} {valve} {model_compatibility_str}"
                             features["Розмір"] = size
                             features["Тип вентиля"] = valve
                             price = random.randint(100, 400)
                        elif base_name == "Контролер":
                            voltage = random.choice([36, 48, 52, 60, 72])
                            amps = random.choice([13, 15, 17, 20, 21, 23, 25, 30, 35, 40, 45, 50])
                            pins = random.choice([5, 6])
                            controller_type = random.choice(["Стандарт", "Синусний", "Посилений"])
                            product_name += f"{voltage}V {amps}A {controller_type} {pins}pin {model_compatibility_str}"
                            features["Напруга"] = f"{voltage}V"
                            features["Макс. струм"] = f"{amps}A"
                            features["Тип"] = controller_type
                            features["Роз'єм дисплея"] = f"{pins} pin"
                            price = random.randint(600, 5000)
                        elif base_name == "Дисплей":
                             model_code = random.choice(["TF-100", "QS-S4", "LH-100", "EY3", "JX-168", "Xiaomi BLE"])
                             pins = random.choice([5, 6])
                             has_trigger = random.choice([True, False])
                             product_name = f"Дисплей {model_code} ({pins}pin){' з курком' if has_trigger else ''} {model_compatibility_str}"
                             features["Модель"] = model_code
                             features["Роз'єм"] = f"{pins} pin"
                             if has_trigger: features["Курок газу"] = "Інтегрований"
                             price = random.randint(400, 3000)
                        elif base_name == "Блок живлення":
                             output_voltage = random.choice([42, 54.6, 67.2, 84])
                             output_amps = random.choice([1.5, 2, 3, 4, 5])
                             connector = random.choice(["DC 5.5x2.1mm", "DC 5.5x2.5mm", "GX16-3 pin", "DC 8mm (Xiaomi)", "XLR"])
                             product_name = f"Зарядний пристрій {output_voltage}V {output_amps}A ({connector}) {model_compatibility_str}"
                             features["Вихідна напруга"] = f"{output_voltage}V"
                             features["Вихідний струм"] = f"{output_amps}A"
                             features["Тип роз'єму"] = connector
                             price = random.randint(350, 1800)
                        else:
                            # Общее имя для других категорий
                            suffix = random.choice(["стандарт", "посилений", "V2.0", "оригінал", f"тип {i%3+1}", "з логотипом", "чорний", "сірий"])
                            product_name += f"{suffix} {model_compatibility_str}"
                            features["Матеріал"] = random.choice(["Алюміній", "Сталь", "ABS Пластик", "Полікарбонат", "Гума", "Силікон"])
                            if base_name == "Гріпса": features["Довжина"] = random.choice(["120мм", "130мм", "135мм"])
                            if base_name == "Ліхтар/Стоп-сигнал": features["Тип світла"] = random.choice(["LED", "COB LED"])
                            if base_name == "Гальмівна система": features["Тип"] = random.choice(["Дисковий механічний", "Дисковий гідравлічний", "Барабанний", "Рекуперативний"])
                            if base_name == "Аксесуар": features["Призначення"] = random.choice(["Тримач телефону", "Дзеркало", "Замок", "Сумка", "Сигнал"])

                        # SKU
                        sku = f"{cat_slug[:3].upper()}-{random_brand.name[:3].upper()}-{product_counter:04d}"
                        # Округление цены
                        price = (price // 10) * 10

                        # Изображение
                        img_url = None
                        if USE_PLACEHOLDER_IMAGES:
                            img_text = slugify(base_name) + f"+{i}"
                            img_url = f"https://via.placeholder.com/400x400.png?text={img_text}"

                        # Slug (уникальный)
                        # Используем slugify из python-slugify, он должен справиться
                        base_slug = slugify(product_name[:80]) # Ограничим длину для slug
                        if not base_slug: # Доп. проверка, если slugify все же вернет пустое
                            base_slug = f"product-{default_part_type.slug}"
                        unique_slug = f"{base_slug}-{product_counter}"


                        # Данные для создания продукта
                        product_data = {
                            "category": current_category,
                            "sku": sku,
                            "name": product_name[:255],
                            # slug будет установлен при создании, если не найден по нему
                            "discription": f"Детальний опис для: {product_name}. \nСумісність: {model_compatibility_str}. \nВиробник: {random_brand.name}. \nАртикул: {sku}. \nЧудовий вибір для вашого електротранспорту!",
                            "price": price,
                            "image_ondeploy": img_url,
                            "in_stock": random.random() < 0.9, # 90% шанс наличия
                            "part_type": default_part_type,
                            "brand": random_brand,
                        }

                        # Создаем или получаем продукт
                        product_obj, created = Product.objects.get_or_create(
                             slug=unique_slug[:255], # Используем уникальный slug для поиска (обрезанный)
                             defaults=product_data  # Передаем все данные в defaults
                        )

                        if created:
                            # Добавляем совместимые модели (только если создан новый)
                            product_obj.compatible_models.add(*random_models)

                            # Добавляем характеристики (только если создан новый)
                            for feat_name, feat_value in features.items():
                                ProductFeature.objects.create(product=product_obj, name=feat_name, value=feat_value)

                            # self.stdout.write(f"  [+] Created: {product_obj.name} (Slug: {product_obj.slug})")
                        # else:
                            # self.stdout.write(f"  [-] Exists: {product_obj.name} (Slug: {product_obj.slug})")

                        # Небольшая пауза, чтобы не перегружать CPU/DB и видеть прогресс (опционально)
                        # time.sleep(0.01)
                        if product_counter % 20 == 0: # Печатать прогресс каждые 20 товаров
                             self.stdout.write(f"    ...processed {product_counter}/{total_products_to_create} products.")


            # --- Финальное Сообщение ---
            end_time = time.time()
            total_time = end_time - start_time
            self.stdout.write(self.style.SUCCESS(f"\nDatabase population completed successfully in {total_time:.2f} seconds."))
            self.stdout.write(self.style.SUCCESS(f"Total products processed/created: {product_counter}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nAn error occurred during population: {e}"))
            import traceback # Добавим traceback для детальной ошибки
            traceback.print_exc() # Печатаем полный traceback ошибки


# Код ниже нужен только если вы НЕ используете management command
if __name__ == "__main__" and "manage.py" not in __import__("sys").argv[0]:
     print("This script should be run within the Django environment.")
     print("Use 'python manage.py shell' and paste the code, or save as a management command.")