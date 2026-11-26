import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import (
    HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, 
    Http404, HttpResponse, HttpResponseNotFound
)
import uuid
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Prefetch, F, Max, ExpressionWrapper, DecimalField, Case, When, Value
from decimal import Decimal
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.template.loader import render_to_string
from django.templatetags.static import static
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

from .models import Listing, ListingImage, ListingFeature, Category, ChatRoom, ChatMessage
from .forms import ListingForm, ListingImageFormSet, ListingFeatureFormSet

from core.utils import get_exchange_rates_to_uah

User = get_user_model()


def get_favorite_statuses_for_listings(request, listings_queryset):
    """
    Вспомогательная функция для получения словаря статусов избранного для списка объявлений.
    `listings_queryset` - это queryset или список объектов Listing.
    """
    favorite_statuses = {}
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and hasattr(profile, 'favorite_listings'):
            listing_ids_on_page = [l.id for l in listings_queryset]
            user_favorite_ids = set(profile.favorite_listings.filter(id__in=listing_ids_on_page).values_list('id', flat=True))
            for listing_id in listing_ids_on_page:
                if listing_id in user_favorite_ids:
                    favorite_statuses[listing_id] = True
    return favorite_statuses


def marketplace_view(request):
    listings_qs_base = Listing.objects.filter(is_active_display=True, status='active') \
        .select_related('category', 'user', 'user__profile') \
        .prefetch_related(
            Prefetch('additional_images', queryset=ListingImage.objects.order_by('order', 'pk'))
        )

    categories = Category.objects.annotate(num_listings=Count('listing', filter=Q(listing__is_active_display=True, listing__status='active'))).filter(num_listings__gt=0).order_by('name')
    
    selected_category_slug = request.GET.get('category')
    selected_category = None
    if selected_category_slug:
        selected_category = get_object_or_404(Category, slug=selected_category_slug)
        listings_qs_base = listings_qs_base.filter(category=selected_category)

    query = request.GET.get('q')
    if query:
        listings_qs_base = listings_qs_base.filter(
            Q(title__icontains=query) | Q(description__icontains=query) |
            Q(brand__icontains=query) | Q(model_name__icontains=query) |
            Q(city__icontains=query)
        ).distinct()

    
    rates = get_exchange_rates_to_uah()

    
    price_in_uah_conditions = [
        When(currency=currency_code, then=F('price') * rate)
        for currency_code, rate in rates.items()
    ]
    
    
    listings_qs_base = listings_qs_base.annotate(
        price_in_uah=ExpressionWrapper(
            Case(*price_in_uah_conditions, default=F('price'), output_field=DecimalField(max_digits=14, decimal_places=2)),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    )

    
    min_price_str = request.GET.get('min_price')
    max_price_str = request.GET.get('max_price')
    
    filter_currency = request.GET.get('filter_currency', Listing.CURRENCY_UAH) 

    if min_price_str and min_price_str.replace('.', '', 1).isdigit():
        min_price_val = Decimal(min_price_str)
        
        min_price_in_uah = min_price_val * rates.get(filter_currency, Decimal('1.0'))
        listings_qs_base = listings_qs_base.filter(price_in_uah__gte=min_price_in_uah)

    if max_price_str and max_price_str.replace('.', '', 1).isdigit():
        max_price_val = Decimal(max_price_str)
        
        max_price_in_uah = max_price_val * rates.get(filter_currency, Decimal('1.0'))
        listings_qs_base = listings_qs_base.filter(price_in_uah__lte=max_price_in_uah)

    condition_filter = request.GET.get('condition')
    if condition_filter:
        listings_qs_base = listings_qs_base.filter(condition=condition_filter)

    
    sort_options = {
        '-updated_at': _('Спочатку оновлені'),
        'price_in_uah': _('Ціна: за зростанням'),      
        '-price_in_uah': _('Ціна: за спаданням'),     
        '-created_at': _('Спочатку нові'),
        'created_at': _('Спочатку старі'),
        '-views_count': _('За популярністю'),
    }
    sort_by = request.GET.get('sort', '-updated_at')
    
    
    valid_sort_fields = [f.name for f in Listing._meta.get_fields()] + list(listings_qs_base.query.annotations.keys())
    
    order_field = sort_by.lstrip('-')
    if order_field in valid_sort_fields:
        if sort_by in sort_options:
            listings_qs_ordered = listings_qs_base.order_by(sort_by)
        else: 
            listings_qs_ordered = listings_qs_base.order_by(sort_by if order_field == sort_by else F(order_field).desc(nulls_last=True) if sort_by.startswith('-') else F(order_field).asc(nulls_last=True) )
    else: 
        listings_qs_ordered = listings_qs_base.order_by('-updated_at')
        sort_by = '-updated_at'
        
    favorite_statuses = get_favorite_statuses_for_listings(request, listings_qs_ordered) 
            
    context = {
        "listings": listings_qs_ordered,
        "categories": categories,
        "selected_category": selected_category,
        "search_query": query,
        "current_sort": sort_by,
        "sort_options": sort_options,
        "min_price": min_price_str, 
        "max_price": max_price_str,
        "selected_condition": condition_filter,
        "condition_choices": Listing.CONDITION_CHOICES,
        "currency_choices": Listing.CURRENCY_CHOICES, 
        "selected_filter_currency": filter_currency,   
        "favorite_status": favorite_statuses,
    }
    return render(request, "marketplace/marketplace.html", context)




def marketplace_category_view(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    listings_qs_base = Listing.objects.filter(is_active_display=True, status='active', category=category)\
                           .select_related('user', 'user__profile')\
                           .prefetch_related(
                               Prefetch('additional_images', queryset=ListingImage.objects.order_by('order', 'pk'))
                           )
    
    categories = Category.objects.annotate(num_listings=Count('listing', filter=Q(listing__is_active_display=True, listing__status='active'))).filter(num_listings__gt=0).order_by('name')

    query = request.GET.get('q')
    if query:
         listings_qs_base = listings_qs_base.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(brand__icontains=query) | Q(model_name__icontains=query) | Q(city__icontains=query)).distinct()

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    condition_filter = request.GET.get('condition')

    if min_price and min_price.isdigit(): listings_qs_base = listings_qs_base.filter(price__gte=min_price)
    if max_price and max_price.isdigit(): listings_qs_base = listings_qs_base.filter(price__lte=max_price)
    if condition_filter: listings_qs_base = listings_qs_base.filter(condition=condition_filter)

    sort_by = request.GET.get('sort', '-updated_at')
    sort_options = {
        '-updated_at': _('Спочатку оновлені'), 'price': _('Ціна: за зростанням'), '-price': _('Ціна: за спаданням'),
        '-created_at': _('Спочатку нові'), 'created_at': _('Спочатку старі'), '-views_count': _('За популярністю'),
    }
    if sort_by in sort_options: 
        listings_qs_ordered = listings_qs_base.order_by(sort_by)
    else: 
        listings_qs_ordered = listings_qs_base.order_by('-updated_at')
        sort_by = '-updated_at'
    
    current_listings_on_page = listings_qs_ordered
    favorite_statuses = get_favorite_statuses_for_listings(request, current_listings_on_page)

    context = {
        "listings": listings_qs_ordered,
        "categories": categories,
        "selected_category": category,
        "search_query": query,
        "current_sort": sort_by,
        "sort_options": sort_options,
        "min_price": min_price,
        "max_price": max_price,
        "selected_condition": condition_filter,
        "condition_choices": Listing.CONDITION_CHOICES,
        "favorite_status": favorite_statuses,
    }
    return render(request, "marketplace/marketplace.html", context)




def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.prefetch_related(
            Prefetch('additional_images', queryset=ListingImage.objects.order_by('order', 'pk')),
            Prefetch('features', queryset=ListingFeature.objects.order_by('name')),
            Prefetch('chat_rooms', queryset=ChatRoom.objects.select_related('buyer', 'buyer__profile').order_by('-updated_at'))
        ).select_related('user', 'user__profile', 'category'),
        pk=pk
    )

    session_key = f'viewed_listing_{listing.pk}'
    if not request.session.get(session_key, False):
        Listing.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
        request.session[session_key] = True
        listing.refresh_from_db(fields=['views_count'])

    is_favorite_main_listing = False
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and hasattr(profile, 'favorite_listings'):
            is_favorite_main_listing = profile.favorite_listings.filter(pk=listing.pk).exists()

    related_listings_qs = listing.get_related_listings() 
    
    favorite_statuses_for_related = get_favorite_statuses_for_listings(request, related_listings_qs)
    
    chat_room_id = None
    can_chat = False
    is_listing_owner = False
    owner_chats = []
    if request.user.is_authenticated:
        is_listing_owner = (request.user == listing.user)
        if is_listing_owner:
            owner_chats = listing.chat_rooms.all() 
        elif request.user != listing.user and listing.status == 'active':
            can_chat = True
            room = ChatRoom.objects.filter(listing=listing, buyer=request.user).first()
            if room:
                chat_room_id = str(room.id)

    context = {
        'listing': listing,
        'related_listings': related_listings_qs,
        'is_listing_owner': is_listing_owner,
        'owner_chats': owner_chats,
        'can_chat': can_chat,
        'chat_room_id': chat_room_id,
        'is_favorite': is_favorite_main_listing,
        'favorite_status': favorite_statuses_for_related, 
    }
    return render(request, 'marketplace/listing_detail.html', context)






