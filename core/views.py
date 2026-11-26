import json
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Min, Max, Avg, F, Count, OuterRef, Subquery, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from transport.models import ElectricVehicle, VehicleReport
from product.models import Product, Category, Review, Brand
from marketplace.models import Listing, ListingImage
from forum.models import UserPost
from cart.models import Order
from core.models import Profile
from django.contrib import messages
from .forms import NewsletterSubscriptionForm
from django.conf import settings
from django.core.mail import send_mail
from core.models import NewsletterSubscriber
from .forms import UserCreationForm
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .utils import generate_ai_email_content
from django.utils.translation import gettext_lazy as _
from product.models import Product, Category as ProductCategory, Brand
from forum.models import UserPost, Category
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.models import User
from cart.models import Order
from django.db.models import Prefetch
from .forms import SignUpForm





def frontpage(request):
    """Головна сторінка + обробка підписки на новини з AI email"""
    products = Product.objects.filter(in_stock=True).order_by('-created_at')[:8]
    form = NewsletterSubscriptionForm()
    featured_reviews = Review.objects.filter(rating=5).select_related('user').order_by('-created_at')[:3]

    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if NewsletterSubscriber.objects.filter(email=email).exists():
                messages.warning(request, _('Цей email вже підписаний на новини!'))
            else:

                try:
                    NewsletterSubscriber.objects.create(email=email)
                except Exception as e:
                    messages.error(request, _('Не вдалося зберегти підписку. Спробуйте пізніше.'))
                    print(f"ERROR saving subscriber {email}: {e}")
                    return redirect('frontpage')


                subject = _('Ласкаво просимо до ElectroHub!')
                email_context = {'email': email}
                ai_message_body = generate_ai_email_content(
                    email_type='newsletter_welcome',
                    context_data=email_context
                )


                fallback_message = _(
                    "Вітаємо!\n\n"
                    "Ви успішно підписалися на нашу розсилку новин.\n\n"
                    "Незабаром ви почнете отримувати останні новини про електротранспорт, "
                    "ексклюзивні пропозиції та корисні поради.\n\n"
                    "Дякуємо, що ви з нами!"
                )


                message_to_send = ai_message_body
                if "Помилка:" in ai_message_body:
                    print(f"WARNING: AI email generation failed for {email}. Using fallback. Error: {ai_message_body}")
                    message_to_send = fallback_message

                    messages.success(request, _('Ви успішно підписалися на новини!'))
                else:
                     messages.success(request, _('Ви успішно підписалися на новини! Лист-вітання вже в дорозі.'))


                try:
                    send_mail(subject, message_to_send, settings.EMAIL_HOST_USER, [email], fail_silently=False)

                    admin_message = f"Нова підписка на новини: {email}"
                    try:
                         send_mail('Нова підписка', admin_message, settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER], fail_silently=False)
                    except Exception as admin_e:
                         print(f"ERROR sending admin notification email: {admin_e}")

                except Exception as e:
                    print(f"ERROR sending welcome email to {email}: {e}")

                    messages.error(request, _('Підписка оформлена, але сталася помилка під час відправки вітального листа.'))

        else:
            messages.error(request, _('Будь ласка, введіть коректний email.'))

        return redirect('frontpage')


    context = {
        'products': products,
        'form': form,
        'featured_reviews': featured_reviews
    }
    return render(request, 'core/frontpage.html', context)

def aboutus(request):
    """Страница о нас"""
    return render(request, 'core/aboutus.html')

def signup(request):
    if request.user.is_authenticated:
        return redirect('core:myaccount')

    if request.method == 'POST':
        print("SIGNUP: POST request received")
        form = SignUpForm(request.POST)
        if form.is_valid():
            print("SIGNUP: Form is valid")
            user = form.save()
            Profile.objects.get_or_create(user=user)
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, _('Реєстрація успішна! Ласкаво просимо, {}!').format(user.get_full_name() or user.username))
            
            next_url = request.POST.get('next')
            if not next_url:
                next_url = request.GET.get('next')

            print(f"SIGNUP: Next URL is '{next_url}'")
            
            if next_url:
                print(f"SIGNUP: Redirecting to next_url: {next_url}")
                return redirect(next_url)
            
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
            print(f"SIGNUP: Redirecting to LOGIN_REDIRECT_URL: {redirect_to}")
            return redirect(redirect_to)
        else:
            print("SIGNUP: Form is NOT valid")
            print(form.errors.as_json())

    else:
        print("SIGNUP: GET request, creating new form")
        form = SignUpForm()
        
    return render(request, 'core/signup.html', {'form': form})



