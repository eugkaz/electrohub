import stripe
import json
import traceback
import logging
from django.conf import settings
from django.db import transaction, DatabaseError
from django.utils import timezone
from django.http import JsonResponse
import requests

from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ImproperlyConfigured

from charge_stations.models import ChargingStation, Booking
from .serializers import (
    ChargingStationSerializer,
    BookingSerializer,
    InitiateBookingSerializer
)

logger = logging.getLogger(__name__)


if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
    logger.critical("CRITICAL: STRIPE_SECRET_KEY is not configured in Django settings!")


else:
    if not (settings.STRIPE_SECRET_KEY.startswith("sk_test_") or settings.STRIPE_SECRET_KEY.startswith("sk_live_")):
        logger.warning("WARNING: STRIPE_SECRET_KEY does not look like a valid test or live key.")
    stripe.api_key = settings.STRIPE_SECRET_KEY



class ChargingStationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ChargingStation.objects.filter(is_active=True).order_by('name')
    serializer_class = ChargingStationSerializer
    permission_classes = [permissions.AllowAny]


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        return Booking.objects.filter(user=self.request.user).select_related('station', 'user').order_by('-start_time')

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def initiate_payment(self, request):
        logger.info(f"Initiate payment request received from user {request.user.id}. Data: {request.data}")
        serializer = InitiateBookingSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            logger.warning(f"Initiate payment validation failed for user {request.user.id}. Errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        validated_data = serializer.validated_data
        station = validated_data['station_id'] 
        start_time = validated_data['start_time']
        end_time = validated_data['end_time']
        amount_stripe = validated_data['calculated_total_amount_stripe']
        amount_main_currency = validated_data['calculated_total_amount_main_currency']
        currency_code = validated_data['currency']
        connector_id_to_save = validated_data['connector_id_to_save']
        
        booking = None
        payment_intent = None

        logger.info(f"Validation successful for user {request.user.id}. Station: {station.id}, Connector: {connector_id_to_save}, Amount (Stripe): {amount_stripe} {currency_code.lower()}")

        try:
            with transaction.atomic():
                logger.info(f"Creating booking for user {request.user.id}, station {station.id}, connector {connector_id_to_save}...")
                booking = Booking.objects.create(
                    user=request.user,
                    station=station,
                    start_time=start_time,
                    end_time=end_time,
                    status=Booking.BookingStatus.PENDING_PAYMENT,
                    total_amount=amount_main_currency,
                    currency=currency_code,
                    connector_id=connector_id_to_save 
                )
                logger.info(f"Booking {booking.id} created for user {request.user.id}. Status: PENDING_PAYMENT.")

                logger.info(f"Attempting to create Stripe PaymentIntent for booking {booking.id}. Amount: {amount_stripe} {currency_code.lower()}.")
                payment_intent_params = {
                    'amount': amount_stripe,
                    'currency': currency_code.lower(),
                    'metadata': {
                        'booking_id': str(booking.id), 
                        'user_id': str(request.user.id),
                        'station_id': str(station.id),
                        'connector_id': str(connector_id_to_save),
                        'description': f"Бронювання станції {station.name} (порт {connector_id_to_save}) на {start_time.strftime('%Y-%m-%d %H:%M')}"
                    },
                    'description': f"Бронювання {station.name} (порт {connector_id_to_save}, ID брон: {booking.id})",
                    'payment_method_types': ['card'],
                }
                logger.debug(f"Stripe PaymentIntent creation params for booking {booking.id}: {payment_intent_params}")
                

                if not stripe.api_key:
                    logger.critical("CRITICAL: Stripe API key is not set before creating PaymentIntent! Check settings.")
                    raise stripe.error.AuthenticationError("Stripe API key is not configured on the server.")

                payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
                
                logger.info(f"Stripe PaymentIntent {payment_intent.id} created successfully for booking {booking.id}.")

                booking.payment_intent_id = payment_intent.id
                booking.save(update_fields=['payment_intent_id'])
                logger.info(f"Booking {booking.id} updated with PaymentIntent ID {payment_intent.id}.")

            response_data = {
                'client_secret': payment_intent.client_secret,
                'booking_id': booking.id,
                'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                'total_amount_display': f"{amount_main_currency:.2f} {currency_code.upper()}"
            }
            logger.info(f"Successfully initiated payment for booking {booking.id}. Booking ID: {response_data['booking_id']}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except stripe.error.AuthenticationError as e:
            logger.critical(f"STRIPE AUTHENTICATION ERROR during payment initiation for user {request.user.id}: {str(e)}. Check your STRIPE_SECRET_KEY.")
            if booking and booking.pk:
                try:
                    booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
                    booking.save(update_fields=['status'])
                    logger.info(f"Booking {booking.id} status set to CANCELLED_SYSTEM due to Stripe Auth error.")
                except DatabaseError as db_err:
                    logger.error(f"Database error while trying to cancel booking {booking.id} after Stripe Auth error: {db_err}")
            return Response({'error': "Помилка конфігурації платіжної системи. Зверніться до підтримки.", 'stripe_error_type': type(e).__name__}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during payment initiation for user {request.user.id} (Booking ID: {booking.id if booking else 'N/A'}). Error: {type(e).__name__} - {str(e)}. HTTP Status: {getattr(e, 'http_status', 'N/A')}. Stripe Code: {getattr(e, 'code', 'N/A')}")
            if booking and booking.pk:
                try:
                    booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
                    booking.save(update_fields=['status'])
                    logger.info(f"Booking {booking.id} status set to CANCELLED_SYSTEM due to Stripe error.")
                except DatabaseError as db_err:
                    logger.error(f"Database error while trying to cancel booking {booking.id} after Stripe error: {db_err}")
            
            error_message_for_client = "Помилка платіжної системи Stripe. Спробуйте, будь ласка, пізніше."
            if hasattr(e, 'user_message') and e.user_message:
                 error_message_for_client = e.user_message
            return Response({'error': error_message_for_client, 'stripe_error_type': type(e).__name__}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Unexpected error during payment initiation for user {request.user.id} (Booking ID: {booking.id if booking else 'N/A'}). Error: {type(e).__name__} - {str(e)}.")
            logger.error(traceback.format_exc())
            if booking and booking.pk and booking.status == Booking.BookingStatus.PENDING_PAYMENT:
                try:
                    booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
                    booking.save(update_fields=['status'])
                    logger.info(f"Booking {booking.id} status set to CANCELLED_SYSTEM due to unexpected error.")
                except DatabaseError as db_err:
                     logger.error(f"Database error while trying to cancel booking {booking.id} after unexpected error: {db_err}")
            return Response({'error': "Внутрішня помилка сервера під час ініціації платежу.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_booking(self, request, pk=None):
        logger.info(f"Confirm booking request received for booking ID {pk} from user {request.user.id}.")
        try:

            booking = Booking.objects.select_related('station').get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            logger.warning(f"Booking ID {pk} not found or does not belong to user {request.user.id}.")
            return Response({'error': 'Бронювання не знайдено або не належить вам.'}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Booking {booking.id} found. Current status: {booking.get_status_display()}.")

        if booking.status == Booking.BookingStatus.CONFIRMED:
            logger.info(f"Booking {booking.id} is already confirmed.")
            station_data = ChargingStationSerializer(booking.station, context={'request': request}).data
            return Response({
                'message': 'Бронювання вже підтверджено.',
                'booking': BookingSerializer(booking, context={'request': request}).data,
                'station': station_data
                }, status=status.HTTP_200_OK)

        if booking.status != Booking.BookingStatus.PENDING_PAYMENT:
            logger.warning(f"Booking {booking.id} is not PENDING_PAYMENT. Status: {booking.get_status_display()}. Cannot confirm.")
            return Response({'error': 'Це бронювання не очікує підтвердження оплати або вже скасоване.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not booking.payment_intent_id:
            logger.error(f"PaymentIntent ID is missing for booking {booking.id}. Cannot confirm.")
            return Response({'error': 'Payment Intent ID не знайдено для цього бронювання. Неможливо підтвердити оплату.'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Attempting to retrieve Stripe PaymentIntent {booking.payment_intent_id} for booking {booking.id}.")
        try:
            if not stripe.api_key:
                logger.critical("CRITICAL: Stripe API key is not set before retrieving PaymentIntent in confirm_booking!")
                raise stripe.error.AuthenticationError("Stripe API key is not configured on the server.")
                
            payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)
            logger.info(f"Stripe PaymentIntent {payment_intent.id} retrieved. Status: {payment_intent.status}.")

            if payment_intent.status == 'succeeded':
                logger.info(f"PaymentIntent {payment_intent.id} status is 'succeeded'. Proceeding with booking confirmation for booking {booking.id}.")
                with transaction.atomic():

                    station_to_book = ChargingStation.objects.select_for_update().get(pk=booking.station.id)
                    current_booking = Booking.objects.select_for_update().get(pk=booking.id) 
                    logger.info(f"Locked station {station_to_book.id} and booking {current_booking.id} for update.")


                    if current_booking.status == Booking.BookingStatus.CONFIRMED:
                        logger.info(f"Booking {current_booking.id} was already confirmed by a parallel request (inside transaction).")
                        station_data_parallel = ChargingStationSerializer(station_to_book, context={'request': request}).data
                        return Response({
                            'message': 'Бронювання вже було підтверджено (паралельний запит).',
                            'booking': BookingSerializer(current_booking, context={'request': request}).data,
                            'station': station_data_parallel
                            }, status=status.HTTP_200_OK)
                    

                    if station_to_book.status == ChargingStation.AvailabilityStatus.OFFLINE:
                        logger.warning(f"Station {station_to_book.id} is OFFLINE. Cancelling booking {current_booking.id}.")
                        current_booking.status = Booking.BookingStatus.CANCELLED_SYSTEM; current_booking.save(update_fields=['status'])


                        logger.info(f"Booking {current_booking.id} status set to CANCELLED_SYSTEM. Refund for PI {current_booking.payment_intent_id} should be initiated.")
                        return Response({'error': f'Станція "{station_to_book.name}" наразі не в мережі. Бронювання скасовано. Кошти будуть повернуті, якщо були списані.'}, status=status.HTTP_409_CONFLICT)


                    if current_booking.connector_id:
                        is_port_operational_now = False
                        connector_exists_now = False
                        if station_to_book.connections_details and isinstance(station_to_book.connections_details, list):
                            for cd in station_to_book.connections_details:
                                if str(cd.get('ID')) == str(current_booking.connector_id):
                                    connector_exists_now = True
                                    if cd.get('StatusType', {}).get('IsOperational') is not False:
                                        is_port_operational_now = True
                                    break
                        if not connector_exists_now:
                            logger.warning(f"Booked connector {current_booking.connector_id} no longer exists on station {station_to_book.id}. Cancelling booking {current_booking.id}.")
                            current_booking.status = Booking.BookingStatus.CANCELLED_SYSTEM; current_booking.save(update_fields=['status'])
                            return Response({'error': 'Обраний для бронювання порт більше не існує на станції. Бронювання скасовано.'}, status=status.HTTP_409_CONFLICT)
                        if not is_port_operational_now:
                            logger.warning(f"Booked connector {current_booking.connector_id} on station {station_to_book.id} is not operational. Cancelling booking {current_booking.id}.")
                            current_booking.status = Booking.BookingStatus.CANCELLED_SYSTEM; current_booking.save(update_fields=['status'])
                            return Response({'error': 'Обраний для бронювання порт став неробочим. Бронювання скасовано.'}, status=status.HTTP_409_CONFLICT)
                        

                        overlapping_on_port = Booking.objects.filter(
                            station=station_to_book,
                            connector_id=current_booking.connector_id,
                            status=Booking.BookingStatus.CONFIRMED,
                            start_time__lt=current_booking.end_time,
                            end_time__gt=current_booking.start_time
                        ).exclude(pk=current_booking.pk).exists()
                        if overlapping_on_port:
                            logger.warning(f"Time slot for booking {current_booking.id} (connector {current_booking.connector_id}) became occupied by another confirmed booking.")
                            current_booking.status = Booking.BookingStatus.CANCELLED_SYSTEM; current_booking.save(update_fields=['status'])
                            return Response({'error': 'На жаль, поки ви оплачували, цей порт на обраний час вже було заброньовано іншим користувачем.'}, status=status.HTTP_409_CONFLICT)
                    

                    current_booking.status = Booking.BookingStatus.CONFIRMED
                    current_booking.save(update_fields=['status'])
                    logger.info(f"Booking {current_booking.id} status successfully set to CONFIRMED.")


                    operational_connector_ids_set = set()
                    total_operational_capacity = 0
                    if station_to_book.connections_details and isinstance(station_to_book.connections_details, list):
                        for cd_detail in station_to_book.connections_details:
                            if cd_detail.get('StatusType', {}).get('IsOperational') is not False:
                                conn_id = cd_detail.get('ID')
                                if conn_id:
                                    operational_connector_ids_set.add(str(conn_id))
                                    total_operational_capacity += cd_detail.get('Quantity', 1)
                    




                    booked_connectors_for_status_update = Booking.objects.filter(
                        station=station_to_book,
                        status=Booking.BookingStatus.CONFIRMED,
                        connector_id__in=list(operational_connector_ids_set),
                        end_time__gt=timezone.now()
                    ).values_list('connector_id', flat=True).distinct()
                    
                    num_currently_booked_operational_ports = len(booked_connectors_for_status_update)
                    
                    new_station_status_val = station_to_book.status 
                    if station_to_book.status not in [ChargingStation.AvailabilityStatus.OFFLINE, ChargingStation.AvailabilityStatus.PLANNED]:
                        if total_operational_capacity == 0:
                            new_station_status_val = ChargingStation.AvailabilityStatus.OFFLINE
                        elif num_currently_booked_operational_ports >= total_operational_capacity:
                            new_station_status_val = ChargingStation.AvailabilityStatus.RESERVED
                        elif num_currently_booked_operational_ports > 0:
                            new_station_status_val = ChargingStation.AvailabilityStatus.PARTIALLY_RESERVED
                        else:
                            new_station_status_val = ChargingStation.AvailabilityStatus.AVAILABLE
                    
                    if station_to_book.status != new_station_status_val:
                        station_to_book.status = new_station_status_val
                        station_to_book.date_last_status_update = timezone.now()
                        station_to_book.save(update_fields=['status', 'date_last_status_update'])
                        logger.info(f"Station {station_to_book.id} status updated to {station_to_book.get_status_display()}. Op. ports: {total_operational_capacity}, Booked op. ports: {num_currently_booked_operational_ports}")
                    else:
                        logger.info(f"Station {station_to_book.id} status remains {station_to_book.get_status_display()}. Op. ports: {total_operational_capacity}, Booked op. ports: {num_currently_booked_operational_ports}")
                

                final_booking_data = BookingSerializer(current_booking, context={'request': request}).data
                final_station_data = ChargingStationSerializer(station_to_book, context={'request': request}).data
                
                response_data_confirm = {
                    'message': 'Бронювання успішно підтверджено та оплачено!',
                    'booking': final_booking_data,
                    'station': final_station_data 
                }
                logger.info(f"Booking {current_booking.id} successfully confirmed. Response sent to user {request.user.id}.")
                return Response(response_data_confirm, status=status.HTTP_200_OK)

            elif payment_intent.status == 'processing':
                 logger.info(f"PaymentIntent {payment_intent.id} for booking {booking.id} is still 'processing'.")
                 return Response({'message': 'Платіж ще обробляється Stripe. Спробуйте перевірити статус пізніше.'}, status=status.HTTP_202_ACCEPTED)
            else: 
                logger.warning(f"PaymentIntent {payment_intent.id} for booking {booking.id} was not successful. Stripe status: {payment_intent.status}.")
                booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
                booking.save(update_fields=['status'])
                logger.info(f"Booking {booking.id} status set to CANCELLED_SYSTEM due to PI status: {payment_intent.status}.")
                error_message = f"Платіж не успішний. Статус Stripe: {payment_intent.status}."
                if payment_intent.last_payment_error and payment_intent.last_payment_error.message:
                    error_message += f" Причина: {payment_intent.last_payment_error.message}"
                return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.AuthenticationError as e:
            logger.critical(f"CRITICAL STRIPE AUTHENTICATION ERROR during booking confirmation for booking {booking.id}: {str(e)}.")
            return Response({'error': "Помилка конфігурації платіжної системи. Зверніться до підтримки.", 'stripe_error_type': type(e).__name__}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during booking confirmation for booking {booking.id} (PI: {booking.payment_intent_id}). Error: {type(e).__name__} - {str(e)}. HTTP Status: {getattr(e, 'http_status', 'N/A')}. Stripe Code: {getattr(e, 'code', 'N/A')}")
            error_message_for_client_confirm = "Помилка платіжної системи Stripe під час перевірки платежу."
            if hasattr(e, 'user_message') and e.user_message:
                 error_message_for_client_confirm = e.user_message
            return Response({'error': error_message_for_client_confirm, 'stripe_error_type': type(e).__name__}, status=status.HTTP_400_BAD_REQUEST)
        except ChargingStation.DoesNotExist:
            logger.error(f"Charging station for booking {booking.id} not found during confirmation (deleted?).")
            if booking.status != Booking.BookingStatus.CONFIRMED : 
                booking.status = Booking.BookingStatus.CANCELLED_SYSTEM
                booking.save(update_fields=['status'])
                logger.info(f"Booking {booking.id} status set to CANCELLED_SYSTEM.")
            return Response({'error': 'Станцію було видалено під час обробки. Бронювання скасовано.'}, status=status.HTTP_404_NOT_FOUND)
        except Booking.DoesNotExist:
             logger.error(f"Booking {pk} not found during confirmation (deleted or changed?).")
             return Response({'error': 'Бронювання було видалено або змінено під час обробки.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unexpected error during booking confirmation for booking {booking.id if 'booking' in locals() and hasattr(booking, 'pk') and booking.pk else pk}. Error: {type(e).__name__} - {str(e)}.")
            logger.error(traceback.format_exc())
            return Response({'error': "Внутрішня помилка сервера під час підтвердження бронювання.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def get_route_view(request):
    logger.info(f"Route request received. Start: ({request.GET.get('start_lat')}, {request.GET.get('start_lon')}), End: ({request.GET.get('end_lat')}, {request.GET.get('end_lon')})")
    ors_api_key = getattr(settings, 'ORS_API_KEY', None)
    if not ors_api_key:
        logger.error("ORS_API_KEY not configured for get_route_view.")
        return JsonResponse({'error': 'ORS API key not configured.'}, status=500)
    start_lat = request.GET.get('start_lat'); start_lon = request.GET.get('start_lon')
    end_lat = request.GET.get('end_lat'); end_lon = request.GET.get('end_lon')
    if not all([start_lat, start_lon, end_lat, end_lon]):
        logger.warning("Missing required parameters for get_route_view.")
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        coordinates = [ [float(start_lon), float(start_lat)], [float(end_lon), float(end_lat)] ]
        for lon, lat_coord in coordinates:
            if not (-90 <= lat_coord <= 90 and -180 <= lon <= 180): raise ValueError("Coordinates out of range")
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid coordinate format or range for get_route_view: {e}")
        return JsonResponse({'error': 'Invalid coordinate format or range.'}, status=400)
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {"Authorization": ors_api_key, "Content-Type": "application/json", "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8"}
    payload = {"coordinates": coordinates}
    logger.info(f"Requesting route from ORS: {url} with payload {payload}")
    response_ors = None
    try:
        response_ors = requests.post(url, json=payload, headers=headers, timeout=20)
        logger.debug(f"ORS response status: {response_ors.status_code}. Response text (first 500 chars): {response_ors.text[:500]}")
        response_ors.raise_for_status() 
        route_data = response_ors.json()
        if 'error' in route_data:
             error_msg = 'Unknown ORS error'; error_detail_data = route_data['error']
             if isinstance(error_detail_data, dict): error_msg = error_detail_data.get('message', error_msg)
             elif isinstance(error_detail_data, str): error_msg = error_detail_data
             logger.warning(f"Error from ORS service: {error_msg}. Full ORS error: {error_detail_data}")
             return JsonResponse({'error': 'Error from routing service', 'details': error_msg}, status=400)
        if route_data.get('type') != 'FeatureCollection' or not isinstance(route_data.get('features'), list) or not route_data['features']:
             logger.warning("No route found or invalid GeoJSON response from ORS.")
             return JsonResponse({'error': 'No route found or invalid GeoJSON response from ORS.'}, status=404)
        route_feature = route_data['features'][0]
        if not route_feature.get('geometry') or not route_feature['geometry'].get('coordinates'):
             logger.error("Route geometry missing in GeoJSON response from ORS.")
             return JsonResponse({'error': 'Route geometry missing in GeoJSON response.'}, status=500)
        logger.info("Successfully retrieved route from ORS.")
        return JsonResponse(route_data, safe=False)
    except requests.exceptions.Timeout:
        logger.error("Routing service (ORS) timed out.")
        return JsonResponse({'error': 'Routing service timed out'}, status=504)
    except requests.exceptions.HTTPError as e:
         error_details = response_ors.text[:500] if response_ors is not None else str(e)
         logger.error(f"Routing service (ORS) HTTPError: {e.response.status_code if e.response else 'N/A'}. Details: {error_details}")
         return JsonResponse({'error': 'Routing service error', 'details': error_details}, status=response_ors.status_code if response_ors is not None else 500)
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection to routing service (ORS) failed: {str(e)}")
        return JsonResponse({'error': 'Connection to routing service failed', 'details': str(e)}, status=503)
    except json.JSONDecodeError:
        error_details_json = response_ors.text[:500] if response_ors is not None else ''
        logger.error(f"Invalid JSON response from ORS. Details: {error_details_json}")
        return JsonResponse({'error': 'Invalid JSON response from ORS', 'details': error_details_json}, status=502)
    except Exception as e:
        logger.error(f"Unexpected server error in get_route_view: {type(e).__name__} - {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({'error': 'Unexpected server error'}, status=500)