@login_required
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES, user=request.user)
        
        image_formset = ListingImageFormSet(request.POST, request.FILES, prefix='images', queryset=ListingImage.objects.none())
        feature_formset = ListingFeatureFormSet(request.POST, prefix='features', queryset=ListingFeature.objects.none())

        if form.is_valid() and image_formset.is_valid() and feature_formset.is_valid():
            try:
                with transaction.atomic():
                    listing = form.save(commit=False)
                    listing.user = request.user
                    
                    listing.status = Listing.STATUS_CHOICES[0][0] 
                    listing.is_active_display = True 
                    listing.save()
                    form.save_m2m() 

                    
                    image_formset.instance = listing
                    image_formset.save()
                    
                    feature_formset.instance = listing
                    feature_formset.save()

                    
                    

                messages.success(request, _("Оголошення '{title}' успішно створено!").format(title=listing.title))
                return redirect(listing.get_absolute_url())
            except Exception as e:
                 messages.error(request, _("Сталася помилка при збереженні: {}").format(e))
        else:
             error_txt = _("Будь ласка, виправте помилки: ")
             if form.errors: error_txt += " " + " ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
             if not image_formset.is_valid(): error_txt += " " + _("Помилки у формі зображень.")
             if not feature_formset.is_valid(): error_txt += " " + _("Помилки у формі характеристик.")
             messages.error(request, error_txt)
    else: 
        form = ListingForm(user=request.user)
        
        image_formset = ListingImageFormSet(prefix='images', queryset=ListingImage.objects.none())
        feature_formset = ListingFeatureFormSet(prefix='features', queryset=ListingFeature.objects.none())

    
    categories_for_form = Category.objects.all().order_by('name')

    context = {
        'form': form,
        'image_formset': image_formset,
        'feature_formset': feature_formset,
        'form_title': _("Створити нове оголошення"),
        'form_action_url': reverse('listing_create'),
        'button_text': _("Опублікувати оголошення"),
        'is_edit': False,
        'categories': categories_for_form, 
    }
    return render(request, 'marketplace/listing_form.html', context)


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.user != request.user and not request.user.is_staff: 
        messages.error(request, _("Ви не маєте права редагувати це оголошення."))
        return redirect(listing.get_absolute_url())

    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES, instance=listing, user=request.user)
        image_formset = ListingImageFormSet(request.POST, request.FILES, instance=listing, prefix='images')
        feature_formset = ListingFeatureFormSet(request.POST, instance=listing, prefix='features')

        if form.is_valid() and image_formset.is_valid() and feature_formset.is_valid():
            try:
                with transaction.atomic():
                    updated_listing = form.save() 
                    
                    image_formset.save()
                    feature_formset.save()
                    
                    

                messages.success(request, _("Оголошення '{title}' успішно оновлено!").format(title=updated_listing.title))
                return redirect(updated_listing.get_absolute_url())
            except Exception as e:
                messages.error(request, _("Сталася помилка при оновленні: {}").format(e))
        else:
            error_txt = _("Будь ласка, виправте помилки:")
            if form.errors: error_txt += " " + " ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
            if not image_formset.is_valid(): error_txt += " " + _("Помилки у формі зображень.")
            if not feature_formset.is_valid(): error_txt += " " + _("Помилки у формі характеристик.")
            messages.error(request, error_txt)
    else: 
        form = ListingForm(instance=listing, user=request.user)
        image_formset = ListingImageFormSet(instance=listing, prefix='images')
        feature_formset = ListingFeatureFormSet(instance=listing, prefix='features')

    categories_for_form = Category.objects.all().order_by('name')
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'feature_formset': feature_formset,
        'listing': listing, 
        'form_title': _("Редагувати: {title}").format(title=listing.title),
        'form_action_url': reverse('listing_edit', kwargs={'pk': listing.pk}),
        'button_text': _("Зберегти зміни"),
        'is_edit': True,
        'categories': categories_for_form,
    }
    return render(request, 'marketplace/listing_form.html', context)


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.user != request.user and not request.user.is_staff:
         messages.error(request, _("Ви не маєте права видаляти це оголошення."))
         return redirect(listing.get_absolute_url())

    if request.method == "POST":
        listing_title = listing.title
        try:
            with transaction.atomic():
                if listing.main_image: listing.main_image.delete(save=False)
                for img_obj in listing.additional_images.all():
                    if img_obj.image: img_obj.image.delete(save=False)
                listing.delete()
            messages.success(request, _("Оголошення '{title}' успішно видалено.").format(title=listing_title))
            return redirect('marketplace-view')
        except Exception as e:
             messages.error(request, _("Помилка при видаленні: {}").format(e))
             return redirect(listing.get_absolute_url())

    context = {'listing': listing}
    return render(request, 'marketplace/listing_confirm_delete.html', context)