def login(request):
    """Обробляє вхід користувача."""
    if request.user.is_authenticated:
        return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))

    redirect_to = request.POST.get('next', request.GET.get('next', ''))

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, _('Ви успішно увійшли.'))

            url_is_safe = url_has_allowed_host_and_scheme(
                url=redirect_to, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            )
            if url_is_safe and redirect_to:
                return redirect(resolve_url(redirect_to))
            else:
                return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
        else:
            messages.error(request, _('Неправильний логін або пароль. Спробуйте ще раз.'))
    else:
        form = AuthenticationForm()

    context = {'form': form, 'next': redirect_to}
    return render(request, 'core/login.html', context)

@login_required
def myaccount(request):
    """Страница аккаунта пользователя"""
    vehicles = ElectricVehicle.objects.filter(user=request.user)
    reports = VehicleReport.objects.filter(vehicle__user=request.user)
    listings = Listing.objects.filter(user=request.user, is_active_display=True)
    forum_topics = UserPost.objects.filter(author__user=request.user)
    orders = Order.objects.filter(user=request.user)
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at').prefetch_related('items__product')


    context = {
        'vehicles': vehicles,
        'reports': reports,
        'listings': listings,
        'forum_topics': forum_topics,
        'user_orders': user_orders,
        'OrderStatus': Order.OrderStatus,
    }

    return render(request, 'core/myaccount.html', context)

