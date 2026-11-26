
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.forms import inlineformset_factory, ModelForm
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from administration import forms 


from product.models import Product, Category as ProductCategory, Brand as ProductBrand, Review as ProductReview
from cart.models import Order, OrderItem
from marketplace.models import Listing, Category as MarketplaceCategory, ListingImage, ListingFeature
from forum.models import UserPost as ForumUserPost, Answer as ForumAnswer, Category as ForumCategory, Author as ForumAuthor
from charge_stations.models import ChargingStation, Booking as StationBooking
from transport.models import ElectricVehicle, VehicleReport
from core.models import Profile, NewsletterSubscriber
from django.contrib.auth.models import User


from .forms import (
    ProductAdminForm, ProductImageFormSet, ProductFeatureFormSet, ProductCategoryAdminForm, ProductBrandAdminForm, ProductReviewAdminForm,
    OrderAdminForm,
    ListingAdminForm, MarketplaceCategoryAdminForm,

    ForumUserPostAdminForm, ForumAnswerAdminForm, ForumCategoryAdminForm,
    ChargingStationAdminForm, StationBookingAdminForm,
    ElectricVehicleAdminForm, VehicleReportAdminForm,
    UserProfileAdminForm, UserAdminChangeForm,
    NewsletterSubscriberAdminForm
)

import logging
logger = logging.getLogger(__name__)




class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    login_url = getattr(settings, 'LOGIN_URL', 'login')
    redirect_field_name = 'next'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, _(
            "У вас немає прав доступу до цієї сторінки."))
        if not self.request.user.is_authenticated:
            return redirect(self.get_login_url())

        return redirect(reverse('frontpage'))


def superuser_required_decorator(view_func):
    decorated_view = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url=getattr(settings, 'LOGIN_URL', 'login'),
        redirect_field_name='next'
    )(view_func)
    return decorated_view


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = getattr(settings, 'LOGIN_URL', 'login')
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
    def handle_no_permission(self):
        messages.error(self.request, _("У вас немає прав персоналу для доступу до цієї сторінки."))
        if not self.request.user.is_authenticated: return redirect(self.get_login_url())
        return redirect(reverse('frontpage'))


def staff_required_decorator(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url=getattr(settings, 'LOGIN_URL', 'login')
    )(view_func)

def superuser_required_decorator(view_func): 
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url=getattr(settings, 'LOGIN_URL', 'login')
    )(view_func)



@staff_required_decorator
def dashboard_view(request):
    stats = {} 
    user = request.user 


    if user.has_perm('core.view_user_stats') or user.is_superuser:
        stats['total_users'] = User.objects.count()




    if user.has_perm('product.view_product_stats') or user.is_superuser: 
        stats['total_products'] = Product.objects.count()




    if user.has_perm('cart.view_order_stats') or user.is_superuser: 
        stats['total_orders'] = Order.objects.count()
        stats['pending_orders'] = Order.objects.filter(status=Order.OrderStatus.PENDING).count()
        stats['processing_orders'] = Order.objects.filter(status=Order.OrderStatus.PROCESSING).count()
        stats['paid_orders'] = Order.objects.filter(status=Order.OrderStatus.PAID).count()




    if user.has_perm('marketplace.view_listing_stats') or user.is_superuser: 
        stats['total_listings'] = Listing.objects.count()
        stats['active_listings'] = Listing.objects.filter(status='active', is_active_display=True).count() 



    if user.has_perm('charge_stations.view_station_stats') or user.is_superuser: 
        stats['total_charging_stations'] = ChargingStation.objects.count()
        stats['active_charging_stations'] = ChargingStation.objects.filter(is_active=True).count()



    if user.has_perm('forum.view_forum_stats') or user.is_superuser: 
        stats['forum_topics'] = ForumUserPost.objects.count()
        stats['forum_answers'] = ForumAnswer.objects.count()



    if user.has_perm('core.view_subscriber_stats') or user.is_superuser: 
        stats['newsletter_subscribers'] = NewsletterSubscriber.objects.count()


    if user.has_perm('transport.view_vehicle_stats') or user.is_superuser: 
        stats['active_vehicles'] = ElectricVehicle.objects.count() 



    if not stats and not user.is_superuser:
        stats['greeting'] = _("Вітаємо! У вас поки немає доступу до статистичних даних.")
    elif not stats and user.is_superuser: 
        stats['info'] = _("Статистика для суперкористувача не завантажилась. Перевірте налаштування дозволів або логіку збору статистики.")





    recent_orders = []
    if user.has_perm('cart.view_order') or user.is_superuser: 
        recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]

    recent_listings = []
    if user.has_perm('marketplace.view_listing') or user.is_superuser: 
        recent_listings = Listing.objects.select_related('user', 'category').order_by('-updated_at')[:5]

    recent_users = []
    if user.has_perm('auth.view_user') or user.is_superuser: 
        recent_users = User.objects.order_by('-date_joined')[:5]








    all_sidebar_menu_items = [
        {
            'menu_title': _("Користувачі"), 'icon_svg_path': "...", 'current_url_prefix': "user_",
            'required_perm_group': 'auth.view_user', 
            'sub_items_list': [
                {"url_name": "administration:user_list", "title": _("Всі користувачі"), 'required_perm': 'auth.view_user'},

            ]
        },
        {
            'menu_title': _("Магазин"), 'icon_svg_path': "...", 'current_url_prefix': "product",
            'required_perm_group': 'product.view_product',
            'sub_items_list': [
                {"url_name": "administration:product_list", "title": _("Товари"), 'required_perm': 'product.view_product'},
                {"url_name": "administration:productcategory_list", "title": _("Категорії товарів"), 'required_perm': 'product.view_category'},
                {"url_name": "administration:productbrand_list", "title": _("Бренди"), 'required_perm': 'product.view_brand'},
                {"url_name": "administration:productreview_list", "title": _("Відгуки на товари"), 'required_perm': 'product.view_review'},

            ]
        },
        {
            'menu_title': _("Замовлення"), 'icon_svg_path': "...", 'current_url_prefix': "order_",
            'required_perm_group': 'cart.view_order',
            'sub_items_list': [
                {"url_name": "administration:order_list", "title": _("Всі замовлення"), 'required_perm': 'cart.view_order'},
            ]
        },
        {
            'menu_title': _("Приватні продажі"), 'icon_svg_path': "...", 'current_url_prefix': "listing_",
            'required_perm_group': 'marketplace.view_listing',
            'sub_items_list': [
                {"url_name": "administration:listing_list", "title": _("Оголошення"), 'required_perm': 'marketplace.view_listing'},
                {"url_name": "administration:marketplacecategory_list", "title": _("Категорії МП"), 'required_perm': 'marketplace.view_category'},
            ]
        },
        {
            'menu_title': _("Форум"), 'icon_svg_path': "...", 'current_url_prefix': "forum",
            'required_perm_group': 'forum.view_userpost', 
            'sub_items_list': [
                {"url_name": "administration:forumuserpost_list", "title": _("Теми"), 'required_perm': 'forum.view_userpost'},
                {"url_name": "administration:forumanswer_list", "title": _("Відповіді"), 'required_perm': 'forum.view_answer'},
                {"url_name": "administration:forumcategory_list", "title": _("Категорії Форуму"), 'required_perm': 'forum.view_category'},
            ]
        },
        {
            'menu_title': _("Зарядні Станції"), 'icon_svg_path': "...", 'current_url_prefix': "chargingstation_",
            'required_perm_group': 'charge_stations.view_chargingstation',
            'sub_items_list': [
                {"url_name": "administration:chargingstation_list", "title": _("Станції"), 'required_perm': 'charge_stations.view_chargingstation'},
                {"url_name": "administration:chargingstation_create", "title": _("Додати станцію"), 'required_perm': 'charge_stations.add_chargingstation'},
                {"url_name": "administration:stationbooking_list", "title": _("Бронювання"), 'required_perm': 'charge_stations.view_booking'}, 
            ]
        },
        {
            'menu_title': _("Транспорт"), 'icon_svg_path': "...", 'current_url_prefix': "electricvehicle_",
            'required_perm_group': 'transport.view_electricvehicle',
            'sub_items_list': [
                {"url_name": "administration:electricvehicle_list", "title": _("ТЗ Користувачів"), 'required_perm': 'transport.view_electricvehicle'},
                {"url_name": "administration:electricvehicle_create", "title": _("Додати ТЗ"), 'required_perm': 'transport.add_electricvehicle'},

            ]
        },
        {
            'menu_title': _("Підписки"), 'icon_svg_path': "...", 'current_url_prefix': "newsletter_",
            'required_perm_group': 'core.view_newslettersubscriber',
            'sub_items_list': [
                {"url_name": "administration:newslettersubscriber_list", "title": _("Підписники на новини"), 'required_perm': 'core.view_newslettersubscriber'},
            ]
        }
    ]

    sidebar_menu_items = []
    for item in all_sidebar_menu_items:
        has_group_perm_code = item.get('required_perm_group')
        can_access_group = user.is_superuser or \
                           (not has_group_perm_code or user.has_perm(has_group_perm_code))

        if can_access_group:
            filtered_sub_items = []
            for sub_item in item.get('sub_items_list', []):
                sub_item_perm_code = sub_item.get('required_perm')
                if user.is_superuser or (not sub_item_perm_code or user.has_perm(sub_item_perm_code)):
                    filtered_sub_items.append(sub_item)
            
            if filtered_sub_items or not item.get('sub_items_list'): 
                item['sub_items_list'] = filtered_sub_items
                sidebar_menu_items.append(item)

    context = {
        'page_title': _('Головна Панель Адміністратора'),
        'stats': stats,
        'recent_orders': recent_orders,
        'recent_listings': recent_listings,
        'recent_users': recent_users,
        'sidebar_main_menu_items': sidebar_menu_items,
        'OrderStatus': Order.OrderStatus, 
    }
    return render(request, 'administration/dashboard.html', context)






