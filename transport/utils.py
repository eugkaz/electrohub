import time
import random
import os
import requests
import traceback
import io

from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from .models import ElectricVehicle, VehicleReport

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.colors import navy, black, gray, green, orange, red
from reportlab.lib.units import inch

from .pdf_styles import register_fonts, get_styles


AI_API_ENDPOINT = getattr(settings, 'AI_API_ENDPOINT', "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent")
AI_API_KEY = getattr(settings, 'AI_API_KEY', None)
AI_MODEL_NAME = getattr(settings, 'AI_MODEL_NAME', "gemini-1.5-flash")
AI_REQUEST_TIMEOUT = 30


def get_real_ai_report(vehicle: ElectricVehicle) -> str:
    """
    Генерує звіт, викликаючи Google Gemini API.
    Якщо ключ API не налаштовано, повертає симульований звіт.
    """
    if not AI_API_KEY:
        print("WARNING: AI_API_KEY не налаштовано. Використовується симуляція звіту.")
        return simulate_ai_report_generation(vehicle)

    charge = vehicle.battery_percentage()
    location = vehicle.location or "Невідомо"
    last_report_time = vehicle.reports.order_by('-generated_at').first().generated_at if vehicle.reports.exists() else None
    time_since_last_report_str = ""
    if last_report_time:
        time_diff = timezone.now() - last_report_time
        days, hours, minutes = time_diff.days, time_diff.seconds // 3600, (time_diff.seconds // 60) % 60
        if days > 0: time_since_last_report_str = f"{days} д."
        elif hours > 0: time_since_last_report_str = f"{hours} год."
        else: time_since_last_report_str = f"{minutes} хв." if minutes > 0 else "менше хвилини"

    prompt = f"""
    Ти - бортовий аналітик стану електротранспорту. Проаналізуй надані дані та згенеруй короткий (4-6 речень), інформативний звіт українською мовою для власника.

    **Дані про транспортний засіб:**
    *   Тип: {vehicle.get_vehicle_type_display()}
    *   Модель: {vehicle.model}
    *   Назва (псевдонім): {vehicle.name or 'Не вказано'}
    *   Поточний рівень заряду: {charge}%
    *   Останнє відоме місцезнаходження: {location}
    *   Статус підключення до мережі: {'Онлайн' if vehicle.is_connected else 'Офлайн'}
    *   Статус блокування: {'Заблоковано' if vehicle.is_locked else 'Розблоковано'}
    *   Час з моменту попереднього звіту: {time_since_last_report_str if time_since_last_report_str else 'Це перший звіт'}

    **Вимоги до звіту:**
    1.  **Загальна оцінка:** Почни з короткого висновку (напр., "Стан транспорту задовільний.", "Потребує уваги.", "Готовий до використання.").
    2.  **Заряд:** Чітко вкажи на стан заряду (критичний, низький, достатній, повний) і чи вистачить його для типових потреб.
    3.  **Рекомендація:** Дай одну конкретну, дієву пораду власнику (напр., "Рекомендується зарядити найближчим часом.", "Перевірте з'єднання з мережею.", "Можна планувати поїздку.").
    4.  **Стиль:** Лаконічно, зрозуміло, без технічного жаргону, списків чи форматування markdown. Тільки текст.
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 200},
    }
    final_url = f"{AI_API_ENDPOINT}?key={AI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(final_url, headers=headers, json=payload, timeout=AI_REQUEST_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()
        
        if "candidates" in response_data and response_data["candidates"]:
            content = response_data["candidates"][0].get("content", {})
            if "parts" in content and content["parts"]:
                ai_summary = content["parts"][0].get("text", "").strip()
                if ai_summary:
                    return ai_summary
        
        error_message = "Помилка: Не вдалося розпізнати звіт у відповіді Gemini API."
        print(f"ERROR: {error_message} Response: {str(response_data)[:500]}")
        return error_message

    except requests.exceptions.RequestException as e:
        error_message = f"Помилка зв'язку з сервісом Gemini API. Спробуйте пізніше. Деталі: {e}"
        print(f"ERROR: {error_message}")
        return error_message
    except Exception as e:
        error_message = "Помилка: Сталася внутрішня помилка під час генерації звіту."
        print(f"CRITICAL ERROR: Неочікувана помилка під час генерації Gemini звіту: {e}\n{traceback.format_exc()}")
        return error_message


def simulate_ai_report_generation(vehicle: ElectricVehicle) -> str:
    """
    Імітує генерацію AI звіту, якщо реальний API не доступний.
    """
    time.sleep(random.uniform(0.5, 1.2))
    charge = vehicle.battery_percentage()
    
    if charge < 15: summary = "Стан критичний! "; recommendation = "Терміново підключіть до зарядного пристрою!"
    elif charge < 40: summary = "Стан задовільний. "; recommendation = "Рекомендується запланувати зарядку найближчим часом."
    elif charge < 85: summary = "Стан добрий. "; recommendation = "Можна використовувати транспорт без обмежень."
    else: summary = "Стан відмінний! "; recommendation = "Транспорт повністю готовий до будь-якої поїздки."
    
    if not vehicle.is_connected:
        summary += "Увага, транспорт зараз офлайн, дані можуть бути застарілими. "

    return f"{summary}Рівень заряду складає {charge}%. {recommendation}"


def generate_pdf_for_report(report: VehicleReport) -> HttpResponse:
    """
    Генерує красивий PDF звіт для заданого об'єкта VehicleReport.
    """
    register_fonts()
    styles = get_styles()
    
    buffer = io.BytesIO()
    vehicle = report.vehicle

    doc = SimpleDocTemplate(buffer,
                            rightMargin=inch/2, leftMargin=inch/2,
                            topMargin=inch/2, bottomMargin=inch/2,
                            title=f"Звіт для {vehicle.name}")
    story = []

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    logo = Image(logo_path, width=0.8*inch, height=0.8*inch) if os.path.exists(logo_path) else Spacer(0,0)
    
    header_data = [[logo, Paragraph(f"Звіт про стан транспорту", styles['h1'])]]
    header_table = Table(header_data, colWidths=[1*inch, None])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(f"{vehicle.get_vehicle_type_display()}: <b>{vehicle.name}</b> ({vehicle.model})", styles['h2']))
    story.append(Paragraph(f"Власник: {vehicle.user.get_full_name() or vehicle.user.username}", styles['body']))
    story.append(Paragraph(f"Дата звіту: {report.generated_at.strftime('%d.%m.%Y %H:%M')}", styles['small_gray']))
    story.append(Spacer(1, 0.3*inch))

    charge_perc = report.charge_at_report or 0
    
    stats_data = [
        [Paragraph('Рівень заряду', styles['body_bold']), Paragraph(f'{charge_perc}%', styles['body'])],
        [Paragraph('Локація', styles['body_bold']), Paragraph(report.location_at_report or "Невідомо", styles['body'])],
        [Paragraph('Статус підключення', styles['body_bold']), Paragraph('Онлайн' if vehicle.is_connected else 'Офлайн', styles['body'])],
    ]
    stats_table = Table(stats_data, colWidths=[2*inch, None])
    stats_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, gray),
        ('BACKGROUND', (0,0), (0,-1), '#f0f0f0'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Аналіз та рекомендації від AI", styles['h3']))
    story.append(Paragraph(report.ai_summary.replace('\n', '<br/>'), styles['body']))

    doc.build(story)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"report_{vehicle.name.replace(' ', '_')}_{report.id}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response.write(pdf)
    return response