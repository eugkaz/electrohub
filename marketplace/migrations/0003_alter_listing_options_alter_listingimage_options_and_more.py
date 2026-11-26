# marketplace/migrations/0003_....py (ЗГЕНЕРОВАНИЙ ЗАНОВО ТА ВІДРЕДАГОВАНИЙ)

import django.db.models.deletion
import uuid # Можливо, знадобиться для CreateModel ChatRoom
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
# Імпортуємо slugify
try:
    from slugify import slugify
    print("Using slugify from 'python-slugify' library for migration.")
except ImportError:
    from django.utils.text import slugify
    print("Using slugify from 'django.utils.text' for migration.")

# Функція для генерації slug
def generate_slugs_for_existing_categories(apps, schema_editor):
    Category = apps.get_model('marketplace', 'Category')
    categories_to_update = Category.objects.filter(Q(slug__isnull=True) | Q(slug=''))
    total = categories_to_update.count()
    if total > 0:
        print(f"\n  Generating slugs for {total} existing categories...")
        updated_count = 0
        for category in categories_to_update:
            name_to_slugify = category.name if category.name else f"category-{category.pk}"
            slug = slugify(name_to_slugify)
            if not slug: slug = f"category-{category.pk}"

            original_slug = slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=category.pk).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            Category.objects.filter(pk=category.pk).update(slug=slug)
            updated_count += 1
        print(f"  Finished generating slugs for {updated_count} categories.")
    else:
         print(f"\n  No categories without slug found.")

