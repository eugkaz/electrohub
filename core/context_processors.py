def favorites_context(request):
    count = 0
    if request.user.is_authenticated:
        product_count = request.user.favorite_products.count()
        listing_count = 0
        profile = getattr(request.user, 'profile', None)
        if profile:
            listing_count = profile.favorite_listings.count()
        count = product_count + listing_count

    return {'user_favorites_total_count': count}