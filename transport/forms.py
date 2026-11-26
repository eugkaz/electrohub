from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ElectricVehicle

class ConnectVehicleForm(forms.Form):
    """
    Форма для підключення існуючого транспортного засобу до акаунту користувача
    за його унікальним ідентифікатором (UUID).
    """
    vehicle_uuid = forms.UUIDField(
        label=_("Унікальний ID транспорту"),
        help_text=_("Введіть або відскануйте унікальний ідентифікатор (UUID), вказаний на вашому транспортному засобі."),
        widget=forms.TextInput(attrs={
            'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            'pattern': '[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}',
            'title': 'Введіть дійсний UUID'
        })
    )
    vehicle_name = forms.CharField(
        label=_("Назва (псевдонім)"),
        max_length=100,
        required=True,
        help_text=_("Дайте цьому транспортному засобу зручну назву для відображення у вашому акаунті (напр., 'Мій скутер', 'Робочий електрокар')."),
        widget=forms.TextInput(attrs={'placeholder': _('Напр., Мій скутер')})
    )


class VehicleUpdateForm(forms.ModelForm):
    """
    Форма для редагування псевдоніму транспортного засобу.
    """
    class Meta:
        model = ElectricVehicle
        fields = ['name']
        labels = {
            'name': _('Новий псевдонім (назва)')
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Напр., Мій швидкий самокат')})
        }