@login_required
def edit_myaccount(request):
    """Редактирование данных профиля пользователя"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:

        profile = Profile.objects.create(user=request.user)

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")


        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email
        user.save()


        if request.FILES.get("avatar"):
            profile.avatar = request.FILES["avatar"]
            profile.save()

        return redirect("myaccount")

    return render(request, "core/edit_myaccount.html", {"profile": profile})

from django.db.models import Q

def shop(request):
    """Відображає сторінку каталогу товарів з фільтрацією, сортуванням та пагінацією."""


    approved_reviews_subquery = Review.objects.filter(
        product=OuterRef('pk'),
        is_approved=True
    ).values('product').annotate(count=Count('pk')).values('count')


    products_qs = Product.objects.filter(is_active=True) \
        .select_related('category', 'brand', 'part_type') \
        .prefetch_related('compatible_models') \
        .annotate(
            approved_reviews_count=Subquery(approved_reviews_subquery, output_field=IntegerField(default=0))
        )


    categories = ProductCategory.objects.filter(is_active=True).prefetch_related('children')
    all_brands = Brand.objects.filter(products__is_active=True).distinct().order_by('name')


    aggregate_result = Product.objects.filter(is_active=True).aggregate(min_p=Min('price'), max_p=Max('price'))
    absolute_min_price = int(aggregate_result['min_p'] or 0)
    absolute_max_price = int(aggregate_result['max_p'] or 10000)
    if absolute_max_price <= absolute_min_price:
        absolute_max_price = absolute_min_price + 100


    query = request.GET.get('q', '').strip()
    active_category_slug = request.GET.get('category', '')
    selected_brands_slugs = request.GET.getlist('brand')
    min_price_str = request.GET.get('min_price', str(absolute_min_price))
    max_price_str = request.GET.get('max_price', str(absolute_max_price))
    selected_rating_str = request.GET.get('rating_gte')
    in_stock_only = request.GET.get('in_stock') == 'true'
    sort = request.GET.get('sort', '-created_at')

    active_category_name = None
    active_category = None




    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query) | Q(sku__iexact=query) |
            Q(short_description__icontains=query) | Q(description__icontains=query) |
            Q(brand__name__icontains=query)
        ).distinct()


    if active_category_slug:
        try:
            active_category = ProductCategory.objects.get(slug=active_category_slug, is_active=True)
            active_category_name = active_category.name
            products_qs = products_qs.filter(category=active_category)
        except ProductCategory.DoesNotExist:
            active_category_slug = ''
            active_category = None


    if selected_brands_slugs:
        products_qs = products_qs.filter(brand__slug__in=selected_brands_slugs)


    current_min_price = absolute_min_price
    current_max_price = absolute_max_price
    try:
        min_price_num = Decimal(min_price_str)
        if min_price_num > absolute_min_price:
            products_qs = products_qs.filter(price__gte=min_price_num)
        current_min_price = int(min_price_num)
    except (ValueError, TypeError):
        min_price_str = str(absolute_min_price)

    try:
        max_price_num = Decimal(max_price_str)
        if max_price_num < absolute_max_price:
            products_qs = products_qs.filter(price__lte=max_price_num)
        current_max_price = int(max_price_num)
    except (ValueError, TypeError):
        max_price_str = str(absolute_max_price)


    needs_avg_rating_annotation = bool(selected_rating_str) or sort == 'rating_desc'
    if needs_avg_rating_annotation and 'avg_rating' not in products_qs.query.annotations:
         products_qs = products_qs.annotate(
             avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
         )
    try:
        if selected_rating_str and selected_rating_str.isdigit():
            selected_rating_num = int(selected_rating_str)

            if 'avg_rating' in products_qs.query.annotations:
                products_qs = products_qs.filter(avg_rating__gte=selected_rating_num)
            else:

                pass
        else:
            selected_rating_str = None
    except (ValueError, TypeError):
        selected_rating_str = None


    if in_stock_only:
        products_qs = products_qs.filter(in_stock=True)


    sort_options = {
        'price_asc': 'price', 'price_desc': '-price', 'newest': '-created_at',
        'oldest': 'created_at', 'rating_desc': '-avg_rating', 'name_asc': 'name', 'name_desc': '-name',
    }
    order_by_field = sort_options.get(sort, '-created_at')

    if sort == 'rating_desc':

        if 'avg_rating' not in products_qs.query.annotations:
             products_qs = products_qs.annotate(avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)))

        products_qs = products_qs.order_by(F('avg_rating').desc(nulls_last=True), '-created_at')
    else:

        products_qs = products_qs.order_by(order_by_field)


    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    favorite_status = {}
    if request.user.is_authenticated:
        favorite_ids = set(request.user.favorite_products.values_list('id', flat=True))
        for product_item in page_obj.object_list:
            favorite_status[product_item.id] = product_item.id in favorite_ids


    context = {
        'products': page_obj,
        'categories': categories,
        'all_brands': all_brands,

        'query': query,
        'active_category_slug': active_category_slug,
        'active_category_name': active_category_name,
        'active_category': active_category,
        'selected_brands': selected_brands_slugs,
        'current_min_price': current_min_price,
        'current_max_price': current_max_price,
        'min_price_value': min_price_str,
        'max_price_value': max_price_str,
        'selected_rating': selected_rating_str,
        'in_stock': in_stock_only,
        'sort': sort,

        'min_product_price': absolute_min_price,
        'max_product_price': absolute_max_price,

        'page_obj': page_obj,
        'paginator': paginator,

        'favorite_status': favorite_status,
        'source': 'shop',
    }
    return render(request, 'core/shop.html', context)










def subscribe_newsletter(request):
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():

            email = form.cleaned_data['email']
            NewsletterSubscriber.objects.create(email=email)
            

            try:
                send_mail(
                    'Підписка на новини підтверджена',
                    'Дякуємо за підписку на наші новини! Тепер ви будете отримувати найактуальнішу інформацію.',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                

                send_mail(
                    'Нова підписка на новини',
                    f'Нова підписка на новини з email: {email}',
                    settings.EMAIL_HOST_USER,
                    [settings.EMAIL_HOST_USER],
                    fail_silently=False,
                )
                

                messages.success(request, 'Ви успішно підписалися на новини!')
            except Exception as e:
                messages.error(request, f'Ошибка при отправке почты: {e}')
        else:
            messages.error(request, 'Будь ласка, введіть коректний email.')
        return redirect('frontpage')
    return render(request, 'core/frontpage.html', {'form': form})

def favorites_count(request):
    count = 0
    if request.user.is_authenticated:
        product_count = 0
        if hasattr(request.user, 'favorite_products'): 
            product_count = request.user.favorite_products.count()
        
        listing_count = 0
        profile = getattr(request.user, 'profile', None)
        if profile and hasattr(profile, 'favorite_listings'):
            listing_count = profile.favorite_listings.count()
        count = product_count + listing_count
    return render(request, 'core/favorites_count.html', {'favorites_total_count': count})

@login_required
def favorites(request):
    favorite_products = []
    favorite_listings = []

    if request.user.is_authenticated:
        if hasattr(request.user, 'favorite_products'):
            favorite_products = request.user.favorite_products.all().select_related('category')
        
        profile = getattr(request.user, 'profile', None)
        if profile and hasattr(profile, 'favorite_listings'):
            favorite_listings = profile.favorite_listings.all().select_related('category', 'user', 'user__profile')
    
    context = {
        'favorite_products': favorite_products,
        'favorite_listings': favorite_listings,

    }
    return render(request, 'core/favorites.html', context)

@login_required
def favorites_preview(request):
    limit = 5
    favorite_products = []
    favorite_listings = []

    if request.user.is_authenticated:
        if hasattr(request.user, 'favorite_products'):
            favorite_products = request.user.favorite_products.all().select_related('category')[:limit]
        
        profile = getattr(request.user, 'profile', None)
        if profile and hasattr(profile, 'favorite_listings'):
            favorite_listings_qs = profile.favorite_listings.all() \
                .select_related('category', 'user', 'user__profile') \
                .prefetch_related(
                    Prefetch(
                        'additional_images',  
                        queryset=ListingImage.objects.order_by('order', 'pk'),
                        to_attr='prefetched_additional_images' 
                    )
                )
            

            favorite_listings_list = list(favorite_listings_qs[:limit])


            for listing_item in favorite_listings_list:
                if hasattr(listing_item, 'prefetched_additional_images') and listing_item.prefetched_additional_images:
                    listing_item.first_preview_image = listing_item.prefetched_additional_images[0]
                else:
                    listing_item.first_preview_image = None
            favorite_listings = favorite_listings_list 

    context = {
        'favorite_products': favorite_products,
        'favorite_listings': favorite_listings, 
    }
    html = render_to_string('core/favorites_preview.html', context, request=request)
    return HttpResponse(html)


@require_POST
@login_required
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    user = request.user
    
    if not hasattr(user, 'favorite_products'):
         return HttpResponseBadRequest("Favorite products feature not available for this user.")

    is_favorite_currently = user.favorite_products.filter(id=product.id).exists()
    source = request.GET.get('source', 'list') 
    added_to_favorites_now = False

    if is_favorite_currently:
        user.favorite_products.remove(product)
        added_to_favorites_now = False
    else:
        user.favorite_products.add(product)
        added_to_favorites_now = True

    product_count = user.favorite_products.count()
    listing_count = 0
    profile = getattr(user, 'profile', None)
    if profile and hasattr(profile, 'favorite_listings'):
        listing_count = profile.favorite_listings.count()
    favorites_total_count = product_count + listing_count

    counter_html = render_to_string(
        'core/favorites_count.html',
        {'favorites_total_count': favorites_total_count},
        request=request
    )
    counter_oob_swap = f"""
    <div id="favorites-counter-container" hx-swap-oob="innerHTML">
        {counter_html}
    </div>
    """
    response_main_content = ""

    if source == 'favorites_page' and not added_to_favorites_now:
        response_main_content = "" 
    else:
        template_mapping = {
            'shop': 'core/partials/toggle_favorite_icon.html',
            'product_detail': 'core/partials/favorite_button.html',
            'similar': 'core/partials/toggle_favorite_icon.html',
            'list': 'core/partials/toggle_favorite_icon.html',
            'favorites_page': 'core/partials/favorite_button.html', 
        }
        template_name = template_mapping.get(source, 'core/partials/toggle_favorite_icon.html')
        button_context = {
            'product': product, 
            'is_favorite': added_to_favorites_now, 
            'source': source, 
            'request': request
        }
        response_main_content = render_to_string(template_name, button_context, request=request)

    final_response_html = response_main_content + counter_oob_swap
    return HttpResponse(final_response_html)



def public_user_profile(request, username):
    profile_owner = get_object_or_404(User.objects.select_related('profile'), username=username)
    


    user_listings = Listing.objects.filter(user=profile_owner, is_active_display=True).order_by('-created_at')[:10]


    context = {
        'profile_user': profile_owner,
        'user_listings': user_listings,

    }
    return render(request, 'core/public_profile.html', context)


