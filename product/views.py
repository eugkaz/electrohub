from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.db.models import Avg
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Product, ProductFeature, ProductImage, Review
from django.contrib.auth.models import User



def product(request, slug):
   try:
       product = get_object_or_404(
           Product.objects.select_related('category', 'brand', 'part_type')
                          .prefetch_related('features', 'images', 'reviews', 'reviews__user', 'compatible_models'),
           slug=slug, is_active=True
       )
   except Http404:
        messages.error(request, "Товар не знайдено або він більше не доступний.")
        return redirect('core:shop')

   similar_products = Product.objects.filter(category=product.category, is_active=True, in_stock=True).exclude(id=product.id).select_related('category')[:4]

   is_current_product_favorite = False
   favorite_status_for_similar = {}
   if request.user.is_authenticated:
       user_favorites_ids = set(request.user.favorite_products.values_list('id', flat=True))
       is_current_product_favorite = product.id in user_favorites_ids
       favorite_status_for_similar = {p.id: p.id in user_favorites_ids for p in similar_products}


   product_reviews = product.reviews.order_by('-created_at')

   login_url = reverse('login')

   context = {
       'product': product,
       'features': product.features.all(),
       'images': product.images.all(),
       'reviews': product_reviews,
       'similar_products': similar_products,
       'average_rating': product.get_average_rating(),
       'is_favorite': is_current_product_favorite,
       'favorite_status': favorite_status_for_similar,
       'source': 'product_detail',
       'login_url': login_url,
   }
   return render(request, 'product/product.html', context)



@require_POST
@login_required
def create_review(request, product_id):
   product = get_object_or_404(Product, id=product_id, is_active=True)
   user = request.user

   rating_str = request.POST.get('rating')
   text = request.POST.get('text', '').strip()

   if not text:
       messages.error(request, 'Будь ласка, напишіть текст відгуку.')
       return redirect('product:product_detail', slug=product.slug)

   try:
       rating = int(rating_str)
       if not (1 <= rating <= 5): raise ValueError("Рейтинг має бути від 1 до 5")
   except (ValueError, TypeError):
       messages.error(request, 'Будь ласка, оберіть коректну оцінку (1-5).')
       return redirect('product:product_detail', slug=product.slug)


   review, created = Review.objects.update_or_create(
       product=product,
       user=user,
       defaults={'rating': rating, 'text': text}
   )

   if created: messages.success(request, 'Дякуємо! Ваш відгук опубліковано.')
   else: messages.success(request, 'Ваш відгук оновлено.')

   return redirect(f"{reverse('product:product_detail', kwargs={'slug': product.slug})}#reviews-section")