@require_POST
@login_required
def toggle_favorite_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    user = request.user
    profile = getattr(user, 'profile', None)

    if not profile:
        
        return HttpResponse(
            "<div id='htmx-global-error' hx-swap-oob='beforeend'><p class='text-red-500 p-2'>Помилка: профіль не знайдено. Будь ласка, оновіть сторінку.</p></div>", 
            status=200 
        )

    is_favorite_currently = listing in profile.favorite_listings.all()
    source = request.GET.get('source', 'list') 
    added_to_favorites_now = False

    if is_favorite_currently:
        profile.favorite_listings.remove(listing)
        added_to_favorites_now = False
    else:
        profile.favorite_listings.add(listing)
        added_to_favorites_now = True
    
    listing_count = profile.favorite_listings.count()
    product_count = 0
    if hasattr(user, 'favorite_products'):
        product_count = user.favorite_products.count()
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
        template_name = 'marketplace/partials/favorite_button_listing.html'
        button_context = {
            'listing': listing, 
            'is_favorite': added_to_favorites_now,
            'request': request,
            'source': source 
        }
        response_main_content = render_to_string(template_name, button_context, request=request)
    
    final_response_html = response_main_content + counter_oob_swap
    return HttpResponse(final_response_html)





@login_required
@require_POST
def get_or_create_chat(request, listing_id):
    listing = get_object_or_404(Listing.objects.select_related('user'), pk=listing_id)
    buyer = request.user

    if buyer == listing.user:
        return JsonResponse({'status': 'error', 'message': _("Ви не можете почати чат самі з собою.")}, status=400)
    
    if listing.status != 'active':
        return JsonResponse({'status': 'error', 'message': _("Чат можливий тільки для активних оголошень.")}, status=400)

    room, created = ChatRoom.objects.get_or_create(
        listing=listing,
        buyer=buyer,
        defaults={'seller': listing.user}
    )
    if not created and not room.seller:
        room.seller = listing.user
        room.save(update_fields=['seller'])

    return JsonResponse({'status': 'success', 'room_id': str(room.id)})


