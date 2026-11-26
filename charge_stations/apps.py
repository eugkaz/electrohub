
from django.apps import AppConfig
import os 
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ChargeStationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'charge_stations'

    def ready(self):
        
        
        
        
        if os.environ.get('RUN_MAIN') == 'true' and 'django_apscheduler' in settings.INSTALLED_APPS:
            from . import jobs 
            try:
                logger.info("ChargeStationsConfig.ready(): Спроба запуску APScheduler...")
                jobs.start_scheduler()
            except Exception as e:
                logger.error(f"ChargeStationsConfig.ready(): Помилка при запуску APScheduler: {e}", exc_info=True)
        elif 'django_apscheduler' not in settings.INSTALLED_APPS:
             logger.warning("ChargeStationsConfig.ready(): django_apscheduler не в INSTALLED_APPS, планувальник не запущено.")
        else:
             logger.info("ChargeStationsConfig.ready(): RUN_MAIN не 'true', APScheduler не запущено (можливо, це manage.py команда або autoreloader).")