def remove_slugs(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0002_alter_category_options_alter_listing_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- ЯВНІ КРОКИ ДЛЯ SLUG ---
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, db_index=False, max_length=255, null=True, verbose_name='Посилання (slug)'),
        ),
        migrations.RunPython(generate_slugs_for_existing_categories, remove_slugs),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, default='', max_length=255, unique=True, verbose_name='Посилання (slug)'),
             # Прибрав null=False, бо SlugField не може бути NULL по суті
        ),
        # Додаємо індекс для LIKE окремо, якщо потрібно
        migrations.RunSQL(
             sql='CREATE INDEX IF NOT EXISTS "marketplace_category_slug_like" ON "marketplace_category" ("slug" varchar_pattern_ops);',
             reverse_sql='DROP INDEX IF EXISTS "marketplace_category_slug_like";'
        ),
        # --- КІНЕЦЬ ЗМІН ДЛЯ SLUG ---

        # --- Решта операцій, згенерованих makemigrations ---
        # (Переконайтесь, що тут є всі AddField, RemoveField, CreateModel і т.д.,
        #  які згенерував makemigrations, КРІМ операцій для category.slug)
        migrations.AlterModelOptions(
            name='listing',
            options={'ordering': ['-updated_at', '-created_at'], 'verbose_name': 'Оголошення', 'verbose_name_plural': 'Оголошення'},
        ),
        migrations.AlterModelOptions(
            name='listingimage',
            options={'ordering': ['order', 'pk'], 'verbose_name': 'Додаткове зображення', 'verbose_name_plural': 'Додаткові зображення'},
        ),
        migrations.RemoveField(
            model_name='listing',
            name='image',
        ),
        migrations.RemoveField(
            model_name='listing',
            name='is_active',
        ),
        migrations.RemoveField(
            model_name='listingimage',
            name='created_at',
        ),
        migrations.AddField(
            model_name='listing',
            name='brand',
            field=models.CharField(blank=True, max_length=100, verbose_name='Бренд/Виробник'),
        ),
        migrations.AddField(
            model_name='listing',
            name='condition',
            field=models.CharField(choices=[('new', 'Новий'), ('used_like_new', 'Б/В - як новий'), ('used_good', 'Б/В - добрий стан'), ('used_fair', 'Б/В - задовільний стан'), ('for_parts', 'На запчастини')], default='used_good', max_length=15, verbose_name='Стан'),
        ),
        migrations.AddField(
            model_name='listing',
            name='contact_name',
            field=models.CharField(blank=True, max_length=100, verbose_name="Ім'я контактної особи (необов'язково)"),
        ),
        migrations.AddField(
            model_name='listing',
            name='is_active_display',
            field=models.BooleanField(db_index=True, default=True, verbose_name='Активне (показувати на сайті)'),
        ),
        migrations.AddField(
            model_name='listing',
            name='is_negotiable',
            field=models.BooleanField(default=False, verbose_name='Можливий торг'),
        ),
        migrations.AddField(
            model_name='listing',
            name='main_image',
            field=models.ImageField(blank=True, null=True, upload_to='marketplace/listings/main/', verbose_name='Головне зображення'),
        ),
        migrations.AddField(
            model_name='listing',
            name='model_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Модель'),
        ),
        migrations.AddField(
            model_name='listing',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата оновлення'),
        ),
        migrations.AddField(
            model_name='listing',
            name='views_count',
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name='Кількість переглядів'),
        ),
        migrations.AddField(
            model_name='listing',
            name='year_of_manufacture',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Рік випуску'),
        ),
        migrations.AddField(
            model_name='listingimage',
            name='alt_text',
            field=models.CharField(blank=True, max_length=150, verbose_name='Альтернативний текст (SEO)'),
        ),
        migrations.AddField(
            model_name='listingimage',
            name='order',
            field=models.PositiveIntegerField(default=0, verbose_name='Порядок'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='marketplace.category', verbose_name='Категорія*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='city',
            field=models.CharField(max_length=100, verbose_name='Місто/Регіон*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='contact_info',
            field=models.CharField(max_length=255, verbose_name='Контакт (телефон/email)*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='description',
            field=models.TextField(verbose_name='Детальний опис*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Ціна*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='status',
            field=models.CharField(choices=[('active', 'Активно'), ('sold', 'Продано'), ('archived', 'В архіві')], default='active', max_length=10, verbose_name='Статус оголошення'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='title',
            field=models.CharField(max_length=200, verbose_name='Заголовок*'),
        ),
        migrations.AlterField(
            model_name='listing',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listings', to=settings.AUTH_USER_MODEL, verbose_name='Автор'),
        ),
        migrations.AlterField(
            model_name='listingimage',
            name='image',
            field=models.ImageField(upload_to='marketplace/listings/additional/', verbose_name='Файл зображення'),
        ),
        migrations.AlterField(
            model_name='listingimage',
            name='listing',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='additional_images', to='marketplace.listing', verbose_name='Оголошення'),
        ),
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bought_chat_rooms', to=settings.AUTH_USER_MODEL, verbose_name='Покупець')),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_rooms', to='marketplace.listing', verbose_name='Оголошення')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sold_chat_rooms', to=settings.AUTH_USER_MODEL, verbose_name='Продавець')),
            ],
            options={
                'verbose_name': 'Чат-кімната',
                'verbose_name_plural': 'Чат-кімнати',
                'ordering': ['-updated_at'],
                'unique_together': {('listing', 'buyer')}, # Змінено unique_together
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='Текст повідомлення')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL, verbose_name='Відправник')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='marketplace.chatroom', verbose_name='Кімната')),
            ],
            options={
                'verbose_name': 'Повідомлення чату',
                'verbose_name_plural': 'Повідомлення чатів',
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='ListingFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Назва характеристики')),
                ('value', models.CharField(max_length=255, verbose_name='Значення')),
                ('icon_svg', models.TextField(blank=True, null=True, verbose_name='SVG іконка (опціонально)')),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='marketplace.listing', verbose_name='Оголошення')),
            ],
            options={
                'verbose_name': 'Характеристика',
                'verbose_name_plural': 'Характеристики',
                'ordering': ['name'],
                'unique_together': {('listing', 'name')},
            },
        ),
    ]