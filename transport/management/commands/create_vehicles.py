import random
from django.core.management.base import BaseCommand
from transport.models import ElectricVehicle, VehicleType

# --- НОВАЯ ФУНКЦИЯ для генерации MAC-адресов ---
def generate_mac_address():
    """Генерирует случайный MAC-адрес в формате XX:XX:XX:XX:XX:XX."""
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6)).upper()
# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---

# ==============================================================================
# СЛОВНИК ДАНИХ ДЛЯ ГЕНЕРАЦІЇ
# ==============================================================================

VEHICLE_DATA = {
    VehicleType.CAR: {
        "models": [
            "Tesla Model Y", "Nissan Leaf", "Hyundai Ioniq 5", "Kia EV6", "Ford Mustang Mach-E",
            "Volkswagen ID.4", "Audi Q4 e-tron", "Porsche Taycan", "Mercedes-Benz EQS", "BMW i4",
            "Rivian R1T", "Lucid Air", "Polestar 2", "Chevrolet Bolt EUV", "Volvo XC40 Recharge"
        ],
        "battery_range": (40.0, 110.0),
    },
    VehicleType.SCOOTER: {
        "models": [
            "Xiaomi Mi 4 Pro", "Ninebot Kickscooter Max G2", "Segway P100S", "Dualtron Thunder 3",
            "Kaabo Wolf King GT", "Inokim OXO", "Niu KQi3 Max", "Apollo Phantom V2",
            "Glion Balto", "Hiboy S2 Pro", "Gotrax GXL V2", "Vsett 10+"
        ],
        "battery_range": (0.4, 2.8),
    },
    VehicleType.BIKE: {
        "models": [
            "Rad Power RadRover 6", "Aventon Aventure.2", "Trek Verve+ 3", "Specialized Turbo Vado 4.0",
            "Giant Stance E+", "Cannondale Topstone Neo SL", "GoCycle G4i", "Ride1Up 700 Series",
            "Lectric XP 3.0", "Canyon Grizl:ON", "Santa Cruz Heckler", "Orbea Rise"
        ],
        "battery_range": (0.5, 1.2),
    },
    VehicleType.MOPED: {
        "models": [
            "Super Soco TC Max", "NIU NQi GTS", "Silence S01", "Horwin EK3", "Vespa Elettrica",
            "Cake Kalk&", "Sur-Ron Light Bee X", "Onyx RCR", "Segway C80"
        ],
        "battery_range": (1.5, 4.5),
    },
    VehicleType.MONOWHEEL: {
        "models": [
            "Inmotion V12", "Begode Master", "Kingsong S22 Eagle", "Veteran Sherman Max",
            "Leaperkim Patton", "Gotway (Begode) EX.N", "Inmotion V11", "Kingsong S18"
        ],
        "battery_range": (0.8, 3.5),
    },
    VehicleType.OTHER: {
        "models": ["Custom Electric Skateboard", "OneWheel GT", "Electric Cargo Trike"],
        "battery_range": (0.6, 5.0),
    }
}

LOCATIONS = [
    "Київ, Майдан Незалежності", "Львів, пл. Ринок", "Одеса, вул. Дерибасівська",
    "Харків, пл. Свободи", "Дніпро, наб. Січеславська", "Івано-Франківськ, вул. Незалежності",
    "Чернівці, вул. О. Кобилянської", "Запоріжжя, пр. Соборний", "Полтава, вул. Соборності",
    "Вінниця, вул. Соборна", "Тернопіль, Театральний майдан", "Ужгород, пл. Театральна"
]

ADJECTIVES = ["Швидкий", "Міський", "Нічний", "Надійний", "Потужний", "Тихий", "Новий", "Мобільний"]
NOUNS = ["Сокіл", "Яструб", "Вітер", "Лист", "Привид", "Стріла", "Мандрівник", "Експлорер"]


# ==============================================================================
# ОСНОВНИЙ КЛАС КОМАНДИ
# ==============================================================================

class Command(BaseCommand):
    help = 'Создает указанное количество случайных электротранспортных средств в базе данных.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--number', '-n',
            type=int,
            default=20, 
            help='Количество транспортных средств для создания',
        )
        parser.add_argument(
            '--type', '-t',
            type=str,
            choices=[v_type.value for v_type in VehicleType],
            help='Создать транспорт только указанного типа (напр., CAR, SCOOTER)',
        )
        
        # --- НОВЫЙ АРГУМЕНТ ---
        parser.add_argument(
            '--no-ble',
            action='store_true',
            help='Создать транспортные средства без BLE MAC-адресов',
        )

    def handle(self, *args, **options):
        count = options['number']
        specific_type_str = options['type']
        no_ble = options['no_ble']

        if specific_type_str:
            types_to_create = [VehicleType(specific_type_str)]
            self.stdout.write(f"Начинаем создание {count} новых транспортных средств типа '{specific_type_str}'...")
        else:
            types_to_create = list(VehicleType)
            self.stdout.write(f"Начинаем создание {count} новых транспортных средств...")
        
        created_count = 0
        for i in range(count):
            vehicle_type = random.choice(types_to_create)
            
            type_data = VEHICLE_DATA.get(vehicle_type)
            if not type_data:
                continue

            model = random.choice(type_data["models"])
            min_cap, max_cap = type_data["battery_range"]
            battery_capacity = round(random.uniform(min_cap, max_cap), 2)
            current_charge = round(random.uniform(0, battery_capacity), 2)
            
            name = f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {i+1}"

            # --- НОВАЯ ЛОГИКА ---
            # Готовим данные для создания объекта
            vehicle_data = {
                'vehicle_type': vehicle_type,
                'name': name,
                'model': model,
                'battery_capacity': battery_capacity,
                'current_charge': current_charge,
                'location': random.choice(LOCATIONS),
                'is_connected': random.choice([True, True, False]), 
                'is_locked': random.choice([True, False]),
            }

            # Добавляем MAC-адрес, если не указан флаг --no-ble
            if not no_ble:
                vehicle_data['ble_mac_address'] = generate_mac_address()
            # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

            try:
                # Создаем объект, передавая словарь с данными
                vehicle = ElectricVehicle.objects.create(**vehicle_data)
                created_count += 1
                
                # Формируем строку для вывода
                mac_info = f"MAC: {vehicle.ble_mac_address}" if vehicle.ble_mac_address else " "
                self.stdout.write(
                    f"  - Создан: {vehicle.get_vehicle_type_display():<15} | "
                    f"Модель: {vehicle.model:<25} | "
                    f"{mac_info:<23} | "
                    f"ID: {vehicle.id}"
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Ошибка при создании транспорта: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nУспешно создано {created_count} из {count} транспортных средств!"))