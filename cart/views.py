
import stripe
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction, DatabaseError
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .cart import Cart
from product.models import Product
from .models import Order, OrderItem
from decimal import Decimal
from django.utils.html import format_html
from django.http import Http404

logger = logging.getLogger(__name__)


if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
    if settings.STRIPE_SECRET_KEY.startswith("sk_test_") or settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        logger.info("Stripe API Key успішно завантажено для cart.views.")
    else:
        logger.error("ПОМИЛКА КОНФІГУРАЦІЇ (cart.views): STRIPE_SECRET_KEY має невірний формат.")
        stripe.api_key = None 
else:
    logger.error("ПОМИЛКА КОНФІГУРАЦІЇ (cart.views): STRIPE_SECRET_KEY не знайдено в налаштуваннях Django!")
    stripe.api_key = None



@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, in_stock=True)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product_id=product.id, quantity=quantity, update_quantity=False)
    new_total_quantity = cart.get_total_quantity()
    counter_html = render_to_string('cart/partials/cart_total.html', {'cart_total_quantity': new_total_quantity})
    oob_counter_response = f"""<div id="cart-counter-container" hx-swap-oob="innerHTML">{counter_html}</div>"""
    message_id = f"cart-message-{product.id}"
    message_html = format_html("""<span id="{}" hx-swap-oob="outerHTML" _="on load wait 3s remove me"><span class="text-green-600 text-xs ml-1">Додано!</span></span>""", message_id)
    return HttpResponse(oob_counter_response + message_html)

@require_POST
def update_cart(request, product_id, action):
    cart = Cart(request)
    logger.debug(f"update_cart: product_id={product_id}, action={action}")
    if action == 'increment':
        cart.add(product_id=product_id, quantity=1, update_quantity=False)
    elif action == 'decrement':
        cart.add(product_id=product_id, quantity=-1, update_quantity=True) 
    elif action == 'remove':
        cart.remove(str(product_id))
    else:
        logger.warning(f"update_cart: Невідома дія '{action}' для товару {product_id}")
        return HttpResponse("Невідома дія", status=400)

    new_total_quantity = cart.get_total_quantity()
    counter_html = render_to_string('cart/partials/cart_total.html', {'cart_total_quantity': new_total_quantity})
    oob_counter_response = f"""<div id="cart-counter-container" hx-swap-oob="innerHTML">{counter_html}</div>"""
    summary_context = {'cart': cart}
    summary_html = render_to_string('cart/partials/cart_summary_total.html', summary_context, request=request)
    oob_summary_response = f"""<span id="cart-summary-total-container" hx-swap-oob="innerHTML">{summary_html}</span>"""
    main_response_html = ""
    if action != 'remove':
        item_data_from_session = cart.get_item(str(product_id))
        if item_data_from_session:
            try:
                product = Product.objects.get(id=product_id)
                price_decimal = Decimal(item_data_from_session['price'])
                item_total_price = item_data_from_session['quantity'] * price_decimal
                item_context_for_template = {'item': {'product': product, 'quantity': item_data_from_session['quantity'], 'price': price_decimal, 'total_price': item_total_price}}
                main_response_html = render_to_string('cart/partials/cart_item.html', item_context_for_template, request=request)
            except Product.DoesNotExist:
                 logger.error(f"Product with id {product_id} not found in update_cart.")
                 main_response_html = f"<!-- Product {product_id} not found -->"
            except Exception as e:
                logger.error(f"Error rendering cart_item.html in update_cart for {product_id}: {e}", exc_info=True)
                main_response_html = f"<!-- Error rendering item {product_id} -->"
    return HttpResponse(main_response_html + oob_counter_response + oob_summary_response)


@login_required(login_url='login')
def cart_view(request):
    cart = Cart(request)
    context = {'cart': cart}
    return render(request, 'cart/cart.html', context)