class UserListView(SuperUserRequiredMixin, ListView):
    model = User
    template_name = 'administration/user_list.html'
    context_object_name = 'users_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by(
            'username').prefetch_related('profile') 



        search_query = self.request.GET.get('q')
        is_staff_filter = self.request.GET.get('is_staff')
        is_active_filter = self.request.GET.get('is_active')

        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) | Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) | Q(
                    last_name__icontains=search_query)
            )
        if is_staff_filter:
            queryset = queryset.filter(is_staff=(is_staff_filter == 'true'))
        if is_active_filter:
            queryset = queryset.filter(is_active=(is_active_filter == 'true'))



        return queryset.annotate(orders_count_ann=Count('orders'))


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Управління Користувачами')
        context['search_query'] = self.request.GET.get('q', '')
        context['is_staff_filter'] = self.request.GET.get('is_staff', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        return context


class UserUpdateView(SuperUserRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminChangeForm
    template_name = 'administration/user_form.html'

    def get_success_url(self):
        return reverse_lazy('administration:user_detail_admin', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _(
            'Редагувати Користувача: {}').format(self.object.username)
        context['form_title'] = _(
            'Редагування статусу та прав користувача @{}').format(self.object.username) 
        context['button_text'] = _('Зберегти зміни')
        context['back_url'] = reverse_lazy('administration:user_list')

        profile_instance = getattr(self.object, 'profile', None)
        if self.request.POST:

            context['profile_form'] = UserProfileAdminForm(
                self.request.POST, self.request.FILES, instance=profile_instance, prefix="profile", user_instance=self.object)
        else:
            context['profile_form'] = UserProfileAdminForm(
                instance=profile_instance, prefix="profile", user_instance=self.object)
        return context

    @transaction.atomic
    def form_valid(self, form):

        original_user = User.objects.get(pk=self.object.pk)

        user = form.save(commit=False)


        user.username = original_user.username
        user.email = original_user.email
        user.first_name = original_user.first_name
        user.last_name = original_user.last_name


        user.save()  
        form.save_m2m() 




        profile_instance = getattr(user, 'profile', None)












        messages.success(self.request, _(
            "Статус та права користувача «{}» успішно оновлено.").format(user.username))
        return HttpResponseRedirect(self.get_success_url())


class UserDetailView(SuperUserRequiredMixin, DetailView):
    model = User
    template_name = 'administration/user_detail_admin.html'
    context_object_name = 'target_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_user = self.object
        context['page_title'] = _(
            'Профіль Користувача: {}').format(target_user.username)





        return context




class ProductListView(SuperUserRequiredMixin, ListView):
    model = Product
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'brand').order_by('-created_at')
        q = self.request.GET.get('q')
        cat_f = self.request.GET.get('category')
        brand_f = self.request.GET.get('brand')
        stock_f = self.request.GET.get('in_stock')
        conditions = []
        if q:
            conditions.append(Q(name__icontains=q) | Q(sku__iexact=q) | Q(brand__name__icontains=q) | Q(description__icontains=q))
        if cat_f and cat_f.isdigit():
            conditions.append(Q(category_id=cat_f))
        if brand_f and brand_f.isdigit():
            conditions.append(Q(brand_id=brand_f))
        if stock_f:
            conditions.append(Q(in_stock=(stock_f == 'true')))
        if conditions:
            qs = qs.filter(*conditions)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'page_title': _('Управління Товарами'),
            'search_query': self.request.GET.get('q', ''),
            'list_fields': [
                ('id', _('ID')),
                ('get_thumbnail_html_small_admin', _('Фото')),
                ('name_link_admin', _('Назва')),
                ('category', _('Категорія')),
                ('price_display_admin', _('Ціна')),
                ('in_stock_display_admin', _('В наявності')),
                ('updated_at|date:"d.m.Y H:i"', _('Оновлено'))
            ],
            'model_name_plural': _("Товари"),
            'model_name_singular': _("Товар"),
            'create_url_name': 'administration:product_create',
            'update_url_name': 'administration:product_update',
            'delete_url_name': 'administration:product_delete',
            'list_url_name': 'administration:product_list',
            'categories_for_filter': ProductCategory.objects.all(),
            'brands_for_filter': ProductBrand.objects.all(),
            'current_category_filter': self.request.GET.get('category', ''),
            'current_brand_filter': self.request.GET.get('brand', ''),
            'current_in_stock_filter': self.request.GET.get('in_stock', '')
        })
        for obj in ctx['objects']:
            setattr(obj, 'get_thumbnail_html_small_admin', lambda o=obj: format_html('<img src="{}" alt="{}" style="width:50px; height:50px; object-fit:cover; border-radius:4px;" />', o.get_thumbnail(), o.name) if o.get_thumbnail() else "-")
            setattr(obj, 'name_link_admin', lambda o=obj: format_html('<a href="{}" class="hover:text-yellow-600 font-medium dark:hover:text-yellow-400">{}</a>', reverse('administration:product_update', args=[o.pk]), o.name))
            setattr(obj, 'price_display_admin', f"{obj.price} {getattr(obj, 'currency_symbol', 'грн')}")
            setattr(obj, 'in_stock_display_admin', format_html('<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {}">{}</span>', "bg-green-100 text-green-800 dark:bg-green-700/30 dark:text-green-300" if obj.in_stock else "bg-red-100 text-red-800 dark:bg-red-700/30 dark:text-red-300", _("Так") if obj.in_stock else _("Ні")))
        return ctx

class ProductCreateView(SuperUserRequiredMixin, CreateView):
    model = Product
    form_class = ProductAdminForm
    template_name = 'administration/product_form_with_images.html'
    success_url = reverse_lazy('administration:product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['images_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES, prefix='images')
            context['features_formset'] = ProductFeatureFormSet(self.request.POST, prefix='features')
        else:
            context['images_formset'] = ProductImageFormSet(prefix='images')
            context['features_formset'] = ProductFeatureFormSet(prefix='features')
        context.update({
            'page_title': _('Додати Новий Товар'),
            'form_title': _('Створення товару'),
            'button_text': _('Створити товар'),
            'back_url': self.success_url
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        images_formset = context['images_formset']
        features_formset = context['features_formset']

        if images_formset.is_valid() and features_formset.is_valid():
            try:
                with transaction.atomic():
                    self.object = form.save()
                    images_formset.instance = self.object
                    images_formset.save()
                    features_formset.instance = self.object
                    features_formset.save()
                messages.success(self.request, _("Товар «{}» успішно створено з зображеннями та характеристиками.").format(self.object.name))
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, _("Сталася помилка під час збереження: {}").format(e))
                return self.form_invalid(form)
        else:
            error_messages = []
            if not form.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі товару."))
            if not images_formset.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі зображень."))
            if not features_formset.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі характеристик."))
            messages.error(self.request, " ".join(error_messages))
            return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        if not form.is_valid():
            messages.error(self.request, _("Будь ласка, виправте помилки у основній формі товару."))
        return self.render_to_response(context)

class ProductUpdateView(SuperUserRequiredMixin, UpdateView):
    model = Product
    form_class = ProductAdminForm
    template_name = 'administration/product_form_with_images.html'
    success_url = reverse_lazy('administration:product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['images_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='images')
            context['features_formset'] = ProductFeatureFormSet(self.request.POST, instance=self.object, prefix='features')
        else:
            context['images_formset'] = ProductImageFormSet(instance=self.object, prefix='images')
            context['features_formset'] = ProductFeatureFormSet(instance=self.object, prefix='features')
        context.update({
            'page_title': _('Редагувати Товар: {}').format(self.object.name),
            'form_title': _('Редагування товару #{}').format(self.object.pk),
            'button_text': _('Зберегти зміни'),
            'back_url': self.success_url
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        images_formset = context['images_formset']
        features_formset = context['features_formset']

        if images_formset.is_valid() and features_formset.is_valid():
            try:
                with transaction.atomic():
                    self.object = form.save()
                    images_formset.instance = self.object
                    images_formset.save()
                    features_formset.instance = self.object
                    features_formset.save()
                messages.success(self.request, _("Товар «{}» успішно оновлено.").format(self.object.name))
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, _("Сталася помилка під час оновлення: {}").format(e))
                return self.form_invalid(form)
        else:
            error_messages = []
            if not form.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі товару."))
            if not images_formset.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі зображень."))
            if not features_formset.is_valid():
                 error_messages.append(_("Будь ласка, виправте помилки у формі характеристик."))
            messages.error(self.request, " ".join(error_messages))
            return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        if not form.is_valid():
            messages.error(self.request, _("Будь ласка, виправте помилки у основній формі товару."))
        return self.render_to_response(context)



class ProductDeleteView(SuperUserRequiredMixin, DeleteView):
    model = Product
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:product_list')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити Товар: {}').format(
    self.object.name), 'object_type_display': Product._meta.verbose_name.capitalize(), 'object_name': self.object.name, 'cancel_url': self.success_url}); return ctx
    
    def post(self, request, *args, **kwargs): name = self.get_object().name; resp = super().delete(request, *args, **
                                                                                               kwargs); messages.success(self.request, _("{} «{}» успішно видалено.").format(Product._meta.verbose_name.capitalize(), name)); return resp




