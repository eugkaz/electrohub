
from django import forms
from django.contrib.auth.forms import UserChangeForm 
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory


from product.models import Product, ProductImage, ProductFeature, Category as ProductCategory, Brand as ProductBrand, Review as ProductReview
from cart.models import Order, OrderItem 
from marketplace.models import Listing, Category as MarketplaceCategory, ListingImage, ListingFeature
from forum.models import UserPost as ForumUserPost, Answer as ForumAnswer, Category as ForumCategory, Author as ForumAuthor
from charge_stations.models import ChargingStation, Booking as StationBooking
from transport.models import ElectricVehicle, VehicleReport
from core.models import Profile, NewsletterSubscriber


default_input_classes = 'form-input block w-full border-gray-300 rounded-md shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-500 focus:ring-opacity-50 text-sm'
default_select_classes = 'form-select block w-full border-gray-300 rounded-md shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-500 focus:ring-opacity-50 text-sm'
default_textarea_classes = 'form-textarea block w-full border-gray-300 rounded-md shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-500 focus:ring-opacity-50 text-sm'
default_checkbox_classes = 'form-checkbox h-4 w-4 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500'
default_file_input_classes = 'form-input block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500'
readonly_input_classes = default_input_classes + ' bg-gray-100 dark:bg-gray-700 cursor-not-allowed'


class UserAdminChangeForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        widgets = {
            'username': forms.TextInput(attrs={'class': readonly_input_classes}),
            'email': forms.EmailInput(attrs={'class': readonly_input_classes}),
            'first_name': forms.TextInput(attrs={'class': readonly_input_classes}),
            'last_name': forms.TextInput(attrs={'class': readonly_input_classes}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect w-full h-32'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect w-full h-32'}),
            'is_active': forms.CheckboxInput(attrs={'class': default_checkbox_classes + ' ml-1'}),
            'is_staff': forms.CheckboxInput(attrs={'class': default_checkbox_classes + ' ml-1'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': default_checkbox_classes + ' ml-1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        readonly_fields = ['username', 'email', 'first_name', 'last_name']
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['readonly'] = True





class UserProfileAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        if 'avatar' in self.fields:
            self.fields['avatar'].widget.attrs['disabled'] = True
            self.fields['avatar'].widget.attrs['class'] = default_file_input_classes + ' cursor-not-allowed opacity-70'
            self.fields['avatar'].help_text = "Зміна аватару на цій сторінці не дозволена."


    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
        }



class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'slug', 'sku', 'description', 'short_description',
            'price', 'original_price', 'in_stock', 'stock_quantity', 'image',
            'part_type', 'brand', 'compatible_models', 'is_active'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': default_select_classes}),
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'slug': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Залишіть порожнім для автогенерації')}),
            'sku': forms.TextInput(attrs={'class': default_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 5}),
            'short_description': forms.TextInput(attrs={'class': default_input_classes}),
            'price': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.01'}),
            'original_price': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.01'}),
            'in_stock': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'stock_quantity': forms.NumberInput(attrs={'class': default_input_classes}),
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes, 'label': _("Головне зображення")}),
            'part_type': forms.Select(attrs={'class': default_select_classes}),
            'brand': forms.Select(attrs={'class': default_select_classes}),
            'compatible_models': forms.SelectMultiple(attrs={'class': 'form-multiselect w-full h-40'}),
            'is_active': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
        }

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'alt_text': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Опис для зображення (SEO)')}),
        }

ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    fields=['image', 'alt_text'],
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class ProductFeatureForm(forms.ModelForm):
    class Meta:
        model = ProductFeature
        fields = ['name', 'value']
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Назва характеристики (напр. Колір)')}),
            'value': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Значення (напр. Червоний)')}),
        }

ProductFeatureFormSet = inlineformset_factory(
    Product,
    ProductFeature,
    form=ProductFeatureForm,
    fields=['name', 'value'],
    extra=1,
    can_delete=True,
    can_delete_extra=True
)



class ProductCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'slug', 'parent', 'image', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'slug': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Залишіть порожнім для автогенерації')}),
            'parent': forms.Select(attrs={'class': default_select_classes}),
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
        }

class ProductBrandAdminForm(forms.ModelForm):
    class Meta:
        model = ProductBrand
        fields = ['name', 'slug', 'logo', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'slug': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Залишіть порожнім для автогенерації')}),
            'logo': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 3}),
        }

class ProductReviewAdminForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['product', 'user', 'text', 'rating', 'is_approved'] 
        widgets = {
            'product': forms.Select(attrs={'class': default_select_classes}),
            'user': forms.Select(attrs={'class': default_select_classes}),
            'text': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 4}),
            'rating': forms.Select(choices=ProductReview.RATING_CHOICES, attrs={'class': default_select_classes}),
            'is_approved': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['product'].disabled = True
            self.fields['user'].disabled = True


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [ 
            'user', 'first_name', 'last_name', 'email', 'phone', 
            'address', 'city', 'zipcode',
            'payment_method', 'status', 



        ]
        widgets = {
            'user': forms.Select(attrs={'class': default_select_classes}),
            'first_name': forms.TextInput(attrs={'class': default_input_classes}),
            'last_name': forms.TextInput(attrs={'class': default_input_classes}),
            'email': forms.EmailInput(attrs={'class': default_input_classes}),
            'phone': forms.TextInput(attrs={'class': default_input_classes}),
            'address': forms.TextInput(attrs={'class': default_input_classes}),
            'city': forms.TextInput(attrs={'class': default_input_classes}),
            'zipcode': forms.TextInput(attrs={'class': default_input_classes}),
            'payment_method': forms.Select(attrs={'class': default_select_classes}),
            'status': forms.Select(attrs={'class': default_select_classes}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['user'].disabled = True 

class OrderItemAdminForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'price_at_purchase', 'quantity']
        widgets = {
            'order': forms.Select(attrs={'class': default_select_classes}),
            'product': forms.Select(attrs={'class': default_select_classes}),
            'price_at_purchase': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': default_input_classes}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['order'].disabled = True
            self.fields['product'].disabled = True 


class ListingAdminForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            'user', 'category', 'title', 'description', 'price', 'currency',
            'is_negotiable', 'condition', 'city', 'contact_name', 'contact_info',
            'main_image', 'status', 'is_active_display',
            'year_of_manufacture', 'brand', 'model_name'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': default_select_classes}),
            'category': forms.Select(attrs={'class': default_select_classes}),
            'title': forms.TextInput(attrs={'class': default_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 5}),
            'price': forms.NumberInput(attrs={'class': default_input_classes, 'step':'0.01'}),
            'currency': forms.Select(attrs={'class': default_select_classes}),
            'is_negotiable': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'condition': forms.Select(attrs={'class': default_select_classes}),
            'city': forms.TextInput(attrs={'class': default_input_classes}),
            'contact_name': forms.TextInput(attrs={'class': default_input_classes}),
            'contact_info': forms.TextInput(attrs={'class': default_input_classes}),
            'main_image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'status': forms.Select(attrs={'class': default_select_classes}),
            'is_active_display': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'year_of_manufacture': forms.NumberInput(attrs={'class': default_input_classes}),
            'brand': forms.TextInput(attrs={'class': default_input_classes}),
            'model_name': forms.TextInput(attrs={'class': default_input_classes}),
        }

class MarketplaceCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = MarketplaceCategory
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'slug': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Автоматично, якщо порожньо')}),
        }

class ListingImageAdminInlineForm(forms.ModelForm):
    class Meta:
        model = ListingImage
        fields = ['image', 'alt_text', 'order']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'alt_text': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('SEO опис зображення')}),
            'order': forms.NumberInput(attrs={'class': default_input_classes, 'placeholder': _('Порядок')}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'order' in self.fields:
            self.fields['order'].required = False


class ListingFeatureAdminInlineForm(forms.ModelForm):
    class Meta:
        model = ListingFeature
        fields = ['name', 'value', 'icon_svg']
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Назва характеристики')}),
            'value': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': _('Значення')}),
            'icon_svg': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 2, 'placeholder': _('Код SVG іконки (необов\'язково)')}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'icon_svg' in self.fields:
            self.fields['icon_svg'].required = False


ListingImageFormSet = inlineformset_factory(
    Listing,
    ListingImage,
    form=ListingImageAdminInlineForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False
)

ListingFeatureFormSet = inlineformset_factory(
    Listing,
    ListingFeature,
    form=ListingFeatureAdminInlineForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False
)


