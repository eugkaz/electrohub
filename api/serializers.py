from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from charge_stations.models import ChargingStation, Booking
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

User = get_user_model()

class ChargingStationSerializer(GeoFeatureModelSerializer):
    coordinates = serializers.ListField(child=serializers.FloatField(), read_only=True)
    photo_url = serializers.URLField(read_only=True, required=False, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    price_per_hour = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True, required=False, allow_null=True)

    class Meta:
        model = ChargingStation
        geo_field = "location"
        id_field = False
        fields = [
            'id', 'name', 'address', 'description', 'is_active', 'photo_url',
            'is_reservable', 'status', 'status_display', 'operating_hours',
            'access_type', 'pricing', 'price_per_hour', 'coordinates',
            'connections_details', 'data_provider', 'date_last_status_update',
        ]
        read_only_fields = fields


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')


class BookingSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    station_info = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    station = serializers.PrimaryKeyRelatedField(queryset=ChargingStation.objects.all(), write_only=False)
    total_amount_display = serializers.SerializerMethodField(read_only=True)
    connector_details_snapshot = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'station', 'station_info', 'user',
            'start_time', 'end_time', 'created_at',
            'status', 'status_display', 'payment_intent_id',
            'total_amount', 'currency', 'total_amount_display',
            'connector_id', 'connector_details_snapshot'
        ]

        read_only_fields = ['id', 'user', 'station_info', 'status_display', 'payment_intent_id', 'created_at', 'total_amount_display', 'connector_details_snapshot']


    def get_station_info(self, obj):
        if obj.station:
            return {
                'id': obj.station.id,
                'name': obj.station.name,
                'address': obj.station.address,
                'price_per_hour': obj.station.price_per_hour
            }
        return None

    def get_total_amount_display(self, obj):
        if obj.total_amount is not None and obj.currency:
            return f"{obj.total_amount} {obj.currency.upper()}"
        return None
    
    def get_connector_details_snapshot(self, obj):

        if obj.station and obj.connector_id and obj.station.connections_details:
            for conn_detail in obj.station.connections_details:

                if str(conn_detail.get('ID')) == str(obj.connector_id):
                    return {
                        'ID': conn_detail.get('ID'),
                        'ConnectionType': conn_detail.get('ConnectionType', {}).get('Title', 'N/A'),
                        'PowerKW': conn_detail.get('PowerKW', 'N/A'),
                        'CurrentType': conn_detail.get('CurrentType', {}).get('Title', 'N/A'),
                        'StatusAtBooking': conn_detail.get('StatusType', {}).get('Title', 'N/A')
                    }
        return None


class InitiateBookingSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    connector_id = serializers.CharField(required=True, allow_blank=False, max_length=100,
                                         help_text="ID обраного конектора зі списку connections_details станції")

    def validate_station_id(self, value):
        try:
            station = ChargingStation.objects.get(pk=value, is_active=True)
        except ChargingStation.DoesNotExist:
            raise serializers.ValidationError("Станція не знайдена або не активна.")
        
        if not station.is_reservable:
            raise serializers.ValidationError("Обрана станція не підтримує бронювання.")
        
        if station.price_per_hour is None or station.price_per_hour < Decimal('0.01'):
            raise serializers.ValidationError(f"Для станції '{station.name}' не встановлено коректну ціну за годину.")
            
        return station

    def validate_start_time(self, value):

        if value < timezone.now() - timedelta(minutes=2):
            raise serializers.ValidationError("Час початку не може бути у минулому.")

        if value > timezone.now() + timedelta(days=7):
            raise serializers.ValidationError("Час початку не може бути більше ніж на 7 днів у майбутньому.")
        return value

    def validate(self, data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        station = data.get('station_id')
        connector_id_req = data.get('connector_id')

        if not all([start_time, end_time, station, connector_id_req]):

             raise serializers.ValidationError("Необхідно вказати станцію, порт, час початку та закінчення.")

        if start_time >= end_time:
            raise serializers.ValidationError({"end_time": "Час закінчення повинен бути пізніше часу початку."})
        
        MAX_BOOKING_DURATION_HOURS = 4
        MIN_BOOKING_DURATION_MINUTES = 15
        duration = end_time - start_time

        if duration > timedelta(hours=MAX_BOOKING_DURATION_HOURS, minutes=1):
            raise serializers.ValidationError({"time_slot": f"Максимальний час бронювання - {MAX_BOOKING_DURATION_HOURS} годин(и)." })
        
        if duration < timedelta(minutes=MIN_BOOKING_DURATION_MINUTES):
             raise serializers.ValidationError({"time_slot": f"Мінімальний час бронювання - {MIN_BOOKING_DURATION_MINUTES} хвилин."})


        selected_connector_obj = None
        if station.connections_details and isinstance(station.connections_details, list):
            for conn_detail in station.connections_details:

                if str(conn_detail.get('ID')) == str(connector_id_req):
                    selected_connector_obj = conn_detail
                    break
        
        if not selected_connector_obj:
            raise serializers.ValidationError({"connector_id": f"Порт з ID '{connector_id_req}' не знайдено на станції '{station.name}'. Перевірте ID порту."})

        is_operational = selected_connector_obj.get('StatusType', {}).get('IsOperational')
        if is_operational is False:
            conn_type_title = selected_connector_obj.get('ConnectionType', {}).get('Title', connector_id_req)
            raise serializers.ValidationError({"connector_id": f"Обраний порт '{conn_type_title}' наразі не робочий."})
        

        overlapping_connector_bookings = Booking.objects.filter(
            station=station,
            connector_id=str(connector_id_req), 
            status=Booking.BookingStatus.CONFIRMED,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if overlapping_connector_bookings:
            raise serializers.ValidationError({"time_slot": "Обраний час для цього порту вже зайнятий."})
        

        if station.status == ChargingStation.AvailabilityStatus.OFFLINE:
             raise serializers.ValidationError({"station_id": f"Станція '{station.name}' наразі не в мережі і не може бути заброньована."})
        if station.status == ChargingStation.AvailabilityStatus.RESERVED:
             raise serializers.ValidationError({"station_id": f"Станція '{station.name}' наразі повністю заброньована."})
        if station.status == ChargingStation.AvailabilityStatus.OCCUPIED:
             raise serializers.ValidationError({"station_id": f"Станція '{station.name}' наразі повністю зайнята."})



        duration_hours_decimal = Decimal(duration.total_seconds()) / Decimal(3600)
        price_per_hour = station.price_per_hour
        

        total_amount_decimal = (duration_hours_decimal * price_per_hour).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        data['calculated_total_amount_main_currency'] = total_amount_decimal
        data['calculated_total_amount_stripe'] = int(total_amount_decimal * 100)
        data['currency'] = 'UAH' 
        data['connector_id_to_save'] = str(connector_id_req)


        MIN_STRIPE_AMOUNT_CENTS = 500 
        if data['calculated_total_amount_stripe'] < MIN_STRIPE_AMOUNT_CENTS:
            min_amount_display = (Decimal(MIN_STRIPE_AMOUNT_CENTS) / Decimal(100)).quantize(Decimal('0.01'))
            raise serializers.ValidationError({"time_slot": f"Мінімальна сума для оплати становить {min_amount_display} {data['currency'].upper()}."})

        return data