@login_required
def get_chat_messages(request, room_id):
    try:

        valid_room_id = uuid.UUID(str(room_id))
    except ValueError:
        return JsonResponse({'status': 'error', 'message': _("Невірний формат ID кімнати.")}, status=400)

    room = get_object_or_404(
        ChatRoom.objects.select_related(
            'listing', 'buyer', 'seller',
            'buyer__profile', 'seller__profile'
        ),
        pk=valid_room_id
    )

    if request.user != room.buyer and request.user != room.seller:
        return JsonResponse({'status': 'error', 'message': _("Доступ заборонено.")}, status=403)

    messages_qs = room.messages.select_related('sender', 'sender__profile').order_by('timestamp')[:500]
    messages_data = []
    default_avatar_url = static('images/default_avatar.png')

    for msg in messages_qs:
        sender_profile = getattr(msg.sender, 'profile', None)
        avatar_url = sender_profile.avatar.url if sender_profile and sender_profile.avatar else default_avatar_url
        
        current_content = msg.content





        messages_data.append({
            'id': msg.id,
            'sender_id': str(msg.sender.id),
            'sender_display_name': msg.sender.get_full_name() or msg.sender.username,
            'sender_avatar_url': avatar_url,
            'content': current_content,
            'timestamp': msg.timestamp.isoformat(),
            'message_type': msg.message_type,
            'image_url': msg.image.url if msg.message_type == 'image' and msg.image else None,
            'is_deleted_by_sender': msg.is_deleted_by_sender,
            'is_edited': msg.is_edited,
        })

    opponent = room.seller if request.user == room.buyer else room.buyer
    opponent_profile = getattr(opponent, 'profile', None)
    opponent_avatar_url = opponent_profile.avatar.url if opponent_profile and opponent_profile.avatar else default_avatar_url
    


    opponent_is_online = False

    return JsonResponse({
        'status': 'success',
        'messages': messages_data,
        'opponent_id': str(opponent.id),
        'opponent_username': opponent.get_full_name() or opponent.username,
        'opponent_avatar_url': opponent_avatar_url,
        'opponent_is_online': opponent_is_online,
    })

