# Create a signal to ensure UserProfile is created for each user
from datetime import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from django.conf import settings

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists and has valid last_seen
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if created and not profile.last_seen:
        profile.last_seen = timezone.now()
        profile.save()