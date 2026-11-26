
from django import forms
from django.contrib.auth.forms import UserCreationForm





from django.contrib.auth import get_user_model

from django.utils.translation import gettext_lazy as _
from .models import Profile, NewsletterSubscriber 

User = get_user_model()

class SignUpForm(UserCreationForm):


    email = forms.EmailField(
        max_length=254,
        required=True,
        label=_("E-mail"),
        help_text=_('Обов\'язково. Використовується для входу та відновлення пароля.')

    )
    first_name = forms.CharField(
        max_length=150,
        required=True, 
        label=_("Ім'я")
    )
    last_name = forms.CharField(
        max_length=150,
        required=True, 
        label=_("Прізвище")
    )

    class Meta(UserCreationForm.Meta):
        model = User



        fields = ("username", "first_name", "last_name", "email") 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'username' in self.fields:
            self.fields['username'].label = _("Логін")
            self.fields['username'].help_text = _("Обов'язково. Тільки літери, цифри та @/./+/-/_.")
            
        if 'password1' in self.fields:
            self.fields['password1'].label = _("Пароль")
            self.fields['password1'].help_text = self.fields['password1'].help_text.replace(
                'містити принаймні 8 символів.', 
                'містити принаймні 8 символів, літери та цифри.'
            )

        if 'password2' in self.fields:
            self.fields['password2'].label = _("Повторіть пароль")
        


    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email and User.objects.filter(email__iexact=email).exists():



            raise forms.ValidationError(_("Користувач з такою електронною адресою вже існує."))
        return email


class AvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = { 
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control-file'})
        }

class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введіть ваш email'})
        }