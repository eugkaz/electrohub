
from django.utils import timezone
from django.db import transaction
from .models import Booking, ChargingStation 
import logging

logger = logging.getLogger(__name__)

def update_expired_bookings_and_station_statuses():
    now = timezone.now()
    logger.info(f"Запуск задачі оновлення статусів бронювань та станцій: {now}")

    
    
    expired_bookings = Booking.objects.filter(
        end_time__lte=now,
        status=Booking.BookingStatus.CONFIRMED 
    )

    if not expired_bookings.exists():
        logger.info("Не знайдено підтверджених бронювань, час яких минув, для оновлення.")
        return

    updated_booking_ids = []
    affected_station_ids = set()

    for booking in expired_bookings:
        with transaction.atomic():
            try:
                
                booking.status = Booking.BookingStatus.COMPLETED
                booking.save(update_fields=['status', 'updated_at'])
                updated_booking_ids.append(booking.id)
                affected_station_ids.add(booking.station_id)
                logger.info(f"Бронювання {booking.id} для станції {booking.station_id} оновлено на COMPLETED.")
            except Exception as e:
                logger.error(f"Помилка при оновленні статусу бронювання {booking.id}: {e}")
                

    logger.info(f"Оновлено статуси для бронювань: {updated_booking_ids}")

    
    if affected_station_ids:
        update_charging_station_statuses(list(affected_station_ids))

def update_charging_station_statuses(station_ids=None):
    """
    Оновлює статус доступності для вказаних зарядних станцій або для всіх,
    якщо station_ids не передано.
    """
    if station_ids:
        stations_to_update = ChargingStation.objects.filter(id__in=station_ids)
    else:
        
        stations_to_update = ChargingStation.objects.all() 
    
    logger.info(f"Оновлення статусів для {stations_to_update.count()} станцій.")
    now = timezone.now()

    for station in stations_to_update:
        if station.status in [ChargingStation.AvailabilityStatus.OFFLINE, ChargingStation.AvailabilityStatus.PLANNED]:
            
            logger.info(f"Станція {station.id} ({station.name}) має статус {station.status}, оновлення статусу доступності пропущено.")
            continue

        
        operational_connector_ids = set()
        total_operational_connectors_capacity = 0 
        
        if station.connections_details and isinstance(station.connections_details, list):
            for cd_detail in station.connections_details:
                if cd_detail.get('StatusType', {}).get('IsOperational') is not False:
                    connector_id_from_detail = cd_detail.get('ID')
                    if connector_id_from_detail:
                        operational_connector_ids.add(str(connector_id_from_detail))
                        total_operational_connectors_capacity += cd_detail.get('Quantity', 1)
        
        if total_operational_connectors_capacity == 0 and station.status != ChargingStation.AvailabilityStatus.OFFLINE:
            logger.info(f"Станція {station.id} ({station.name}) не має операційних портів. Встановлюємо статус OFFLINE.")
            station.status = ChargingStation.AvailabilityStatus.OFFLINE
            station.save(update_fields=['status', 'date_last_status_update'])
            continue 

        
        
        current_active_bookings_for_operational_ports = Booking.objects.filter(
            station=station,
            status=Booking.BookingStatus.CONFIRMED, 
            connector_id__in=list(operational_connector_ids),
            start_time__lte=now,
            end_time__gt=now 
        )
        
        num_currently_booked_or_active_ports = current_active_bookings_for_operational_ports.values_list('connector_id', flat=True).distinct().count()
        
        new_station_status = station.status 

        if num_currently_booked_or_active_ports >= total_operational_connectors_capacity:
            
            
            
            
            new_station_status = ChargingStation.AvailabilityStatus.RESERVED 
        elif num_currently_booked_or_active_ports > 0:
            new_station_status = ChargingStation.AvailabilityStatus.PARTIALLY_RESERVED 
        else: 
            new_station_status = ChargingStation.AvailabilityStatus.AVAILABLE
        
        if station.status != new_station_status:
            station.status = new_station_status
            
            station.save(update_fields=['status']) 
            logger.info(f"Статус станції {station.id} ({station.name}) оновлено на {station.get_status_display()}. Операційних портів: {total_operational_connectors_capacity}, Зайнято/заброньовано зараз: {num_currently_booked_or_active_ports}")
        else:
            logger.info(f"Статус станції {station.id} ({station.name}) залишається {station.get_status_display()}. Операційних портів: {total_operational_connectors_capacity}, Зайнято/заброньовано зараз: {num_currently_booked_or_active_ports}")