class ProductCategoryListView(SuperUserRequiredMixin, ListView):
    model = ProductCategory
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20
    
    def get_queryset(self): return super().get_queryset().annotate(
    product_count_ann=Count('products')).order_by('name')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Категорії Товарів'), 'list_fields': ['name', 'slug', 'parent', 'product_count_ann', 'is_active_display'], 'model_name_plural': _("Категорії товарів"), 'model_name_singular': _(
    "Категорію товарів"), 'create_url_name': 'administration:productcategory_create', 'update_url_name': 'administration:productcategory_update', 'delete_url_name': 'administration:productcategory_delete'}); [setattr(obj, 'is_active_display', _("Так")if obj.is_active else _("Ні"))for obj in ctx['objects']]; return ctx


class ProductCategoryCreateView(SuperUserRequiredMixin, CreateView):
    model = ProductCategory
    form_class = ProductCategoryAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:productcategory_list')


def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _(
    'Створити Категорію Товарів'), 'form_title': _('Нова категорія товарів'), 'button_text': _('Створити'), 'back_url': self.success_url}); return ctx


def form_valid(self, form): messages.success(self.request, _(
    "Категорію «{}» створено.").format(form.instance.name)); return super().form_valid(form)


class ProductCategoryUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ProductCategory
    form_class = ProductCategoryAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:productcategory_list')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Редагувати Категорію: {}').format(self.object.name), 'form_title': _('Редагування категорії #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return ctx; 
    
    def form_valid(self, form): messages.success(self.request, _("Категорію «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)


class ProductCategoryDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ProductCategory
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:productcategory_list')
    
    def get_context_data(self, **kwargs): 
        ctx = super().get_context_data(**kwargs); 
        ctx.update({'page_title': _('Видалити: {}').format(self.object.name), 'object_type_display': _('Категорію товарів'), 'object_name': 
            self.object.name, 'cancel_url': self.success_url}); 
        return ctx; 
    def post(self, request, *args, **kwargs): 
        name = self.get_object().name; resp = super().delete(request, *args, **kwargs); 
        messages.success(self.request, _("Категорію «{}» видалено.").format(name)); 
        return resp



class OrderListView(SuperUserRequiredMixin, ListView):
    model = Order
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user').order_by('-created_at')
        search_query = self.request.GET.get('q')
        status_query = self.request.GET.get('status')

        conditions = []
        if search_query:
            q_objects = Q(id__iexact=search_query)
            if hasattr(Order, 'user') and Order._meta.get_field('user').remote_field.model._meta.get_field('username'):
                 q_objects |= Q(user__username__icontains=search_query)
            if hasattr(Order, 'user') and Order._meta.get_field('user').remote_field.model._meta.get_field('email'):
                 q_objects |= Q(user__email__icontains=search_query)
            if hasattr(Order, 'first_name'): q_objects |= Q(first_name__icontains=search_query)
            if hasattr(Order, 'last_name'): q_objects |= Q(last_name__icontains=search_query)
            if hasattr(Order, 'phone'): q_objects |= Q(phone__icontains=search_query)
            if hasattr(Order, 'stripe_payment_intent_id'): q_objects |= Q(stripe_payment_intent_id__icontains=search_query)
            conditions.append(q_objects)

        if status_query and hasattr(Order, 'status'):
            conditions.append(Q(status=status_query))

        if conditions:
            final_q_object = Q()
            for cond in conditions:
                if cond:
                    final_q_object &= cond
            if final_q_object:
                queryset = queryset.filter(final_q_object)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Управління Замовленнями')
        context['search_query'] = self.request.GET.get('q', '')
        context['status_query'] = self.request.GET.get('status', '')
        context['list_fields'] = [
            ('id', _('ID')),
            ('user_display_admin', _('Користувач')),
            ('created_at_formatted_admin', _('Дата')),
            ('total_price_display_admin', _('Сума')),
            ('status_display_admin', _('Статус')),
            ('payment_method_display_admin', _('Оплата'))
        ]
        context['model_name_plural'] = _("Замовлення")
        context['model_name_singular'] = _("Замовлення")
        context['detail_url_name'] = 'administration:order_detail_admin'
        context['update_url_name'] = 'administration:order_update'

        if hasattr(Order, 'status') and hasattr(Order._meta.get_field('status'), 'choices'):
            context['order_statuses_for_filter'] = Order._meta.get_field('status').choices
        else:
            context['order_statuses_for_filter'] = []


        status_color_map_list = {
            'pending': "yellow",
            'processing': "indigo",
            'paid': "blue",
            'shipped': "purple",
            'completed': "green",
            'cancelled': "red",
            'payment_failed': "red",

        }

        for obj in context['objects']:
            user_display = _("Гість")
            if obj.user:
                user_display = obj.user.username if hasattr(obj.user, 'username') else obj.user.get_full_name()
            elif obj.first_name and obj.last_name:
                user_display = f"{obj.first_name} {obj.last_name}"

            setattr(obj, 'user_display_admin', user_display)
            setattr(obj, 'created_at_formatted_admin', obj.created_at.strftime("%d.%m.%Y %H:%M") if obj.created_at else "-")
            


            setattr(obj, 'total_price_display_admin', f"{obj.total_price:.2f} грн" if obj.total_price is not None else "-")

            
            setattr(obj, 'payment_method_display_admin', obj.get_payment_method_display())

            status_val = obj.status
            status_text = obj.get_status_display()
            color = status_color_map_list.get(status_val, "gray")
            setattr(obj, 'status_display_admin', format_html(f'<span class="px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-{color}-100 text-{color}-800 dark:bg-{color}-700/30 dark:text-{color}-300">{status_text}</span>'))
        return context


class OrderDetailView(SuperUserRequiredMixin, DetailView):
    model = Order
    template_name = 'administration/order_detail_admin.html'
    context_object_name = 'order_instance'

    def get_queryset(self):
        return super().get_queryset().select_related('user').prefetch_related('items__product')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order_status_choices_for_select = []
        if hasattr(Order, 'status') and hasattr(Order._meta.get_field('status'), 'choices'):
            order_status_choices_for_select = Order._meta.get_field('status').choices


        status_color_map_detail = {
            'pending': "yellow",
            'processing': "indigo",
            'paid': "blue",
            'shipped': "purple",
            'completed': "green",
            'cancelled': "red",
            'payment_failed': "red",
        }

        ctx.update({
            'page_title': _('Деталі Замовлення #{}').format(self.object.id),
            'OrderStatusEnum_choices': order_status_choices_for_select,
            'order_status_color_map': status_color_map_detail
        })
        return ctx


class OrderUpdateView(SuperUserRequiredMixin, UpdateView):
    model = Order
    form_class = OrderAdminForm
    template_name = 'administration/generic_form.html'

    def get_success_url(self):
        return reverse_lazy('administration:order_detail_admin', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'page_title': _('Редагувати Замовлення #{}').format(self.object.id),
            'form_title': _('Редагування замовлення #{}').format(self.object.pk),
            'button_text': _('Зберегти зміни'),
            'back_url': self.get_success_url()
        })
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        post_data_keys = set(request.POST.keys())
        is_quick_status_update = 'status' in post_data_keys and \
                                 len(post_data_keys.difference({'csrfmiddlewaretoken', 'status'})) == 0

        if is_quick_status_update:
            new_status_value = request.POST.get('status')
            old_status_value = self.object.status
            
            valid_statuses = [choice[0] for choice in Order._meta.get_field('status').choices]
            if new_status_value not in valid_statuses:
                messages.error(request, _("Неприпустиме значення статусу."))
                return HttpResponseRedirect(self.get_success_url())

            if old_status_value != new_status_value:
                self.object.status = new_status_value
                self.object.save(update_fields=['status'])
                new_status_display = self.object.get_status_display()
                logger.info(
                    f"Статус замовлення #{self.object.id} змінено з '{old_status_value}' на '{new_status_value}' "
                    f"адміном {request.user.username} (швидке оновлення)."
                )
                messages.success(
                    request,
                    _("Статус замовлення #{} успішно оновлено на «{}».").format(
                        self.object.id, new_status_display
                    )
                )
            else:
                messages.info(request, _("Статус замовлення не змінено (залишився тим самим)."))
            
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        original_order = None
        try:
            original_order = Order.objects.get(pk=self.object.pk)
            old_status = original_order.status
        except Order.DoesNotExist:
            old_status = None

        new_status = form.cleaned_data.get('status')
        response = super().form_valid(form)
        
        if original_order and old_status is not None and old_status != new_status:
            logger.info(
                f"Статус замовлення #{self.object.id} змінено з '{old_status}' на '{new_status}' "
                f"адміном {self.request.user.username} (повне редагування)."
            )
        
        messages.success(self.request, _("Замовлення #{} успішно оновлено.").format(self.object.id))
        return response




ListingImageFormSet = inlineformset_factory(
    Listing, 
    ListingImage, 
    form=ModelForm, 
    fields=('image', 'alt_text', 'order'), 
    extra=1, 
    can_delete=True, 
    min_num=0, 
    validate_min=False
)
ListingFeatureFormSet = inlineformset_factory(
    Listing, 
    ListingFeature, 
    form=ModelForm, 
    fields=('name', 'value', 'icon_svg'), 
    extra=1, 
    can_delete=True, 
    min_num=0, 
    validate_min=False
)


class ListingListView(SuperUserRequiredMixin, ListView):
    model = Listing
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 15
    
    def get_queryset(self): qs = super().get_queryset().select_related('user', 'category').order_by('-updated_at'); q = self.request.GET.get('q'); cat_f = self.request.GET.get('cat_marketplace'); status_f = self.request.GET.get('status_listing'); conditions = [(q, Q(
    title__icontains=q) | Q(description__icontains=q) | Q(user__username__icontains=q)if q else None), (cat_f, Q(category_id=cat_f)if cat_f and cat_f.isdigit()else None), (status_f, Q(status=status_f)if status_f else None)]; qs = qs.filter(*[c for v, c in conditions if c]); return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'page_title': _('Управління Оголошеннями'), 'search_query': self.request.GET.get('q', ''), 'list_fields': ['id', 'main_image_thumbnail_admin', 'title_link_admin', 'user', 'category', 'price_display_admin', 'status_display_admin', 'is_active_display_admin', 'updated_at|date:"d.m.Y"'], 'model_name_plural': _("Оголошення"), 'model_name_singular': _(
            "Оголошення"), 'create_url_name': 'administration:listing_create', 'update_url_name': 'administration:listing_update', 'delete_url_name': 'administration:listing_delete', 'marketplace_categories_for_filter': MarketplaceCategory.objects.all(), 'listing_statuses_for_filter': Listing.STATUS_CHOICES, 'current_cat_marketplace_filter': self.request.GET.get('cat_marketplace', ''), 'current_status_listing_filter': self.request.GET.get('status_listing', '')})
        for obj in ctx['objects']:
            setattr(obj, 'main_image_thumbnail_admin', lambda o=obj: format_html(
                '<img src="{}" style="width:50px; height:40px; object-fit:cover; border-radius:3px;" />', o.main_image.url)if o.main_image else "-")
            setattr(obj, 'title_link_admin', lambda o=obj: format_html(
                '<a href="{}" class="hover:text-yellow-600 font-medium">{}</a>', reverse('administration:listing_update', args=[o.pk]), o.title))
            setattr(obj, 'price_display_admin',
                    f"{obj.price} {obj.currency_symbol}")
            setattr(obj, 'status_display_admin', obj.get_status_display())
            setattr(obj, 'is_active_display_admin', _("Так")
                    if obj.is_active_display else _("Ні"))
            return ctx


