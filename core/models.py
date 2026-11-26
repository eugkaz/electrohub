from django.db import models
from django.contrib.auth.models import User
from product.models import Product
from marketplace.models import Listing

class Profile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default-avatar.png', null=True, blank=True)

    favorite_products = models.ManyToManyField(Product, related_name='favorited_by_profiles', blank=True)

    favorite_listings = models.ManyToManyField(Listing, related_name='favorited_by_profiles', blank=True)

    def __str__(self):
        return f'Profile for {self.user.username}'



from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:

        Profile.objects.create(user=instance)

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email