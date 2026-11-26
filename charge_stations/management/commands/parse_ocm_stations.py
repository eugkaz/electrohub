# charge_stations/management/commands/parse_ocm_stations.py

import requests
import json
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.contrib.gis.geos import Point # Для создания гео-объектов
from charge_stations.models import ChargingStation # Импортируем твою модель

# --- Карта статусов OCM к статусам твоей модели ---
# Ключи - это Title из StatusType в OCM API (https://api.openchargemap.io/v3/referencedata/)
# Значения - это значения из твоего `ChargingStation.AvailabilityStatus.choices`
OCM_STATUS_MAP = {
    'Operational': ChargingStation.AvailabilityStatus.AVAILABLE,
    'Partly Operational': ChargingStation.AvailabilityStatus.AVAILABLE, # Решаем, что частично рабочая = доступна
    'Not Operational': ChargingStation.AvailabilityStatus.OFFLINE,
    'Planned': ChargingStation.AvailabilityStatus.PLANNED,
    'Temporarily Unavailable': ChargingStation.AvailabilityStatus.OFFLINE,
    'Unknown': ChargingStation.AvailabilityStatus.UNKNOWN,
    # Добавь/проверь другие статусы из OCM API /referencedata, если нужно
}

class Command(BaseCommand):
    """
    Django Management Command для парсинга данных зарядных станций
    с Open Charge Map API и сохранения их в базу данных.

    По умолчанию настроена на запрос станций в Одессе и Одесской области.
    Используйте флаг --all-country для парсинга всей страны, указанной в --countrycode.
    """
    help = ('Парсит данные станций с OCM API. По умолч.: Одесса и область. '
            'Используйте --all-country для всей страны.')

    def add_arguments(self, parser):
        """
        Определяет аргументы командной строки для настройки параметров парсинга.
        """
        parser.add_argument(
            '--maxresults',
            type=int,
            default=10000, # Значительно увеличиваем лимит для всей страны
            help='Максимальное количество станций для запроса с OCM API (для всей страны может потребоваться > 5000).'
        )
        parser.add_argument(
            '--countrycode',
            type=str,
            default='UA', # По умолчанию Украина
            help='Код страны (ISO 3166-1 alpha-2) для запроса станций.'
        )
        parser.add_argument(
            '--all-country',
            action='store_true', # Делаем это флагом
            default=False,       # По умолчанию флаг выключен
            help='Запросить все станции для указанной страны (--countrycode), игнорируя --latitude, --longitude, --distance.'
        )
        # --- Аргументы для регионального поиска (используются, если --all-country НЕ указан) ---
        parser.add_argument(
            '--latitude',
            type=float,
            default=46.48, # По умолчанию Одесса
            help='Широта центра поиска (используется, если не указан --all-country).'
        )
        parser.add_argument(
            '--longitude',
            type=float,
            default=30.73, # По умолчанию Одесса
            help='Долгота центра поиска (используется, если не указан --all-country).'
        )
        parser.add_argument(
            '--distance',
            type=int,
            default=300, # По умолчанию радиус для Одесской области
            help='Радиус поиска в километрах (используется, если не указан --all-country).'
        )
        parser.add_argument(
            '--distanceunit',
            type=str,
            default='KM', # Единица измерения радиуса
            choices=['KM', 'Miles'],
            help='Единица измерения расстояния (KM или Miles).'
        )


    def handle(self, *args, **options):
        """
        Основной метод, выполняющий логику команды.
        """
        self.stdout.write(self.style.NOTICE("Запуск парсинга станций с Open Charge Map..."))

        # --- 1. Получение API ключа ---
        ocm_api_key = getattr(settings, 'OCM_API_KEY', None)
        if not ocm_api_key:
            raise CommandError("Ошибка: API ключ OpenChargeMap (OCM_API_KEY) не найден в settings.py.")
        if ocm_api_key == "ВАШ_РЕАЛЬНЫЙ_КЛЮЧ_ОТ_OPENCHARGEMAP":
             raise CommandError("Ошибка: Пожалуйста, замените плейсхолдер 'ВАШ_РЕАЛЬНЫЙ_КЛЮЧ_ОТ_OPENCHARGEMAP' на ваш реальный API ключ OCM в settings.py.")

        # --- 2. Формирование параметров запроса ---
        ocm_api_url = "https://api.openchargemap.io/v3/poi/"
        params = {
            'output': 'json',
            'compact': False,    # Получаем полные данные, а не компактные
            'verbose': False,    # Не нужно лишнего в ответе
            'key': ocm_api_key,
            'maxresults': options['maxresults'],
            # Включаем дополнительные поля для большей информации
            'includecomments': True,
            'includeoperationalstatus': True, # Явно запрашиваем статус
        }

        # --- Логика выбора режима: вся страна или регион ---
        if options['all_country']:
            self.stdout.write(self.style.NOTICE(f"РЕЖИМ: Запрос ВСЕХ станций для страны: {options['countrycode']} (max: {options['maxresults']})"))
            if not options['countrycode']:
                 raise CommandError("--countrycode обязателен при использовании --all-country.")
            params['countrycode'] = options['countrycode']
            # Удаляем гео-параметры, если они случайно попали
            params.pop('latitude', None)
            params.pop('longitude', None)
            params.pop('distance', None)
            params.pop('distanceunit', None)
        else:
            self.stdout.write(self.style.NOTICE(f"РЕЖИМ: Запрос станций в регионе: lat={options['latitude']}, lon={options['longitude']}, dist={options['distance']} {options['distanceunit']} (max: {options['maxresults']})"))
            params['latitude'] = options['latitude']
            params['longitude'] = options['longitude']
            params['distance'] = options['distance']
            params['distanceunit'] = options['distanceunit']
            if options['countrycode']: # Можно добавить код страны и для региона
                 params['countrycode'] = options['countrycode']

        self.stdout.write(f"Запрос к OCM API: {ocm_api_url} с параметрами: {params}")

        # --- 3. Выполнение запроса к OCM API ---
        try:
            self.stdout.write("Отправка запроса к OCM API...")
            response = requests.get(ocm_api_url, params=params, timeout=180) # Таймаут 3 минуты
            response.raise_for_status() # Вызовет исключение для 4xx/5xx ответов
            ocm_data = response.json()
            self.stdout.write(self.style.SUCCESS(f"Ответ получен. Статус: {response.status_code}. Станций в ответе: {len(ocm_data) if isinstance(ocm_data, list) else 'Не список'}"))
        except requests.exceptions.Timeout:
             raise CommandError(f"Ошибка: Запрос к OCM API превысил таймаут (180 секунд). Попробуйте уменьшить maxresults или проверьте API OCM.")
        except requests.exceptions.RequestException as e:
            error_text = e.response.text[:500] if hasattr(e, 'response') and e.response else str(e)
            raise CommandError(f"Ошибка запроса к OCM API: {e}. Ответ сервера (начало): {error_text}")
        except json.JSONDecodeError:
             raise CommandError(f"Ошибка декодирования JSON ответа от OCM API. Ответ (начало): {response.text[:500]}")

        if not isinstance(ocm_data, list):
            self.stderr.write(self.style.ERROR("Ошибка: OCM API вернул не список станций. Проверьте параметры запроса и ответ API."))
            return

        # --- 4. Обработка и сохранение данных ---
        created_count = 0
        updated_count = 0
        skipped_count = 0
        total_stations = len(ocm_data)

        self.stdout.write(f"Начало обработки и сохранения {total_stations} станций в базу данных...")

        for i, station_data in enumerate(ocm_data):
            ocm_id = station_data.get('ID') # OCM ID

            if (i + 1) % 100 == 0: # Логгирование прогресса
                 self.stdout.write(f"Обработано {i + 1}/{total_stations} станций...")

            if not ocm_id:
                self.stderr.write(f"Пропуск станции #{i+1} без ID: {station_data.get('AddressInfo', {}).get('Title')}")
                skipped_count += 1
                continue

            # --- Извлечение основных блоков данных ---
            addr_info = station_data.get('AddressInfo', {}) or {}
            connections = station_data.get('Connections', []) or [] # Список коннекторов
            usage_type = station_data.get('UsageType', {}) or {} # Тип использования/доступа
            status_type = station_data.get('StatusType', {}) or {} # Статус работоспособности
            data_provider = station_data.get('DataProvider', {}) or {} # Поставщик данных

            # --- Статус ---
            ocm_status_title = status_type.get('Title', 'Unknown')
            internal_status = OCM_STATUS_MAP.get(ocm_status_title, ChargingStation.AvailabilityStatus.UNKNOWN)

            # --- Координаты ---
            latitude = addr_info.get('Latitude')
            longitude = addr_info.get('Longitude')
            location_point = None
            if latitude is not None and longitude is not None:
                try:
                    location_point = Point(float(longitude), float(latitude), srid=4326)
                except (ValueError, TypeError) as e:
                    self.stderr.write(self.style.WARNING(f"Предупреждение: Неверный формат координат для OCM ID {ocm_id}: lat={latitude}, lon={longitude}. Ошибка: {e}"))

            # --- Адрес ---
            full_address = ", ".join(filter(None, [
                addr_info.get('AddressLine1'), addr_info.get('AddressLine2'),
                addr_info.get('Town'), addr_info.get('StateOrProvince'),
                addr_info.get('Postcode')
            ]))
            if not full_address and addr_info.get('Title'): # Если адрес не собран, берем Title из AddressInfo
                full_address = addr_info.get('Title')

            # --- Дата обновления статуса ---
            date_last_status_str = station_data.get('DateLastStatusUpdate')
            date_last_status_dt = None
            if date_last_status_str:
                try:
                    date_last_status_dt = parse_datetime(date_last_status_str)
                except ValueError:
                    self.stderr.write(self.style.WARNING(f"Не удалось распарсить дату '{date_last_status_str}' для OCM ID {ocm_id}"))

            # --- Фото URL (первое активное изображение) ---
            photo_url = next((item['ItemURL']
                              for item in station_data.get('MediaItems', []) or []
                              if isinstance(item, dict) and item.get('IsEnabled') and item.get('ItemURL')),
                             None)

            # --- Тип Доступа ---
            access_type_str = usage_type.get('Title', '')

            # --- Данные для сохранения/обновления (словарь defaults) ---
            # Собираем все данные, которые будем записывать/обновлять
            defaults = {
                'name': addr_info.get('Title', f'Станція OCM {ocm_id}')[:255], # Название станции или плейсхолдер
                'location': location_point, # Гео-точка (может быть None)
                'address': full_address[:500] if full_address else None, # Полный адрес
                'description': station_data.get('GeneralComments') or addr_info.get('GeneralComments'), # Описание
                'status': internal_status, # Наш внутренний статус
                'operating_hours': addr_info.get('AccessComments', '')[:255], # Комментарии по доступу/часам
                'access_type': access_type_str[:100], # Тип доступа (Public, Private, etc.)
                'pricing': station_data.get('UsageCost', '')[:255], # Информация о цене
                'photo_url': photo_url[:500] if photo_url else None, # URL первого фото
                'data_provider': data_provider.get('Title', '')[:100], # Название провайдера данных
                'date_last_status_update': date_last_status_dt, # Дата обновления статуса
                'connections_details': connections, # Сохраняем весь JSON деталей коннекторов
                'is_reservable': False, # По умолчанию для станций OCM - нет бронирования
                'is_active': True # Считаем активными по умолчанию (можно добавить логику на основе статуса OCM)
            }

            # Убираем ключи со значением None из defaults,
            # чтобы при обновлении (update_or_create) не перезаписывать
            # существующие значения в базе данных на None, если OCM их не вернул.
            defaults_filtered = {k: v for k, v in defaults.items() if v is not None}

            # --- Создание или обновление записи в БД ---
            try:
                # Используем ocm_id как уникальный идентификатор для поиска/создания
                obj, created = ChargingStation.objects.update_or_create(
                    ocm_id=ocm_id,
                    defaults=defaults_filtered
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                # Логгируем ошибку, если не удалось сохранить/обновить
                self.stderr.write(self.style.ERROR(f"!! Ошибка сохранения станции OCM ID {ocm_id} ({addr_info.get('Title')}): {e}"))
                self.stderr.write(f"  Данные: {defaults_filtered}") # Показываем данные, которые пытались сохранить
                skipped_count += 1

        # --- Финальный отчет ---
        self.stdout.write(self.style.SUCCESS(f"\nПарсинг завершен!"))
        self.stdout.write(f"Всего обработано станций из ответа API: {total_stations}")
        self.stdout.write(self.style.SUCCESS(f"Создано новых записей в БД: {created_count}"))
        self.stdout.write(f"Обновлено существующих записей в БД: {updated_count}")
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f"Пропущено станций (без ID или с ошибкой сохранения): {skipped_count}"))
        else:
             self.stdout.write("Пропущенных станций нет.")