class ListingCreateView(SuperUserRequiredMixin, CreateView):
    model = Listing
    form_class = ListingAdminForm
    template_name = 'administration/listing_form_admin.html'
    success_url = reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx.update({'image_formset': ListingImageFormSet(self.request.POST, self.request.FILES, prefix='images', instance=self.object if self.object else None),
                       'feature_formset': ListingFeatureFormSet(self.request.POST, prefix='features', instance=self.object if self.object else None)})
        else:
            ctx.update({'image_formset': ListingImageFormSet(prefix='images', instance=self.object if self.object else None),
                       'feature_formset': ListingFeatureFormSet(prefix='features', instance=self.object if self.object else None)})
        ctx.update({'page_title': _('Створити Оголошення'), 'form_title': _(
            'Нове оголошення'), 'button_text': _('Створити'), 'back_url': self.success_url})
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        feature_formset = context['feature_formset']
        

        if not form.is_valid():
            return self.form_invalid(form)

        if image_formset.is_valid() and feature_formset.is_valid():
            listing = form.save(commit=False)
            listing.user = self.request.user 
            listing.save() 
            form.save_m2m() 
            
            image_formset.instance = listing 
            image_formset.save()
            
            feature_formset.instance = listing 
            feature_formset.save()
            
            messages.success(self.request,_("Оголошення «{}» створено.").format(listing.title))
            return HttpResponseRedirect(self.get_success_url()) 
        else:

            if not image_formset.is_valid():
                form.add_error(None, _("Помилки у додаткових зображеннях. Перевірте, чи завантажено файли та чи заповнено обов'язкові поля, якщо є."))

                logger.warning(f"Listing image_formset errors: {image_formset.errors} {image_formset.non_form_errors()}")
            if not feature_formset.is_valid():
                form.add_error(None, _("Помилки у характеристиках."))
                logger.warning(f"Listing feature_formset errors: {feature_formset.errors} {feature_formset.non_form_errors()}")
            return self.form_invalid(form)



