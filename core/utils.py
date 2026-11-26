

import time
import requests
import traceback
from django.conf import settings
from django.utils.translation import gettext_lazy as _ 
from decimal import Decimal



AI_API_ENDPOINT = getattr(settings, 'AI_API_ENDPOINT', None)
AI_API_KEY = getattr(settings, 'AI_API_KEY', None)
AI_MODEL_NAME = getattr(settings, 'AI_MODEL_NAME', "gemini-1.5-flash") 
AI_REQUEST_TIMEOUT = 30


def generate_ai_email_content(email_type: str, context_data: dict = None) -> str:
    """
    Генерує текст для email за допомогою Google Gemini API.
    Налаштування API беруться з settings.py.

    Args:
        email_type (str): Тип email (напр., 'newsletter_welcome', 'order_confirm').
        context_data (dict, optional): Дані для персоналізації листа.

    Returns:
        str: Згенерований текст email або повідомлення про помилку.
    """
    
    if not AI_API_ENDPOINT or not AI_API_KEY:
        error_message = _("Помилка конфігурації: Не вдалося зв'язатися з AI сервісом для генерації email.")
        print(f"ERROR: AI email generation config missing in settings.py.")
        return error_message 

    print(f"INFO: [CORE UTILS] Виклик Google Gemini API ({AI_MODEL_NAME}) для генерації email типу '{email_type}'...")

    
    prompt = ""
    if email_type == 'newsletter_welcome':
        subscriber_email = context_data.get('email', 'новий підписник') if context_data else 'новий підписник'
        prompt = f"""
        Ти - копірайтер для інтернет-магазину електротранспорту "ElectroHub" (назву можна адаптувати). Напиши **тільки текст** привітного вітального листа (body) українською мовою для нового підписника розсилки новин ({subscriber_email}).

        Вимоги до тексту:
        - Почни з теплого привітання, звертаючись до спільноти або нового учасника (напр., "Вітаємо у світі ElectroHub!", "Раді бачити вас у нашій еко-родині!").
        - Підтверди успішну підписку на розсилку.
        - Коротко (1-2 речення) окресли, що цікавого чекає на підписника (напр., "дізнавайтесь першими про новинки електротранспорту, отримуйте ексклюзивні поради та спеціальні пропозиції"). НЕ використовуй списки.
        - Заверши позитивним закликом залишатися на зв'язку або очікувати на новини (напр., "Слідкуйте за нашими листами!", "До зустрічі у наступній розсилці!").
        - Тон: Дружній, сучасний, ентузіазм щодо еко-транспорту.
        - Довжина: 4-6 речень. Не включай тему листа або звертання типу "Шановний...".
        """
    
    
    else:
        error_message = _("Помилка: Невідомий тип email ('%(type)s') для генерації AI контенту.") % {'type': email_type}
        print(f"ERROR: Unknown email_type '{email_type}' for AI generation.")
        return error_message

    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 150,
        }
    }
    final_url = f"{AI_API_ENDPOINT}?key={AI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    
    try:
        print(f"DEBUG: [CORE UTILS] Відправка POST-запиту (email) до {final_url}...")
        start_time = time.time()
        response = requests.post(final_url, headers=headers, json=payload, timeout=AI_REQUEST_TIMEOUT)
        duration = time.time() - start_time
        print(f"DEBUG: [CORE UTILS] Запит (email) до Gemini API завершено за {duration:.2f} сек. Статус: {response.status_code}")

        response.raise_for_status()
        response_data = response.json()
        print(f"DEBUG: [CORE UTILS] Отримана відповідь (email) від Gemini API (частково): { str(response_data)[:500] }...")

        
        if "candidates" in response_data and response_data["candidates"]:
            first_candidate = response_data["candidates"][0]
            if "content" in first_candidate and "parts" in first_candidate["content"] and first_candidate["content"]["parts"]:
                ai_summary = first_candidate["content"]["parts"][0].get("text", "").strip()
                if ai_summary:
                    print(f"INFO: [CORE UTILS] Gemini AI email body типу '{email_type}' успішно згенеровано.")
                    
                    if first_candidate.get('finishReason') == 'SAFETY':
                         print(f"WARNING: [CORE UTILS] Email body '{email_type}' згенеровано, але можливе блокування SAFETY.")
                    return ai_summary 
                else: 
                    error_message = _("Помилка: AI сервіс повернув порожній текст для email.")
                    print(f"ERROR: [CORE UTILS] {error_message} Response: {response_data}")
                    return error_message
            
            elif first_candidate.get('finishReason') == 'SAFETY':
                 error_message = _("Помилка: Генерація email заблокована через налаштування безпеки AI.")
                 print(f"ERROR: [CORE UTILS] {error_message} Ratings: {first_candidate.get('safetyRatings')}")
                 return error_message
            
            else:
                 reason = first_candidate.get('finishReason', 'UNKNOWN')
                 error_message = _("Помилка: Не вдалося отримати текст email з відповіді AI (причина: %(reason)s).") % {'reason': reason}
                 print(f"ERROR: [CORE UTILS] {error_message} Response: {response_data}")
                 return error_message
        
        elif "error" in response_data:
             error_details = response_data.get("error", {})
             error_code = error_details.get('code', 'N/A')
             error_api_msg = error_details.get('message', 'Невідома помилка API')
             error_message = _("Помилка від AI сервісу (%(code)s): %(message)s") % {'code': error_code, 'message': error_api_msg}
             print(f"ERROR: [CORE UTILS] {error_message}")
             return error_message
        
        else:
             error_message = _("Помилка: Не вдалося розпізнати текст email у відповіді AI (немає 'candidates').")
             print(f"ERROR: [CORE UTILS] {error_message} Response: {response_data}")
             return error_message

    
    except requests.exceptions.Timeout:
        error_message = _("Помилка: Сервіс AI не відповів вчасно при генерації email.")
        print(f"ERROR: [CORE UTILS] {error_message} Endpoint: {AI_API_ENDPOINT}")
        return error_message
    except requests.exceptions.RequestException as e:
        status_code_str = f" (Статус: {e.response.status_code})" if e.response is not None else ""
        error_message = _("Помилка зв'язку з AI сервісом при генерації email") + status_code_str
        print(f"ERROR: [CORE UTILS] Запит (email) до Gemini API не вдався: {e}{status_code_str}")
        
        return f"{error_message}. Спробуйте пізніше."
    
    except Exception as e:
        error_message = _("Помилка: Сталася непередбачена помилка під час генерації email.")
        print(f"CRITICAL ERROR: [CORE UTILS] Неочікувана помилка під час генерації AI email: {e}\n{traceback.format_exc()}")
        return error_message

def get_exchange_rates_to_uah():
    
    
    return {
        'UAH': Decimal('1.00'),
        'USD': Decimal('39.50'), 
        'EUR': Decimal('42.80'), 
    }