@login_required
@require_POST
def upload_chat_image(request):
    room_id_str = request.POST.get('room_id')
    image_file = request.FILES.get('image')
    caption = request.POST.get('caption', '')

    if not room_id_str or not image_file:
        return JsonResponse({'status': 'error', 'message': _("Необхідні дані відсутні.")}, status=400)

    try:
        room_id_uuid = uuid.UUID(room_id_str)
        room = ChatRoom.objects.select_related('buyer', 'seller').get(pk=room_id_uuid)
    except (ValueError, ChatRoom.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': _("Кімнату чату не знайдено.")}, status=404)

    if request.user != room.buyer and request.user != room.seller:
        return JsonResponse({'status': 'error', 'message': _("Доступ заборонено.")}, status=403)

    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': _("Файл занадто великий (макс. 5MB).")}, status=400)
    
    allowed_content_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if image_file.content_type not in allowed_content_types:
        return JsonResponse({'status': 'error', 'message': _("Непідтримуваний тип файлу.")}, status=400)

    try:
        chat_message = ChatMessage(
            room=room,
            sender=request.user,
            content=caption,
            message_type='image',
            image=image_file
        )
        chat_message.full_clean()
        chat_message.save()
    except ValidationError as e:
        error_message = e.message_dict.get('__all__', [str(e)])[0]
        return JsonResponse({'status': 'error', 'message': error_message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': _("Помилка збереження: {}").format(str(e))}, status=500)

    channel_layer = get_channel_layer()
    group_name = room.room_group_name
    sender_profile = getattr(request.user, 'profile', None)
    default_avatar_url = static('images/default_avatar.png')
    sender_avatar_url = sender_profile.avatar.url if sender_profile and sender_profile.avatar else default_avatar_url

    message_data_for_ws = {
        'type': 'chat_message_broadcast',
        'message': {
            'id': chat_message.id,
            'user_id': str(request.user.id),
            'username': request.user.get_full_name() or request.user.username,
            'avatar_url': sender_avatar_url,
            'message': chat_message.content,
            'timestamp': chat_message.timestamp.isoformat(),
            'message_type': 'image',
            'image_url': chat_message.image.url,
            'is_edited': chat_message.is_edited,
            'is_deleted_by_sender': chat_message.is_deleted_by_sender,
        }
    }
    async_to_sync(channel_layer.group_send)(group_name, message_data_for_ws)
    return JsonResponse({'status': 'success', 'message_id': chat_message.id, 'image_url': chat_message.image.url, 'caption': chat_message.content})

@login_required
@require_POST
def hide_chat_room(request, room_id):
    try:
        valid_room_id = uuid.UUID(str(room_id))
    except ValueError:
        return JsonResponse({'status': 'error', 'message': _("Невірний формат ID кімнати.")}, status=400)
        
    room = get_object_or_404(ChatRoom, pk=valid_room_id)
    if request.user != room.buyer and request.user != room.seller:
        return JsonResponse({'status': 'error', 'message': _("Доступ заборонено.")}, status=403)

    if room.hide_for_user(request.user):
        return JsonResponse({'status': 'success', 'message': _("Чат приховано.")})
    else:
        return JsonResponse({'status': 'error', 'message': _("Не вдалося приховати чат.")}, status=500)

@login_required
@require_POST
def delete_chat_message(request, message_id):
    message = get_object_or_404(ChatMessage.objects.select_related('room', 'sender'), pk=message_id)

    if message.sender != request.user:
        return JsonResponse({'status': 'error', 'message': _("Ви не можете видалити це повідомлення.")}, status=403)

    time_limit_seconds = 3600
    if (timezone.now() - message.timestamp).total_seconds() > time_limit_seconds and not request.user.is_staff:
         return JsonResponse({'status': 'error', 'message': _("Час на видалення повідомлення вичерпано.")}, status=403)

    if message.mark_as_deleted(request.user):
        channel_layer = get_channel_layer()
        group_name = message.room.room_group_name
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'chat_message_deleted_broadcast',
                'message_id': message.id,
                'room_id': str(message.room.id),

            }
        )
        return JsonResponse({'status': 'success', 'message': _("Повідомлення видалено.")})
    else:
        return JsonResponse({'status': 'error', 'message': _("Не вдалося видалити повідомлення.")}, status=500)

@login_required
@require_POST
def edit_chat_message(request, message_id):
    message = get_object_or_404(ChatMessage.objects.select_related('room', 'sender'), pk=message_id)
    if message.sender != request.user:
        return JsonResponse({'status': 'error', 'message': _("Ви не можете редагувати це повідомлення.")}, status=403)
    if message.is_deleted_by_sender:
        return JsonResponse({'status': 'error', 'message': _("Видалене повідомлення не можна редагувати.")}, status=403)

    try:
        data = json.loads(request.body)
        new_content = data.get('content', '')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': _("Невірний формат запиту.")}, status=400)


    if message.message_type == 'text' and not new_content.strip():
        return JsonResponse({'status': 'error', 'message': _("Текстове повідомлення не може бути порожнім.")}, status=400)

    time_limit_seconds = 3600
    if (timezone.now() - message.timestamp).total_seconds() > time_limit_seconds and not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': _("Час на редагування повідомлення вичерпано.")}, status=403)

    if message.edit_message(request.user, new_content):
        channel_layer = get_channel_layer()
        group_name = message.room.room_group_name
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'chat_message_edited_broadcast',
                'message_id': message.id,
                'new_content': message.content,
                'is_edited_flag': message.is_edited,
            }
        )
        return JsonResponse({'status': 'success', 'message': _("Повідомлення оновлено."), 'new_content': message.content})
    else:
        return JsonResponse({'status': 'error', 'message': _("Не вдалося оновити повідомлення.")}, status=500)