@login_required(login_url='login')
@require_GET
def checkout_page_view(request):
    cart = Cart(request)
    if not cart:
        messages.info(request, "Ваш кошик порожній.")
        return redirect('cart:cart')
    initial_form_data = {}
    if request.user.is_authenticated:
        initial_form_data = {'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email}
    context = {'cart': cart, 'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY or "", 'form_data': initial_form_data}
    return render(request, 'cart/checkout.html', context)


@login_required(login_url='login')
@require_POST 
def process_checkout(request):
   logger.info(f"--- process_checkout CALLED (User: {request.user.username}) ---")
   logger.info(f"Request Method: {request.method}")
   logger.info(f"Content-Type: {request.content_type}")

   data_from_client = {} 

   if request.content_type == 'application/json':
       try:

           request_body_decoded = request.body.decode('utf-8')
           if not request_body_decoded:
               logger.warning("Порожнє тіло JSON запиту отримано.")
               return JsonResponse({'error': "Тіло запиту порожнє."}, status=400)
           data_from_client = json.loads(request_body_decoded)
           logger.info(f"Parsed JSON data from request.body: {data_from_client}")
       except json.JSONDecodeError as e:
           logger.error(f"Помилка розбору JSON з request.body: {e}. Тіло: {request.body[:500]}")
           return JsonResponse({'error': "Некоректний формат JSON у запиті."}, status=400)
       except UnicodeDecodeError as e:
           logger.error(f"Помилка декодування UTF-8 з request.body: {e}. Тіло: {request.body[:500]}")
           return JsonResponse({'error': "Помилка кодування даних у запиті."}, status=400)
   else:

       logger.warning(f"Отримано непідтримуваний Content-Type: {request.content_type}. Очікується application/json.")
       return JsonResponse({'error': "Непідтримуваний Content-Type. Сервер очікує application/json."}, status=415)

   cart = Cart(request)
   if not cart: 
       error_msg = "Ваш кошик порожній. Неможливо оформити замовлення."
       logger.warning(f"Спроба оформити замовлення з порожнім кошиком користувачем {request.user.username}")
       return JsonResponse({'error': error_msg, 'redirect_url': reverse('cart:cart')}, status=400)


   form_data = {
       'first_name': str(data_from_client.get('first_name', '')).strip(),
       'last_name': str(data_from_client.get('last_name', '')).strip(),
       'email': str(data_from_client.get('email', '')).strip(),
       'phone': str(data_from_client.get('phone', '')).strip(),
       'address': str(data_from_client.get('address', '')).strip(),
       'city': str(data_from_client.get('city', '')).strip(),
       'zipcode': str(data_from_client.get('zipcode', '')).strip(),
       'payment_method': data_from_client.get('payment_method')
   }
   logger.info(f"Дані форми для валідації: {form_data}")


   validation_errors_dict = {} 
   if not form_data['first_name']: validation_errors_dict['first_name'] = "Ім'я є обов'язковим."
   if not form_data['last_name']: validation_errors_dict['last_name'] = "Прізвище є обов'язковим."
   if not form_data['email']: 
       validation_errors_dict['email'] = "Email є обов'язковим."
   elif "@" not in form_data['email'] or "." not in form_data['email'].split('@')[-1]:
       validation_errors_dict['email'] = "Введіть коректний email."
   if not form_data['phone']: 
       validation_errors_dict['phone'] = "Телефон є обов'язковим."
   elif not form_data['phone'].replace('+','').replace('(','').replace(')','').replace('-','').replace(' ','').isdigit() or \
         not (10 <= len(form_data['phone'].replace('+','').replace('(','').replace(')','').replace('-','').replace(' ','')) <= 15):
       validation_errors_dict['phone'] = "Введіть коректний номер телефону (наприклад, +380XXXXXXXXX або 0XXXXXXXXX, 10-12 цифр без плюса)."
   if not form_data['address']: validation_errors_dict['address'] = "Адреса є обов'язковою."
   if not form_data['city']: validation_errors_dict['city'] = "Місто є обов'язковим."
   
   payment_method_value = form_data.get('payment_method')
   if not payment_method_value or payment_method_value not in [choice[0] for choice in Order.PaymentChoices.choices]:
        validation_errors_dict['payment_method'] = "Будь ласка, оберіть дійсний спосіб оплати."
        logger.warning(f"Помилка валідації для payment_method. Отримано: '{payment_method_value}', Очікувалось: {[choice[0] for choice in Order.PaymentChoices.choices]}")

   if validation_errors_dict:
       logger.warning(f"Серверна валідація не пройдена для користувача {request.user.username}. Помилки: {validation_errors_dict}")
       return JsonResponse({'error': "Будь ласка, виправте помилки у формі.", 'errors_detail': validation_errors_dict}, status=400)


   total_price_decimal = cart.get_total_cost()
   order = None 

   try:
       with transaction.atomic(): 
           order = Order.objects.create(
               user=request.user, 
               first_name=form_data['first_name'],
               last_name=form_data['last_name'],
               email=form_data['email'],
               phone=form_data['phone'],
               address=form_data['address'],
               city=form_data['city'],
               zipcode=form_data['zipcode'],
               total_price=total_price_decimal,
               payment_method=form_data['payment_method'],
               status=Order.OrderStatus.PENDING 
           )
           
           order_items_to_create = []
           for item_from_cart_dict in cart:
               product_object = item_from_cart_dict.get('product')
               if not product_object:
                   logger.error(f"Не знайдено об'єкт Product в item_from_cart_dict для замовлення {order.id}")
                   raise ValueError("Помилка даних кошика: відсутній продукт.")

               order_items_to_create.append(
                   OrderItem(
                       order=order, 
                       product=product_object,
                       price_at_purchase=item_from_cart_dict['price'],
                       quantity=item_from_cart_dict['quantity']
                   )
               )
           if order_items_to_create: 
               OrderItem.objects.bulk_create(order_items_to_create)
           
           logger.info(f"Замовлення {order.id} та {len(order_items_to_create)} позицій OrderItems створено. Статус PENDING для користувача {request.user.username}.")

   except DatabaseError as e:
       logger.error(f"ПОМИЛКА БД при створенні замовлення або OrderItems для {request.user.username}: {e}", exc_info=True)
       return JsonResponse({'error': "Помилка бази даних при створенні замовлення. Спробуйте пізніше."}, status=500)
   except ValueError as e:
        logger.error(f"Помилка даних при створенні OrderItems для {request.user.username}: {e}", exc_info=True)
        return JsonResponse({'error': f"Помилка даних кошика: {e}"}, status=400)
   except Exception as e: 
       logger.error(f"Неочікувана ПОМИЛКА при створенні замовлення або OrderItems для {request.user.username}: {e}", exc_info=True)
       return JsonResponse({'error': "Непередбачена помилка сервера при створенні замовлення. Спробуйте пізніше."}, status=500)

   if not order: 
        logger.error(f"Об'єкт замовлення не було створено для користувача {request.user.username} після блоку транзакції (малоймовірно).")
        return JsonResponse({'error': "Не вдалося створити об'єкт замовлення."}, status=500)


   if order.payment_method == Order.PaymentChoices.CARD:
       if not stripe.api_key or not getattr(settings, 'STRIPE_PUBLISHABLE_KEY', None):
           error_msg_stripe_keys = "Помилка конфігурації платіжної системи. Зверніться до адміністрації."
           logger.error(error_msg_stripe_keys + f" stripe.api_key is set: {bool(stripe.api_key)}, STRIPE_PUBLISHABLE_KEY is set: {bool(getattr(settings, 'STRIPE_PUBLISHABLE_KEY', None))}")
           if order.status != Order.OrderStatus.PAYMENT_FAILED:
                order.status = Order.OrderStatus.PAYMENT_FAILED; order.save(update_fields=['status'])
           return JsonResponse({'error': error_msg_stripe_keys}, status=500)
       
       try:
           protocol = 'https' if request.is_secure() else 'http'
           host = request.get_host()
           success_url = f"{protocol}://{host}{reverse('cart:success')}?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}" 
           cancel_url = f"{protocol}://{host}{reverse('cart:payment_cancel')}?order_id={order.id}"
           
           amount_in_cents = int(total_price_decimal * 100)
           
           MIN_AMOUNT_CENTS_STRIPE_UAH = getattr(settings, 'MIN_STRIPE_CHARGE_UAH_CENTS', 2000) 

           if amount_in_cents < MIN_AMOUNT_CENTS_STRIPE_UAH:
               min_sum_uah = Decimal(MIN_AMOUNT_CENTS_STRIPE_UAH / 100)
               msg_min_sum = f"Мінімальна сума для онлайн оплати становить {min_sum_uah:.2f} грн. Ваша сума: {total_price_decimal:.2f} грн."
               logger.warning(f"Спроба оплати нижче мінімального ліміту Stripe для замовлення {order.id}: {total_price_decimal:.2f} грн")
               if order.status != Order.OrderStatus.PAYMENT_FAILED:
                    order.status = Order.OrderStatus.PAYMENT_FAILED; order.save(update_fields=['status'])
               return JsonResponse({'error': msg_min_sum, 'errors_detail': {'total_price': msg_min_sum}}, status=400)

           checkout_session_params = {
               'payment_method_types': ['card'],
               'line_items': [{
                   'price_data': { 
                       'currency': 'uah', 
                       'product_data': {'name': f'Замовлення #{order.id} в магазині ElectroHub'}, 
                       'unit_amount': amount_in_cents, 
                   }, 
                   'quantity': 1,
               }],
               'mode': 'payment', 
               'success_url': success_url, 
               'cancel_url': cancel_url,
               'client_reference_id': str(order.id), 
               'customer_email': order.email,
               'locale': 'en'
           }
           
           session = stripe.checkout.Session.create(**checkout_session_params)
           
           order.stripe_checkout_session_id = session.id 
           order.save(update_fields=['stripe_checkout_session_id'])
           logger.info(f"Створено Stripe Checkout Session ID: {session.id} для замовлення {order.id} користувача {request.user.username}")

           return JsonResponse({'session_id': session.id, 'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY})

       except stripe.error.StripeError as e:
           logger.error(f"Stripe помилка при створенні Checkout Session для замовлення {order.id} ({request.user.username}): {e}", exc_info=True)
           user_friendly_stripe_error = getattr(e, 'user_message', None) or str(e) 
           if order.status != Order.OrderStatus.PAYMENT_FAILED:
                order.status = Order.OrderStatus.PAYMENT_FAILED; order.save(update_fields=['status'])
           return JsonResponse({'error': f"Помилка платіжної системи: {user_friendly_stripe_error}"}, status=400)
       except Exception as e: 
           logger.error(f"Неочікувана помилка при створенні Stripe Checkout Session для замовлення {order.id} ({request.user.username}): {e}", exc_info=True)
           if order.status != Order.OrderStatus.PAYMENT_FAILED:
                order.status = Order.OrderStatus.PAYMENT_FAILED; order.save(update_fields=['status'])
           return JsonResponse({'error': "Сталася непередбачена помилка при підготовці онлайн оплати. Спробуйте пізніше."}, status=500)

   elif order.payment_method == Order.PaymentChoices.CASH:
       order.status = Order.OrderStatus.PROCESSING 
       order.save(update_fields=['status'])
       cart.clear() 
       logger.info(f"Замовлення {order.id} (готівка) для {request.user.username} переведено в статус PROCESSING. Кошик очищено.")

       
       success_redirect_url = reverse('cart:success') + f"?order_id={order.id}&payment_method=cash&order_processed=true"
       return JsonResponse({'success': True, 'redirect_url': success_redirect_url})
   else: 
       logger.error(f"Невідомий спосіб оплати '{order.payment_method}' для замовлення {order.id} ({request.user.username})")
       return JsonResponse({'error': "Обрано невідомий спосіб оплати."}, status=400)



def success(request):
   order = None
   order_id = request.GET.get("order_id")
   stripe_session_id = request.GET.get("session_id") 
   payment_method = request.GET.get("payment_method")
   order_processed_cash = request.GET.get("order_processed") == "true" and payment_method == "cash"
   user_msg = None 

   if order_id:
       if not request.user.is_authenticated:
           messages.error(request, "Для перегляду деталей замовлення необхідно увійти.")
           return redirect('login') 
       try:
           order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id, user=request.user)
           if order.payment_method == Order.PaymentChoices.CARD and stripe_session_id and order.stripe_checkout_session_id == stripe_session_id:
               if order.status == Order.OrderStatus.PENDING: 
                   logger.info(f"Перевірка статусу Stripe сесії {stripe_session_id} для замовлення {order.id} (success URL).")
                   try:
                       if not stripe.api_key: raise Exception("Stripe API key not set for session retrieval")
                       checkout_session = stripe.checkout.Session.retrieve(stripe_session_id)
                       if checkout_session.payment_status == 'paid':
                           with transaction.atomic():
                               order_upd = Order.objects.select_for_update().get(pk=order.id)
                               if order_upd.status == Order.OrderStatus.PENDING:
                                   order_upd.status = Order.OrderStatus.PAID 
                                   order_upd.stripe_payment_intent_id = checkout_session.payment_intent
                                   order_upd.save(update_fields=['status', 'stripe_payment_intent_id'])
                                   Cart(request).clear()
                                   logger.info(f"Замовлення {order_upd.id} оновлено до PAID (success URL). Кошик очищено.")
                                   order = order_upd 
                                   user_msg = "Ваше замовлення успішно оплачено!"
                       else: 
                           logger.warning(f"Stripe сесія {stripe_session_id} для замовлення {order.id} НЕ 'paid' (статус: {checkout_session.payment_status}).")
                           user_msg = "Оплата ще не підтверджена. Зв'яжіться з підтримкою."
                           if checkout_session.status in ['expired', 'open'] and order.status == Order.OrderStatus.PENDING: pass
                           elif order.status == Order.OrderStatus.PENDING : order.status = Order.OrderStatus.PAYMENT_FAILED; order.save(update_fields=['status'])
                   except stripe.error.StripeError as e: logger.error(f"Stripe помилка сесії {stripe_session_id} для {order.id}: {e}"); user_msg = "Не вдалося перевірити статус онлайн платежу."
                   except Exception as e: logger.error(f"Загальна помилка Stripe сесії для {order.id}: {e}", exc_info=True); user_msg = "Помилка перевірки статусу оплати."
               elif order.status == Order.OrderStatus.PAID or order.status == Order.OrderStatus.PROCESSING : user_msg = "Ваше замовлення успішно оформлено!" + (" (оплачено)" if order.status == Order.OrderStatus.PAID else "")
               else: user_msg = f"Статус замовлення: {order.get_status_display()}."; order = None
           elif order.payment_method == Order.PaymentChoices.CASH:
               if order_processed_cash: user_msg = "Замовлення прийнято! Очікуйте дзвінка."
               elif order.status in [Order.OrderStatus.PROCESSING, Order.OrderStatus.CONFIRMED_BY_MANAGER, Order.OrderStatus.SHIPPED, Order.OrderStatus.COMPLETED]: user_msg = f"Замовлення #{order.id} - {order.get_status_display()}."
               else: user_msg = f"Статус замовлення: {order.get_status_display()}."; order = None
           else: logger.error(f"Замовлення {order.id} має невідомий метод оплати: {order.payment_method}"); user_msg = "Помилка замовлення."; order = None
       except Order.DoesNotExist: messages.error(request, "Замовлення не знайдено."); user_msg = "Замовлення не знайдено."; order = None
       except Exception as e: logger.error(f"Загальна помилка success page для order_id {order_id}: {e}", exc_info=True); messages.error(request, "Помилка відображення."); user_msg = "Помилка."; order = None
   elif order_processed_cash: user_msg = "Замовлення прийнято! Очікуйте дзвінка."
   
   if user_msg:
       is_success_status = order and (order.status == Order.OrderStatus.PAID or (order.payment_method == Order.PaymentChoices.CASH and order.status == Order.OrderStatus.PROCESSING))
       if is_success_status or order_processed_cash: messages.success(request, user_msg)
       elif order or not list(messages.get_messages(request)): messages.info(request, user_msg or "Дякуємо!")
       
   context = {'order': order} 
   return render(request, "cart/success.html", context)

def payment_cancel(request):
   order_id = request.GET.get("order_id")
   if order_id and request.user.is_authenticated:
       try:
           order = Order.objects.get(id=order_id, user=request.user)
           if order.status == Order.OrderStatus.PENDING:
               order.status = Order.OrderStatus.CANCELLED 
               order.save(update_fields=['status'])
               logger.info(f"Замовлення {order.id} статус CANCELLED після скасування Stripe.")
               messages.warning(request, f"Оплату для замовлення #{order.id} було скасовано.")

       except Order.DoesNotExist: messages.error(request, "Замовлення, для якого скасовано оплату, не знайдено.")
       except Exception as e: logger.error(f"Помилка скасування для замовлення {order_id}: {e}", exc_info=True); messages.error(request, "Помилка обробки скасування.")
   else: messages.warning(request, "Процес оплати було скасовано.")
   return render(request, 'cart/cancel.html')

@require_GET
def hx_menu_cart(request):
    cart = Cart(request)
    return render(request, 'cart/cart_menu.html', {'cart': cart})

@require_GET
def hx_cart_summary_total(request):
    cart = Cart(request)
    return render(request, 'cart/partials/cart_summary_total.html', {'cart': cart})

@login_required(login_url='login')
def order_detail_view(request, order_id):
    """
    Відображає детальну інформацію про конкретне замовлення користувача.
    """
    try:


        order = get_object_or_404(
            Order.objects.select_related('user').prefetch_related('items__product'), 
            id=order_id, 
            user=request.user
        )
    except Http404:
        messages.error(request, "Замовлення не знайдено або у вас немає до нього доступу.")
        return redirect('myaccount')

    context = {
        'order': order,
        'OrderStatus': Order.OrderStatus,
    }
    return render(request, 'cart/order_detail.html', context)
