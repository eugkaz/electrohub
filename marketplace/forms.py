
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Listing, Category, ListingImage, ListingFeature
from django.forms import inlineformset_factory
from django.utils import timezone


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class ListingForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        label=_("Категорія*"),
        required=True,
        empty_label=_("--- Оберіть категорію ---"),
        widget=forms.Select(attrs={
            
        })
    )

    main_image = forms.ImageField(
        label=_("Головне зображення"),
        required=False, 
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*'
            
        }),
        help_text=_("Це зображення буде відображатись першим. Макс. 5MB.")
    )
    
    

    class Meta:
        model = Listing
        fields = [
            'category', 'title', 'description', 'price', 'currency', 
            'is_negotiable', 'condition', 'city', 'contact_name', 'contact_info',
            'main_image', 
            'year_of_manufacture', 'brand', 'model_name',
            'is_active_display' 
        ]
        
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'year_of_manufacture': forms.NumberInput(), 
            'is_negotiable': forms.CheckboxInput(),
            'is_active_display': forms.CheckboxInput(),
        }
        labels = {
            'title': _("Назва оголошення*"),
            'description': _("Детальний опис*"),
            'price': _("Ціна*"),
            'currency': _("Валюта*"),
            'is_negotiable': _("Можливий торг"),
            'condition': _("Стан*"),
            'city': _("Місто/Регіон*"),
            'contact_name': _("Контактне ім'я"),
            'contact_info': _("Контакт (телефон/email)*"),
            'year_of_manufacture': _("Рік випуску"),
            'brand': _("Бренд/Виробник"),
            'model_name': _("Модель"),
            'is_active_display': _("Опублікувати оголошення (буде видиме іншим)"),
        }
        help_texts = {
            'contact_info': _("Ця інформація буде видима іншим користувачам."),
            'is_active_display': _("Якщо зняти галочку, оголошення буде збережено як чернетка і не буде видимим."),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)

        
        base_input_classes = "w-full py-2.5 px-4 bg-white rounded-lg border border-gray-300 focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-500 focus:outline-none transition duration-150 ease-in-out shadow-sm text-sm placeholder:text-gray-400 disabled:bg-gray-100 disabled:cursor-not-allowed"
        select_classes = base_input_classes.replace("px-4", "pl-4 pr-10") 
        textarea_classes = base_input_classes.replace("py-2.5", "py-3") + " min-h-[100px]"
        checkbox_classes = "h-4 w-4 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500 focus:ring-offset-1"
        file_input_classes = "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:cursor-pointer file:rounded-lg file:border file:border-gray-300 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 file:transition-colors file:duration-150"

        
        self.fields['category'].widget.attrs.update({'class': select_classes})
        self.fields['title'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('Наприклад, Електросамокат Xiaomi Mi Pro 2')})
        self.fields['description'].widget.attrs.update({'class': textarea_classes, 'placeholder': _('Опишіть стан товару, причину продажу, комплектацію тощо...')})
        self.fields['price'].widget.attrs.update({'class': base_input_classes, 'placeholder': '15000'})
        self.fields['currency'].widget.attrs.update({'class': select_classes})
        self.fields['is_negotiable'].widget.attrs.update({'class': checkbox_classes + ' ml-1 mr-2'})
        self.fields['condition'].widget.attrs.update({'class': select_classes})
        self.fields['city'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('Наприклад, Київ')})
        self.fields['contact_name'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('Ваше ім\'я (необов\'язково)')})
        self.fields['contact_info'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('+380 XX XXX XX XX або email')})
        self.fields['main_image'].widget.attrs.update({'class': file_input_classes})
        self.fields['year_of_manufacture'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('РРРР')})
        self.fields['brand'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('Наприклад, Xiaomi, Segway...')})
        self.fields['model_name'].widget.attrs.update({'class': base_input_classes, 'placeholder': _('Наприклад, Mi Pro 2, Ninebot G30...')})
        self.fields['is_active_display'].widget.attrs.update({'class': checkbox_classes + ' ml-1 mr-2'})


        
        if not self.instance or not self.instance.pk:
            self.fields['main_image'].required = True
            self.fields['is_active_display'].initial = True 
            if user and user.is_authenticated:
                if not self.initial.get('contact_name') and (user.get_full_name() or user.username):
                    self.initial['contact_name'] = user.get_full_name() or user.username
                
                
                
                
        else: 
            self.fields['main_image'].required = False


    def clean_year_of_manufacture(self):
        year = self.cleaned_data.get('year_of_manufacture')
        if year is not None: 
            current_year = timezone.now().year
            if not (1900 <= year <= current_year + 1):
                raise ValidationError(
                    _("Вкажіть коректний рік випуску (від 1900 до %(max_year)s).") % {'max_year': current_year + 1}
                )
        return year

    def clean_main_image(self):
        image = self.cleaned_data.get('main_image', False) 
        
        
        
        if not self.instance.pk and self.fields['main_image'].required and not image:
            raise ValidationError(_("Головне зображення є обов'язковим для нового оголошення."))

        
        
        if image and hasattr(image, 'content_type') and hasattr(image, 'size'):
            max_size = 5 * 1024 * 1024 
            allowed_content_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            
            if image.size > max_size:
                raise ValidationError(
                    _("Розмір файлу головного зображення не повинен перевищувати %(size)s MB.") % {'size': max_size // (1024*1024)}
                )
            if image.content_type not in allowed_content_types:
                raise ValidationError(
                    _("Неприпустимий тип файлу для головного зображення. Дозволені: JPEG, PNG, GIF, WebP.")
                )
        elif image is False and self.instance.pk and self.fields['main_image'].required : 
             raise ValidationError(_("Головне зображення є обов'язковим."))
             
        return image


class ListingImageForm(forms.ModelForm):
    class Meta:
        model = ListingImage
        fields = ['image', 'alt_text', 'order', 'id']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file mb-1 text-xs'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control form-control-sm text-xs', 'placeholder': 'Опис (SEO)'}),
            'order': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-xs', 'style': 'width: 60px;', 'min': '0'}),
        }

class ListingFeatureForm(forms.ModelForm):
    class Meta:
        model = ListingFeature
        fields = ['name', 'value', 'id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm mb-1', 'placeholder': 'Характеристика'}),
            'value': forms.TextInput(attrs={'class': 'form-control form-control-sm mb-1', 'placeholder': 'Значення'}),
        }

ListingImageFormSet = inlineformset_factory(
    Listing, ListingImage, form=ListingImageForm,
    extra=1, can_delete=True, can_order=False
)

ListingFeatureFormSet = inlineformset_factory(
    Listing, ListingFeature, form=ListingFeatureForm,
    extra=2, can_delete=True
)