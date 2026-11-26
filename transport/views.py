import json, uuid
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import ElectricVehicle, VehicleReport
from .forms import ConnectVehicleForm, VehicleUpdateForm
from .utils import get_real_ai_report, generate_pdf_for_report


@csrf_exempt
def update_vehicle_status(request, vehicle_id):
    """
    API endpoint для оновлення статусу транспорту (наприклад, з IoT пристрою).
    Приймає POST запит з JSON.
    """
    vehicle = get_object_or_404(ElectricVehicle, pk=vehicle_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            vehicle.current_charge = data.get('current_charge', vehicle.current_charge)
            vehicle.location = data.get('location', vehicle.location)
            vehicle.is_connected = True
            vehicle.save()
            print(f"SIMULATING: Отримано оновлення статусу для транспорту {vehicle.id}: заряд={vehicle.current_charge}, локація={vehicle.location}")
            return JsonResponse({"message": "Дані транспорту успішно оновлені."})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Невірний формат JSON."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Дозволено тільки POST запити."}, status=405)


@login_required
def vehicle_list(request):
    """
    Показує сторінку зі списком всіх транспортних засобів,
    підключених до поточного користувача.
    """
    vehicles = ElectricVehicle.objects.filter(user=request.user)
    context = {'vehicles': vehicles}
    return render(request, 'transport/vehicle_list.html', context)


@login_required
def connect_vehicle(request):
    if request.method == 'POST':
        form = ConnectVehicleForm(request.POST)
        if form.is_valid():
            vehicle_uuid = form.cleaned_data['vehicle_uuid']
            vehicle_name = form.cleaned_data['vehicle_name']
            
            try:
                vehicle = get_object_or_404(ElectricVehicle, unique_vehicle_id=vehicle_uuid, user__isnull=True)
                vehicle.user = request.user
                vehicle.name = vehicle_name
                vehicle.save(update_fields=['user', 'name'])
                messages.success(request, _(f"Транспорт '{vehicle.get_vehicle_type_display()}' успішно підключено!"))
                return redirect('transport:vehicle_details', pk=vehicle.pk)
            except Http404:
                messages.error(request, _("Помилка: Транспорт не знайдено або він вже зайнятий."))
                return redirect('transport:connect_vehicle')
    
    return render(request, 'transport/connect_vehicle.html')



@login_required
def find_vehicle(request):
    """
    HTMX view для пошуку транспорту за UUID або BLE MAC-адресом.
    """
    identifier = request.GET.get('identifier', '').strip()

    if not identifier:
        return HttpResponse("")

    # Будуємо запит, який шукає або в полі UUID, або в полі BLE MAC
    # iexact - пошук без урахування регістру
    search_query = Q(unique_vehicle_id__iexact=identifier) | Q(ble_mac_address__iexact=identifier)

    try:
        vehicle = ElectricVehicle.objects.get(search_query)
        
        if vehicle.user:
            message = _("Цей транспорт вже у вашому гаражі.") if vehicle.user == request.user else _("Цей транспорт вже прив'язаний до іншого акаунту.")
            return render(request, 'transport/partials/_find_result_error.html', {'message': message})
        else:
            # Знайдено і вільний
            form = ConnectVehicleForm(initial={'vehicle_uuid': vehicle.unique_vehicle_id, 'vehicle_name': vehicle.model})
            context = {'vehicle': vehicle, 'form': form}
            return render(request, 'transport/partials/_find_result_success.html', context)

    except ElectricVehicle.DoesNotExist:
        return render(request, 'transport/partials/_find_result_error.html', {'message': _("Транспорт з таким ID або MAC-адресом не знайдено.")})
    except ElectricVehicle.MultipleObjectsReturned:
        return render(request, 'transport/partials/_find_result_error.html', {'message': _("Помилка: Знайдено декілька пристроїв. Будь ласка, зверніться до підтримки.")})



@login_required
def vehicle_details(request, pk):
    """
    Показує детальну інформацію про конкретний транспортний засіб.
    """
    vehicle = get_object_or_404(ElectricVehicle, pk=pk, user=request.user)
    latest_report = vehicle.reports.order_by('-generated_at').first()
    context = {
        'vehicle': vehicle,
        'latest_report': latest_report
    }
    return render(request, 'transport/vehicle_details.html', context)


class VehicleUpdateView(LoginRequiredMixin, UpdateView):
    """
    Клас для редагування псевдоніму транспортного засобу.
    """
    model = ElectricVehicle
    form_class = VehicleUpdateForm
    template_name = 'transport/vehicle_form.html'
    
    def get_queryset(self):

        return ElectricVehicle.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('transport:vehicle_details', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _("Псевдонім транспорту успішно оновлено."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Редагувати псевдонім")
        return context


class VehicleDeleteView(LoginRequiredMixin, DeleteView):
    """
    Клас для відв'язування транспортного засобу від акаунту.
    Об'єкт не видаляється з БД, а лише очищується поле 'user'.
    """
    model = ElectricVehicle
    template_name = 'transport/vehicle_confirm_delete.html'
    
    def get_queryset(self):
        return ElectricVehicle.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        vehicle = self.get_object()
        vehicle_name = vehicle.name
        vehicle.user = None
        vehicle.save(update_fields=['user'])
        messages.warning(self.request, _(f"Транспорт '{vehicle_name}' було успішно відв'язано від вашого акаунту."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('transport:vehicle_list')


@login_required
@require_POST
def toggle_lock(request, pk):
    """
    HTMX endpoint для перемикання стану блокування.
    """
    vehicle = get_object_or_404(ElectricVehicle, pk=pk, user=request.user)
    vehicle.is_locked = not vehicle.is_locked
    vehicle.save(update_fields=['is_locked'])
    context = {'vehicle': vehicle}
    html = render_to_string('transport/partials/lock_status_button.html', context, request=request)
    return HttpResponse(html)


@login_required
@require_POST
def generate_ai_report_view(request, pk):
    """
    HTMX endpoint для генерації та відображення нового AI-звіту.
    """
    vehicle = get_object_or_404(ElectricVehicle, pk=pk, user=request.user)
    ai_summary_text = get_real_ai_report(vehicle)
    
    new_report = VehicleReport.objects.create(
        vehicle=vehicle,
        ai_summary=ai_summary_text,
        charge_at_report=vehicle.battery_percentage(),
        location_at_report=vehicle.location
    )
    

    vehicle.refresh_from_db() 
    
    context = {'vehicle': vehicle, 'latest_report': new_report}
    html = render_to_string('transport/partials/report_section.html', context, request=request)
    return HttpResponse(html)


@login_required
def download_report_pdf(request, report_id):
    report = get_object_or_404(VehicleReport, pk=report_id, vehicle__user=request.user)

    return generate_pdf_for_report(report)