class ForumUserPostAdminForm(forms.ModelForm):
    class Meta:
        model = ForumUserPost
        fields = ['author', 'category', 'title', 'description', 'image'] 
        widgets = {
            'author': forms.Select(attrs={'class': default_select_classes}),
            'category': forms.Select(attrs={'class': default_select_classes}),
            'title': forms.TextInput(attrs={'class': default_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 5}),
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['author'].queryset = ForumAuthor.objects.select_related('user').all()



class ForumAnswerAdminForm(forms.ModelForm):
    class Meta:
        model = ForumAnswer
        fields = ['user_post', 'user', 'content', 'image', 'parent']
        widgets = {
            'user_post': forms.Select(attrs={'class': default_select_classes}),
            'user': forms.Select(attrs={'class': default_select_classes}),
            'content': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'parent': forms.Select(attrs={'class': default_select_classes, 'required': False}), 
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['user_post'].disabled = True
            self.fields['user'].disabled = True
            if self.instance.user_post:
                self.fields['parent'].queryset = ForumAnswer.objects.filter(user_post=self.instance.user_post).exclude(pk=self.instance.pk)
            else:
                self.fields['parent'].queryset = ForumAnswer.objects.none()
        self.fields['parent'].required = False 

class ForumCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = ForumCategory
        fields = ['name', 'description'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 3}),
        }



class ChargingStationAdminForm(forms.ModelForm):
    class Meta:
        model = ChargingStation
        fields = '__all__' 
        exclude = ['ocm_id'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'location': forms.TextInput(attrs={'class': default_input_classes, 'placeholder': 'Point(довгота широта)'}), 
            'address': forms.TextInput(attrs={'class': default_input_classes}),
            'description': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'photo': forms.ClearableFileInput(attrs={'class': default_file_input_classes}),
            'is_reservable': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'status': forms.Select(attrs={'class': default_select_classes}),
            'operating_hours': forms.TextInput(attrs={'class': default_input_classes}),
            'access_type': forms.TextInput(attrs={'class': default_input_classes}),
            'pricing': forms.TextInput(attrs={'class': default_input_classes}),
            'price_per_hour': forms.NumberInput(attrs={'class': default_input_classes, 'step':'0.01'}),
            'photo_url': forms.URLInput(attrs={'class': default_input_classes}),
            'data_provider': forms.TextInput(attrs={'class': default_input_classes}),
            'date_last_status_update': forms.DateTimeInput(attrs={'class': default_input_classes, 'type':'datetime-local'}),
            'connections_details': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 5, 'placeholder': 'JSON-структура деталей конекторів'}),
        }

class StationBookingAdminForm(forms.ModelForm):
    class Meta:
        model = StationBooking
        fields = ['station', 'user', 'connector_id', 'start_time', 'end_time', 'status', 
                  'payment_intent_id', 'total_amount', 'currency']
        widgets = {
            'station': forms.Select(attrs={'class': default_select_classes}),
            'user': forms.Select(attrs={'class': default_select_classes}),
            'connector_id': forms.TextInput(attrs={'class': default_input_classes}),
            'start_time': forms.DateTimeInput(
                attrs={'class': default_input_classes, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'class': default_input_classes, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M' 
            ),
            'status': forms.Select(attrs={'class': default_select_classes}), 
            'payment_intent_id': forms.TextInput(attrs={'class': default_input_classes}),
            'total_amount': forms.NumberInput(attrs={'class': default_input_classes, 'step':'0.01'}),
            'currency': forms.TextInput(attrs={'class': default_input_classes, 'maxlength': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:

            for field_name in ['user', 'station', 'start_time', 'end_time', 'payment_intent_id', 'total_amount', 'currency']:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True



class ElectricVehicleAdminForm(forms.ModelForm):
    class Meta:
        model = ElectricVehicle
        fields = '__all__'
        exclude = ['unique_vehicle_id', 'last_updated'] 
        widgets = {
            'user': forms.Select(attrs={'class': default_select_classes}),
            'name': forms.TextInput(attrs={'class': default_input_classes}),
            'model': forms.TextInput(attrs={'class': default_input_classes}),
            'battery_capacity': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.1'}),
            'current_charge': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.1'}),
            'location': forms.TextInput(attrs={'class': default_input_classes}),
            'is_connected': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
            'is_locked': forms.CheckboxInput(attrs={'class': default_checkbox_classes}),
        }

class VehicleReportAdminForm(forms.ModelForm):
    class Meta:
        model = VehicleReport
        fields = ['vehicle', 'ai_summary', 'charge_at_report', 'location_at_report']

        widgets = {
            'vehicle': forms.Select(attrs={'class': default_select_classes}),
            'ai_summary': forms.Textarea(attrs={'class': default_textarea_classes, 'rows': 5}),
            'charge_at_report': forms.NumberInput(attrs={'class': default_input_classes, 'step': '0.1'}),
            'location_at_report': forms.TextInput(attrs={'class': default_input_classes}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['vehicle'].disabled = True



class NewsletterSubscriberAdminForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email'] 
        widgets = {
            'email': forms.EmailInput(attrs={'class': default_input_classes}),
        }