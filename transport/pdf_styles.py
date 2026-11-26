import os
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import navy, black, gray
from reportlab.lib.enums import TA_RIGHT

def register_fonts():
    try:
        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
        bold_font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf')
        
        if os.path.exists(font_path) and os.path.exists(bold_font_path):
            if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_font_path))
                pdfmetrics.registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold', italic=None, boldItalic=None)
                print("INFO: Шрифти DejaVuSans для PDF успішно завантажено.")
        else:
            print("WARNING: Файли шрифтів DejaVuSans не знайдено, буде використано Helvetica.")
    except Exception as e:
        print(f"ERROR: Помилка завантаження шрифтів для PDF: {e}")

def get_styles():
    base_font = 'DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
    bold_font = 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    
    return {
        'h1': ParagraphStyle(name='h1', fontName=bold_font, fontSize=20, leading=24, textColor=navy, alignment=TA_RIGHT),
        'h2': ParagraphStyle(name='h2', fontName=bold_font, fontSize=16, leading=20, spaceAfter=10),
        'h3': ParagraphStyle(name='h3', fontName=bold_font, fontSize=12, leading=16, spaceAfter=8, textColor=navy),
        'body': ParagraphStyle(name='body', fontName=base_font, fontSize=10, leading=14),
        'body_bold': ParagraphStyle(name='body_bold', fontName=bold_font, fontSize=10, leading=14),
        'small_gray': ParagraphStyle(name='small_gray', fontName=base_font, fontSize=8, leading=10, textColor=gray),
    }