class ListingUpdateView(SuperUserRequiredMixin, UpdateView):
    model = Listing
    form_class = ListingAdminForm
    template_name = 'administration/listing_form_admin.html'
    success_url = reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx.update({'image_formset': ListingImageFormSet(self.request.POST, self.request.FILES, instance=self.object,
                       prefix='images'), 'feature_formset': ListingFeatureFormSet(self.request.POST, instance=self.object, prefix='features')})
        else:
            ctx.update({'image_formset': ListingImageFormSet(instance=self.object, prefix='images'),
                       'feature_formset': ListingFeatureFormSet(instance=self.object, prefix='features')})
        ctx.update({'page_title': _('Редагувати: {}').format(self.object.title), 'form_title': _(
            'Редагування оголошення #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': self.success_url})
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        feature_formset = context['feature_formset']

        if not form.is_valid():
            return self.form_invalid(form)

        if image_formset.is_valid() and feature_formset.is_valid():
            listing = form.save() 

            
            image_formset.instance = listing 
            image_formset.save()
            
            feature_formset.instance = listing
            feature_formset.save()
            
            messages.success(self.request,_("Оголошення «{}» оновлено.").format(listing.title))
            return HttpResponseRedirect(self.get_success_url())
        else:
            if not image_formset.is_valid():
                form.add_error(None, _("Помилки у додаткових зображеннях."))
                logger.warning(f"Listing update image_formset errors: {image_formset.errors} {image_formset.non_form_errors()}")
            if not feature_formset.is_valid():
                form.add_error(None, _("Помилки у характеристиках."))
                logger.warning(f"Listing update feature_formset errors: {feature_formset.errors} {feature_formset.non_form_errors()}")
            return self.form_invalid(form)



class ListingDeleteView(SuperUserRequiredMixin, DeleteView):
    model = Listing
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:listing_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити: {}').format(self.object.title), 'object_type_display': Listing._meta.verbose_name.capitalize(), 'object_name': self.object.title, 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): name = self.get_object().title; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("{} «{}» видалено.").format(Listing._meta.verbose_name.capitalize(), name)); return resp




class ForumUserPostListView(SuperUserRequiredMixin, ListView):
    model = ForumUserPost
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('author__user', 'category').order_by('-last_activity')
        search_query = self.request.GET.get('q')
        category_filter = self.request.GET.get('category')
        author_user_filter = self.request.GET.get('author_user') 

        conditions = []
        if search_query:
            conditions.append(Q(title__icontains=search_query) | Q(description__icontains=search_query))
        if category_filter and category_filter.isdigit():
            conditions.append(Q(category_id=category_filter))
        if author_user_filter and author_user_filter.isdigit():

            conditions.append(Q(author__user_id=author_user_filter)) 
        
        if conditions:
            final_q_object = Q()
            for cond in conditions:
                if cond: final_q_object &= cond
            if final_q_object: queryset = queryset.filter(final_q_object)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        



        authors_with_posts_user_ids = ForumUserPost.objects.filter(author__isnull=False, author__user__isnull=False)\
                                                    .values_list('author__user_id', flat=True).distinct()
        users_who_are_authors = User.objects.filter(is_active=True, pk__in=authors_with_posts_user_ids).order_by('username')


        context.update({
            'page_title': _('Теми Форуму (Модерація)'),
            'list_fields': [
                ('id', _('ID')), 
                ('title_link_admin', _('Назва')), 
                ('author_display_admin', _('Автор')), 
                ('category', _('Категорія')), 
                ('answer_count_display', _('Відповідей')), 
                ('topic_view_count', _('Переглядів')), 
                ('last_activity|date:"d.m.Y H:i"', _('Остання активність'))
            ],
            'model_name_plural': _("Теми форуму"), 
            'model_name_singular': _("Тему форуму"),
            'update_url_name': 'administration:forumuserpost_update',
            'delete_url_name': 'administration:forumuserpost_delete',
            'list_url_name': 'administration:forumuserpost_list',

            'search_query': self.request.GET.get('q', ''),
            'forum_categories_for_filter': ForumCategory.objects.annotate(num_posts_ann=Count('posts')).filter(num_posts_ann__gt=0).order_by('name'),
            'users_for_filter': users_who_are_authors, 
            'current_category_filter': self.request.GET.get('category', ''),
            'current_author_user_filter': self.request.GET.get('author_user', '') 
        })
        
        for obj in context['objects']:
            setattr(obj, 'title_link_admin', lambda o=obj: format_html('<a href="{}" class="hover:text-yellow-600 font-medium dark:hover:text-yellow-400">{}</a>', reverse('administration:forumuserpost_update', args=[o.pk]), o.title or _("(без назви)")))
            setattr(obj, 'author_display_admin', obj.author.user.username if obj.author and obj.author.user else _("N/A"))
            setattr(obj, 'answer_count_display', obj.answer_count) 
        return context



class ForumUserPostUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ForumUserPost
    form_class = ForumUserPostAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:forumuserpost_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Редагувати Тему: {}').format(self.object.title), 'form_title': _('Редагування теми #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return ctx; 
    def form_valid(self, form): messages.success(self.request, _("Тему «{}» оновлено.").format(form.instance.title)); return super().form_valid(form)


class ForumUserPostDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ForumUserPost
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:forumuserpost_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити: {}').format(self.object.title), 'object_type_display': _('Тему форуму'), 'object_name': self.object.title, 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): name = self.get_object().title; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("Тему «{}» видалено.").format(name)); return resp




class StationBookingListView(SuperUserRequiredMixin, ListView):
    model = StationBooking
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('station', 'user')
            .order_by('-start_time')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        objects = context['objects']

        context.update({
            'page_title': _('Бронювання Зарядних Станцій'),
            'list_fields': [
                'id',
                'station',
                'user_display_admin',
                'connector_id_display',
                'start_time|date:"d.m H:i"',
                'end_time|date:"d.m H:i"',
                'status_display_admin',
                'total_amount_display',
            ],
            'model_name_plural': _("Бронювання станцій"),
            'model_name_singular': _("Бронювання станції"),
            'update_url_name': 'administration:stationbooking_update',
            'delete_url_name': 'administration:stationbooking_delete',
        })

        status_color_map = {
            'CONFIRMED': 'green',
            'PENDING_PAYMENT': 'yellow',
            'CANCELLED_SYSTEM': 'red',
            'COMPLETED': 'blue',
        }

        for obj in objects:
            obj.user_display_admin = obj.user.username if obj.user else "N/A"
            obj.connector_id_display = obj.connector_id or "N/A"
            obj.total_amount_display = f"{obj.total_amount} {obj.currency}" if obj.total_amount else "N/A"

            status = str(obj.status).upper()
            color = status_color_map.get(status, 'gray')
            label = obj.get_status_display() if hasattr(obj, 'get_status_display') else str(obj.status)

            obj.status_display_admin = format_html(
                f'<span class="px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full '
                f'bg-{color}-100 text-{color}-800">{label}</span>'
            )

        return context


class StationBookingUpdateView(SuperUserRequiredMixin, UpdateView):
    model = StationBooking
    form_class = StationBookingAdminForm
    template_name = 'administration/generic_form.html' 
    success_url = reverse_lazy('administration:stationbooking_list') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Редагувати Бронювання Станції #{}').format(self.object.pk),
            'form_title': _('Редагування бронювання #{}').format(self.object.pk),
            'button_text': _('Зберегти зміни'),
            'back_url': self.get_success_url() 
        })
        return context

    def form_valid(self, form):

        logger.info(f"StationBookingUpdateView: Оновлення бронювання ID {self.object.pk}")
        logger.info(f"Дані з форми (cleaned_data): {form.cleaned_data}")
        logger.info(f"Об'єкт до збереження (form.instance): start_time={form.instance.start_time}, end_time={form.instance.end_time}")
        

        response = super().form_valid(form) 


        self.object.refresh_from_db() 
        logger.info(f"Об'єкт після збереження: start_time={self.object.start_time}, end_time={self.object.end_time}")
        
        messages.success(self.request, _("Бронювання станції #{} успішно оновлено.").format(form.instance.pk))
        return response

    def get_success_url(self):


        return reverse_lazy('administration:stationbooking_list')



class StationBookingDeleteView(SuperUserRequiredMixin, DeleteView):
    model = StationBooking
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:stationbooking_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити Бронювання Станції #{}').format(self.object.pk), 'object_type_display': _('Бронювання станції'), 'object_name': f"Бронювання #{self.object.pk}", 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): pk = self.get_object().pk; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("Бронювання станції #{} видалено.").format(pk)); return resp




class ElectricVehicleListView(SuperUserRequiredMixin, ListView):
    model = ElectricVehicle
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20
    def get_queryset(self): return super().get_queryset().select_related('user').order_by('-last_updated'); 
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Електротранспорт Користувачів'), 'list_fields': ['id', 'name', 'model', 'user', 'battery_percentage_display', 'is_connected', 'is_locked', 'last_updated|date:"d.m.Y H:i"'], 'model_name_plural': _("Транспортні засоби"), 'model_name_singular': _("Транспортний засіб"), 'create_url_name': 'administration:electricvehicle_create', 'update_url_name': 'administration:electricvehicle_update', 'delete_url_name': 'administration:electricvehicle_delete'}); [setattr(o, 'battery_percentage_display', f"{o.battery_percentage()}%")for o in ctx['objects']]; return ctx


class ElectricVehicleCreateView(SuperUserRequiredMixin, CreateView):
    model = ElectricVehicle
    form_class = ElectricVehicleAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:electricvehicle_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Додати Транспорт'), 'form_title': _('Новий транспортний засіб'), 'button_text': _('Додати'), 'back_url': self.success_url}); return ctx; 
    def form_valid(self, form): messages.success(self.request, _("Транспорт «{}» додано.").format(form.instance.name)); return super().form_valid(form)


class ElectricVehicleUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ElectricVehicle
    form_class = ElectricVehicleAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:electricvehicle_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Редагувати: {}').format(self.object.name), 'form_title': _('Редагування ТЗ #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return ctx; 
    def form_valid(self, form): messages.success(self.request, _("Транспорт «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)


class ElectricVehicleDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ElectricVehicle
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:electricvehicle_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити: {}').format(self.object.name), 'object_type_display': _('Транспортний засіб'), 'object_name': self.object.name, 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): name = self.get_object().name; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("Транспорт «{}» видалено.").format(name)); return resp




class NewsletterSubscriberListView(SuperUserRequiredMixin, ListView):
    model = NewsletterSubscriber
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 50
    def get_queryset(self): return super().get_queryset().order_by('-subscribed_at'); 
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Підписники на Новини'), 'list_fields': ['id', 'email', 'subscribed_at|date:"d.m.Y H:i"'], 'model_name_plural': _("Підписники"), 'model_name_singular': _("Підписника"), 'delete_url_name': 'administration:newslettersubscriber_delete'}); return ctx


class NewsletterSubscriberDeleteView(SuperUserRequiredMixin, DeleteView):
    model = NewsletterSubscriber
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:newslettersubscriber_list')
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити Підписника: {}').format(self.object.email), 'object_type_display': _('Підписку'), 'object_name': self.object.email, 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): email = self.get_object().email; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("Підписку для «{}» видалено.").format(email)); return resp


class MarketplaceCategoryListView(SuperUserRequiredMixin, ListView):
    model = MarketplaceCategory
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 30
    def get_queryset(self):
        return super().get_queryset().annotate(listing_count_ann=Count('listing')).order_by('name')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Категорії продажів'),
            'list_fields': [('name', _('Назва')), ('slug', _('Посилання')), ('listing_count_ann', _('Оголошень'))],
            'model_name_plural': _("Категорії продажів"),
            'model_name_singular': _("Категорію продажу"),
            'create_url_name': 'administration:marketplacecategory_create',
            'update_url_name': 'administration:marketplacecategory_update',
            'delete_url_name': 'administration:marketplacecategory_delete',
            'list_url_name': 'administration:marketplacecategory_list',
        })
        return context

class MarketplaceCategoryCreateView(SuperUserRequiredMixin, CreateView):
    model = MarketplaceCategory; form_class = MarketplaceCategoryAdminForm
    template_name = 'administration/generic_form.html'; success_url = reverse_lazy('administration:marketplacecategory_list')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Створити Категорію Приватного продажу'), 'form_title': _('Нова категорія приватного продажу'), 'button_text': _('Створити'), 'back_url': str(self.success_url)}); return context
    def form_valid(self, form): messages.success(self.request, _("Категорію «{}» створено.").format(form.instance.name)); return super().form_valid(form)

class MarketplaceCategoryUpdateView(SuperUserRequiredMixin, UpdateView):
    model = MarketplaceCategory; form_class = MarketplaceCategoryAdminForm
    template_name = 'administration/generic_form.html'; success_url = reverse_lazy('administration:marketplacecategory_list')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Редагувати Категорію: {}').format(self.object.name), 'form_title': _('Редагування категорії приватного продажу #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': str(self.success_url)}); return context
    def form_valid(self, form): messages.success(self.request, _("Категорію «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)

class MarketplaceCategoryDeleteView(SuperUserRequiredMixin, DeleteView):
    model = MarketplaceCategory; template_name = 'administration/confirm_delete.html'; success_url = reverse_lazy('administration:marketplacecategory_list')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Видалити: {}').format(self.object.name), 'object_type_display': _('Категорію приватного продажу'), 'object_name': self.object.name, 'cancel_url': str(self.success_url)}); return context
    def post(self, request, *args, **kwargs): object_name = self.get_object().name; response = super().delete(request, *args, **kwargs); messages.success(self.request, _("Категорію «{}» видалено.").format(object_name)); return response


class ListingListView(SuperUserRequiredMixin, ListView):
    model = Listing
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'category').order_by('-updated_at')
        search_query = self.request.GET.get('q')
        category_filter = self.request.GET.get('category')
        status_filter = self.request.GET.get('status')
        user_filter = self.request.GET.get('user')
        conditions = []
        if search_query:
            conditions.append(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(city__icontains=search_query)
            )
        if category_filter and category_filter.isdigit():
            conditions.append(Q(category_id=category_filter))
        if status_filter:
            conditions.append(Q(status=status_filter))
        if user_filter and user_filter.isdigit():
            conditions.append(Q(user_id=user_filter))
        if conditions:
            final_q_object = Q()
            for cond in conditions:
                final_q_object &= cond
            queryset = queryset.filter(final_q_object)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Управління Оголошеннями Приватного Продажу'),
            'search_query': self.request.GET.get('q', ''),
            'list_fields': [
                ('id', _('ID')),
                ('main_image_thumbnail_admin', _('Фото')),
                ('title_link_admin', _('Заголовок')),
                ('user', _('Автор')),
                ('category', _('Категорія МП')),
                ('price_display_admin', _('Ціна')),
                ('get_status_display', _('Статус')), 
                ('is_active_display_admin', _('Активне')),
                ('updated_at|date:"d.m.Y"', _('Оновлено'))
            ],
            'model_name_plural': _("Оголошення"),
            'model_name_singular': _("Оголошення"),
            'create_url_name': 'administration:listing_create',
            'update_url_name': 'administration:listing_update',
            'delete_url_name': 'administration:listing_delete',
            'list_url_name': 'administration:listing_list',
            'marketplace_categories_for_filter': MarketplaceCategory.objects.all().order_by('name'),
            'listing_statuses_for_filter': Listing.STATUS_CHOICES,
            'users_for_listing_filter': User.objects.filter(listings__isnull=False).distinct().order_by('username'),
            'current_category_filter': self.request.GET.get('category', ''),
            'current_status_filter': self.request.GET.get('status', ''),
            'current_user_filter': self.request.GET.get('user', ''),
        })
        for obj in context['objects']:
            setattr(obj, 'main_image_thumbnail_admin', lambda o=obj: format_html('<img src="{}" style="width:50px; height:40px; object-fit:cover; border-radius:3px;" />', o.main_image.url) if o.main_image and hasattr(o.main_image, 'url') else "-")
            setattr(obj, 'title_link_admin', lambda o=obj: format_html('<a href="{}" class="hover:text-yellow-600 font-medium dark:hover:text-yellow-400">{}</a>', reverse('administration:listing_update', args=[o.pk]), o.title))
            setattr(obj, 'price_display_admin', f"{obj.price} {obj.currency_symbol}")
            setattr(obj, 'is_active_display_admin', _("Так") if obj.is_active_display else _("Ні"))
        return context


