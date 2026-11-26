
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
import logging


from .utils import update_expired_bookings_and_station_statuses 


logger = logging.getLogger(__name__)

def start_scheduler():
    
    if settings.DEBUG and getattr(settings, 'RUNSERVERPLUS_POLLER_RELOADER_RUNNING', False):
        logger.info("APScheduler: RUNSERVERPLUS_POLLER_RELOADER_RUNNING detected, scheduler not started to avoid duplication.")
        return

    try:
        if hasattr(start_scheduler, 'scheduler_running') and start_scheduler.scheduler_running:
            logger.info("APScheduler: Scheduler already seems to be running in this process.")
            return
        
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        
        scheduler.add_job(
            update_expired_bookings_and_station_statuses,
            trigger='interval',
            minutes=5, 
            id='update_booking_statuses_job',
            max_instances=1,
            replace_existing=True,
        )
        logger.info("APScheduler: Задачу 'update_expired_bookings_and_station_statuses' додано до розкладу (кожні 5 хвилин).")
        
        scheduler.start()
        setattr(start_scheduler, 'scheduler_running', True) 
        logger.info("APScheduler: Планувальник запущено.")

    except Exception as e:
        logger.error(f"APScheduler: Помилка запуску планувальника: {e}", exc_info=True)