class ListingCreateView(SuperUserRequiredMixin, CreateView):
    model = Listing
    form_class = ListingAdminForm
    template_name = 'administration/listing_form_admin.html'
    success_url = reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ListingImageFormSet(self.request.POST, self.request.FILES, prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(self.request.POST, prefix='features')
        else:
            context['image_formset'] = ListingImageFormSet(prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(prefix='features')
        context.update({
            'page_title': _('Створити Оголошення'),
            'form_title': _('Нове оголошення'),
            'button_text': _('Створити'),
            'back_url': str(self.success_url)
        })
        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        feature_formset = context['feature_formset']

        if image_formset.is_valid() and feature_formset.is_valid():
            self.object = form.save(commit=False)
            if not self.object.user_id:
                self.object.user = self.request.user
            self.object.save()
            form.save_m2m()

            image_formset.instance = self.object
            image_formset.save()

            feature_formset.instance = self.object
            feature_formset.save()

            messages.success(self.request, _("Оголошення «{}» успішно створено.").format(self.object.title))
            return HttpResponseRedirect(self.get_success_url())
        else:
            if not image_formset.is_valid():
                logger.warning(f"Listing create image_formset errors: {image_formset.errors} {image_formset.non_form_errors()}")
                form.add_error(None, _("Будь ласка, виправте помилки у формі зображень."))

            if not feature_formset.is_valid():
                logger.warning(f"Listing create feature_formset errors: {feature_formset.errors} {feature_formset.non_form_errors()}")
                form.add_error(None, _("Будь ласка, виправте помилки у формі характеристик."))

            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(f"ListingCreateView: form_invalid called. Errors: {form.errors}, Non-field errors: {form.non_field_errors()}")
        context = self.get_context_data()
        if self.request.POST:
            context['image_formset'] = ListingImageFormSet(self.request.POST, self.request.FILES, prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(self.request.POST, prefix='features')
        else:
            context['image_formset'] = ListingImageFormSet(prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(prefix='features')
        context['form'] = form
        return self.render_to_response(context)


class ListingUpdateView(SuperUserRequiredMixin, UpdateView):
    model = Listing
    form_class = ListingAdminForm
    template_name = 'administration/listing_form_admin.html'

    def get_success_url(self):
         return reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ListingImageFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(self.request.POST, instance=self.object, prefix='features')
        else:
            context['image_formset'] = ListingImageFormSet(instance=self.object, prefix='images')
            context['feature_formset'] = ListingFeatureFormSet(instance=self.object, prefix='features')
        context.update({
            'page_title': _('Редагувати: {}').format(self.object.title),
            'form_title': _('Редагування оголошення #{}').format(self.object.pk),
            'button_text': _('Зберегти зміни'),
            'back_url': str(self.get_success_url())
        })
        return context

    @transaction.atomic
    def form_valid(self, form):
        logger.info(f"ListingUpdateView: form_valid called for listing {self.object.pk}")
        context = self.get_context_data()
        image_formset = context['image_formset']
        feature_formset = context['feature_formset']

        are_formsets_valid = True
        if not image_formset.is_valid():
            are_formsets_valid = False
            logger.warning(f"ListingUpdateView: image_formset НЕ валідний: {image_formset.errors} {image_formset.non_form_errors()}")
            form.add_error(None, _("Помилки у додаткових зображеннях."))

        if not feature_formset.is_valid():
            are_formsets_valid = False
            logger.warning(f"ListingUpdateView: feature_formset НЕ валідний: {feature_formset.errors} {feature_formset.non_form_errors()}")
            form.add_error(None, _("Помилки у характеристиках."))

        if are_formsets_valid and form.is_valid(): 
            logger.info(f"ListingUpdateView: Всі форми та формсети валідні для лістингу {self.object.pk}.")
            self.object = form.save()

            image_formset.save()
            feature_formset.save()

            messages.success(self.request, _("Оголошення «{}» успішно оновлено.").format(self.object.title))
            return HttpResponseRedirect(self.get_success_url())
        else:
            logger.warning(f"ListingUpdateView: Повернення форми через невалідні формсети або основну форму для лістингу {self.object.pk}.")
            if not form.is_valid(): 
                 logger.warning(f"ListingUpdateView: Основна форма НЕ валідна: {form.errors}")
            return self.form_invalid(form)


    def form_invalid(self, form):
        logger.warning(f"ListingUpdateView: form_invalid called for listing {self.object.pk if hasattr(self, 'object') and self.object else 'N/A'}. Errors: {form.errors}, Non-field errors: {form.non_field_errors()}")
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class ListingDeleteView(SuperUserRequiredMixin, DeleteView):
    model = Listing
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Видалити Оголошення: {}').format(self.object.title),
            'object_type_display': Listing._meta.verbose_name.capitalize(),
            'object_name': self.object.title,
            'cancel_url': str(self.success_url)
        })
        return context

    def post(self, request, *args, **kwargs):
        obj_to_delete = self.get_object()
        object_name = obj_to_delete.title
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, _("{} «{}» успішно видалено.").format(Listing._meta.verbose_name.capitalize(), object_name))
        return response



class ListingDeleteView(SuperUserRequiredMixin, DeleteView):
    model = Listing
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:listing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Видалити Оголошення: {}').format(self.object.title),
            'object_type_display': Listing._meta.verbose_name.capitalize(),
            'object_name': self.object.title,
            'cancel_url': str(self.success_url)
        })
        return context

    def post(self, request, *args, **kwargs):
        obj_to_delete = self.get_object()
        object_name = obj_to_delete.title
        
        response = super().delete(request, *args, **kwargs)
        
        messages.success(self.request, _("{} «{}» успішно видалено.").format(Listing._meta.verbose_name.capitalize(), object_name))
        return response






class ForumCategoryListView(SuperUserRequiredMixin, ListView):
    model = ForumCategory
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 30

    def get_queryset(self): return super().get_queryset().annotate(
        post_count_ann=Count('posts')).order_by('name')  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Категорії Форуму'),
            'list_fields': ['name', 'description_short', 'post_count_ann', 'created_at|date:"d.m.Y"'],
            'model_name_plural': _("Категорії форуму"),
            'model_name_singular': _("Категорію форуму"),
            'create_url_name': 'administration:forumcategory_create',
            'update_url_name': 'administration:forumcategory_update',
            'delete_url_name': 'administration:forumcategory_delete',
        })
        for obj in context['objects']:
            setattr(obj, 'description_short', (obj.description[:70] + '...') if obj.description and len(
                obj.description) > 70 else obj.description)
        return context


class ForumCategoryCreateView(SuperUserRequiredMixin, CreateView):
    model = ForumCategory
    form_class = ForumCategoryAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:forumcategory_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _(
        'Створити Категорію Форуму'), 'form_title': _('Нова категорія форуму'), 'button_text': _('Створити'), 'back_url': self.success_url}); return context
    def form_valid(self, form): messages.success(self.request, _(
        "Категорію форуму «{}» створено.").format(form.instance.name)); return super().form_valid(form)


class ForumCategoryUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ForumCategory
    form_class = ForumCategoryAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:forumcategory_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Редагувати Категорію Форуму: {}').format(self.object.name),
            'form_title': _('Редагування категорії форуму #{}').format(self.object.pk),
            'button_text': _('Зберегти'),
            'back_url': self.success_url,
            'read_only_fields_data': [ 
                (_('Дата створення'), self.object.created_at.strftime("%d.%m.%Y %H:%M") if self.object.created_at else "-"),
            ]
        })
        return context
    def form_valid(self, form): messages.success(self.request, _(
        "Категорію форуму «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)


class ForumCategoryDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ForumCategory
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:forumcategory_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Видалити: {}').format(
        self.object.name), 'object_type_display': _('Категорію форуму'), 'object_name': self.object.name, 'cancel_url': self.success_url}); return context
    def post(self, request, *args, **kwargs): object_name = self.get_object().name; response = super().delete(request, *args,
                                                                                                              **kwargs); messages.success(self.request, _("Категорію форуму «{}» видалено.").format(object_name)); return response



class ForumAnswerListView(SuperUserRequiredMixin, ListView):
    model = ForumAnswer
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self): return super().get_queryset().select_related(
        'user_post', 'user', 'parent').order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Відповіді на Форумі (Модерація)'),
            'list_fields': ['id', 'content_short', 'user_display', 'user_post_title', 'parent_id_display', 'date_created|date:"d.m.Y H:i"', 'upvotes_count', 'downvotes_count'],
            'model_name_plural': _("Відповіді"),
            'model_name_singular': _("Відповідь"),
            'update_url_name': 'administration:forumanswer_update',
            'delete_url_name': 'administration:forumanswer_delete',
        })
        for obj in context['objects']:
            setattr(obj, 'content_short',
                    (obj.content[:70] + '...') if len(obj.content) > 70 else obj.content)
            setattr(obj, 'user_display',
                    obj.user.username if obj.user else "N/A")
            setattr(obj, 'user_post_title',
                    obj.user_post.title if obj.user_post else "N/A")
            setattr(obj, 'parent_id_display',
                    obj.parent.id if obj.parent else "-")
        return context


class ForumAnswerUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ForumAnswer
    form_class = ForumAnswerAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:forumanswer_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Редагувати Відповідь #{}').format(self.object.pk), 'form_title': _(
        'Редагування відповіді на пост "{}"').format(self.object.user_post.title if self.object.user_post else ""), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return context
    def form_valid(self, form): messages.success(self.request, _(
        "Відповідь #{} оновлено.").format(form.instance.pk)); return super().form_valid(form)


class ForumAnswerDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ForumAnswer
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:forumanswer_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Видалити Відповідь #{}').format(
        self.object.pk), 'object_type_display': _('Відповідь'), 'object_name': f"Відповідь ID {self.object.pk}", 'cancel_url': self.success_url}); return context
    def post(self, request, *args, **kwargs): pk = self.get_object().pk; response = super().delete(request,
                                                                                                   *args, **kwargs); messages.success(self.request, _("Відповідь #{} видалено.").format(pk)); return response



class ProductReviewListView(SuperUserRequiredMixin, ListView):
    model = ProductReview
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self): return super().get_queryset().select_related(
        'product', 'user').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Відгуки на Товари (Модерація)'),
            'list_fields': ['id', 'product_link_admin', 'user_display', 'rating_stars', 'text_short', 'is_approved_display', 'created_at|date:"d.m.Y"'],
            'model_name_plural': _("Відгуки"),
            'model_name_singular': _("Відгук"),
            'update_url_name': 'administration:productreview_update',
            'delete_url_name': 'administration:productreview_delete',
        })
        for obj in context['objects']:
            setattr(obj, 'product_link_admin', lambda o=obj: format_html('<a href="{}" class="hover:text-yellow-600">{}</a>',
                    reverse('administration:product_update', args=[o.product.pk]), o.product.name) if o.product else "N/A")
            setattr(obj, 'user_display',
                    obj.user.username if obj.user else "N/A")
            setattr(obj, 'rating_stars', "★" * obj.rating + "☆" *
                    (5 - obj.rating) if obj.rating else "N/A")
            setattr(obj, 'text_short',
                    (obj.text[:70] + '...') if len(obj.text) > 70 else obj.text)
            setattr(obj, 'is_approved_display', format_html('<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {}">{}</span>',
                    "bg-green-100 text-green-800" if obj.is_approved else "bg-yellow-100 text-yellow-800", _("Так") if obj.is_approved else _("На розгляді")))
        return context



class ProductReviewUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ProductReview
    form_class = ProductReviewAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:productreview_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Редагувати Відгук #{}').format(self.object.pk), 'form_title': _(
        'Редагування відгуку на {}').format(self.object.product.name if self.object.product else ""), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return context
    def form_valid(self, form): messages.success(self.request, _(
        "Відгук #{} оновлено.").format(form.instance.pk)); return super().form_valid(form)


class ProductReviewDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ProductReview
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:productreview_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Видалити Відгук #{}').format(
        self.object.pk), 'object_type_display': _('Відгук'), 'object_name': f"Відгук ID {self.object.pk}", 'cancel_url': self.success_url}); return context
    def post(self, request, *args, **kwargs): pk = self.get_object().pk; response = super().delete(request,
                                                                                                   *args, **kwargs); messages.success(self.request, _("Відгук #{} видалено.").format(pk)); return response



class VehicleReportListView(SuperUserRequiredMixin, ListView):
    model = VehicleReport
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 20

    def get_queryset(self): return super().get_queryset().select_related(
        'vehicle__user', 'vehicle').order_by('-generated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Звіти по Транспорту'),
            'list_fields': ['id', 'vehicle_display', 'user_display', 'generated_at|date:"d.m.Y H:i"', 'charge_at_report_display', 'location_at_report_short'],
            'model_name_plural': _("Звіти"),
            'model_name_singular': _("Звіт"),
            'detail_url_name': 'administration:vehiclereport_detail',  
            'delete_url_name': 'administration:vehiclereport_delete',
        })
        for obj in context['objects']:
            setattr(obj, 'vehicle_display',
                    f"{obj.vehicle.name} ({obj.vehicle.model})" if obj.vehicle else "N/A")
            setattr(obj, 'user_display',
                    obj.vehicle.user.username if obj.vehicle and obj.vehicle.user else "N/A")
            setattr(obj, 'charge_at_report_display',
                    f"{obj.charge_at_report}%" if obj.charge_at_report is not None else "N/A")
            setattr(obj, 'location_at_report_short', (obj.location_at_report[:30] + '...') if obj.location_at_report and len(
                obj.location_at_report) > 30 else obj.location_at_report)
        return context


class VehicleReportDetailView(SuperUserRequiredMixin, DetailView):
    model = VehicleReport
    template_name = 'administration/vehiclereport_detail_admin.html'
    context_object_name = 'report'  

    def get_queryset(self): return super().get_queryset(
    ).select_related('vehicle__user', 'vehicle')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update(
        {'page_title': _('Деталі Звіту #{}').format(self.object.pk)}); return context


class VehicleReportDeleteView(SuperUserRequiredMixin, DeleteView):
    model = VehicleReport
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:vehiclereport_list')

    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context.update({'page_title': _('Видалити Звіт #{}').format(
        self.object.pk), 'object_type_display': _('Звіт по транспорту'), 'object_name': f"Звіт #{self.object.pk}", 'cancel_url': self.success_url}); return context
    def post(self, request, *args, **kwargs): pk = self.get_object().pk; response = super().delete(request,
                                                                                                   *args, **kwargs); messages.success(self.request, _("Звіт #{} видалено.").format(pk)); return response





class ChargingStationListView(SuperUserRequiredMixin, ListView):  
    model = ChargingStation
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 15
    def get_queryset(self): return super().get_queryset().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Зарядні Станції'),
            'list_fields': ['id', 'name_link_admin', 'address_short', 'status', 'is_active_display', 'is_reservable_display'],
            'model_name_plural': _("Зарядні станції"), 'model_name_singular': _("Зарядну станцію"),
            'create_url_name': 'administration:chargingstation_create',
            'update_url_name': 'administration:chargingstation_update',
            'delete_url_name': 'administration:chargingstation_delete'
        })
        for obj in context['objects']:
            setattr(obj, 'name_link_admin', lambda o=obj: format_html(
                '<a href="{}" class="hover:text-yellow-600 font-medium">{}</a>', reverse('administration:chargingstation_update', args=[o.pk]), o.name))
            setattr(obj, 'address_short', (obj.address[:50] + '...') if obj.address and len(
                obj.address) > 50 else obj.address)
            setattr(obj, 'is_active_display', _("Так")
                    if obj.is_active else _("Ні"))
            setattr(obj, 'is_reservable_display', _("Так")
                    if obj.is_reservable else _("Ні"))
        return context


class ChargingStationCreateView(SuperUserRequiredMixin, CreateView):
    model = ChargingStation
    form_class = ChargingStationAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:chargingstation_list')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _(
    'Додати Станцію'), 'form_title': _('Нова зарядна станція'), 'button_text': _('Створити'), 'back_url': self.success_url}); return ctx
    
    def form_valid(self, form): messages.success(self.request, _(
    "Станцію «{}» створено.").format(form.instance.name)); return super().form_valid(form)


class ChargingStationUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ChargingStation
    form_class = ChargingStationAdminForm
    template_name = 'administration/generic_form.html'
    success_url = reverse_lazy('administration:chargingstation_list')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Редагувати: {}').format(self.object.name), 'form_title': _('Редагування станції #{}').format(self.object.pk), 'button_text': _('Зберегти'), 'back_url': self.success_url}); return ctx; 
    
    def form_valid(self, form): messages.success(self.request, _("Станцію «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)


class ChargingStationDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ChargingStation
    template_name = 'administration/confirm_delete.html'
    success_url = reverse_lazy('administration:chargingstation_list')
    
    def get_context_data(self, **kwargs): ctx = super().get_context_data(**kwargs); ctx.update({'page_title': _('Видалити: {}').format(self.object.name), 'object_type_display': _('Зарядну станцію'), 'object_name': self.object.name, 'cancel_url': self.success_url}); return ctx; 
    def post(self, request, *args, **kwargs): name = self.get_object().name; resp = super().delete(request, *args, **kwargs); messages.success(self.request, _("Зарядну станцію «{}» видалено.").format(name)); return resp

class ProductBrandListView(SuperUserRequiredMixin, ListView):
    model = ProductBrand
    template_name = 'administration/generic_list.html'
    context_object_name = 'objects'
    paginate_by = 30
    def get_queryset(self): return super().get_queryset().annotate(product_count_ann=Count('products')).order_by('name')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _('Бренди Товарів'),
            'list_fields': ['name', 'slug', 'product_count_ann'],
            'model_name_plural': _("Бренди товарів"),
            'model_name_singular': _("Бренд товарів"),
            'create_url_name': 'administration:productbrand_create',
            'update_url_name': 'administration:productbrand_update',
            'delete_url_name': 'administration:productbrand_delete',
        })
        return context

class ProductBrandCreateView(SuperUserRequiredMixin, CreateView):
    model = ProductBrand; form_class = ProductBrandAdminForm
    template_name = 'administration/generic_form.html'; success_url = reverse_lazy('administration:productbrand_list')
    def get_context_data(self, **kwargs): context=super().get_context_data(**kwargs); context.update({'page_title':_('Створити Бренд Товарів'),'form_title':_('Новий бренд'),'button_text':_('Створити'),'back_url':self.success_url}); return context
    def form_valid(self, form): messages.success(self.request, _("Бренд «{}» створено.").format(form.instance.name)); return super().form_valid(form)

class ProductBrandUpdateView(SuperUserRequiredMixin, UpdateView):
    model = ProductBrand; form_class = ProductBrandAdminForm
    template_name = 'administration/generic_form.html'; success_url = reverse_lazy('administration:productbrand_list')
    def get_context_data(self, **kwargs): context=super().get_context_data(**kwargs); context.update({'page_title':_('Редагувати Бренд: {}').format(self.object.name),'form_title':_('Редагування бренду #{}').format(self.object.pk),'button_text':_('Зберегти'),'back_url':self.success_url}); return context
    def form_valid(self, form): messages.success(self.request, _("Бренд «{}» оновлено.").format(form.instance.name)); return super().form_valid(form)

class ProductBrandDeleteView(SuperUserRequiredMixin, DeleteView):
    model = ProductBrand; template_name = 'administration/confirm_delete.html'; success_url = reverse_lazy('administration:productbrand_list')
    def get_context_data(self, **kwargs): context=super().get_context_data(**kwargs); context.update({'page_title':_('Видалити: {}').format(self.object.name),'object_type_display':_('Бренд товарів'),'object_name':self.object.name,'cancel_url':self.success_url}); return context
    def post(self, request, *args, **kwargs): object_name = self.get_object().name; response = super().delete(request, *args, **kwargs); messages.success(self.request, _("Бренд «{}» видалено.").format(object_name)); return response