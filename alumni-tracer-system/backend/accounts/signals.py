from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .models import CustomUser

@receiver(post_delete, sender=CustomUser)
def delete_user_tokens_on_delete(sender, instance, **kwargs):
    """
    Delete JWT tokens when user is deleted
    """
    try:
        # Import here to avoid circular imports
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        
        # Delete outstanding tokens for the user
        OutstandingToken.objects.filter(user=instance).delete()
    except Exception as e:
        # Log the error but don't crash the deletion process
        print(f"Error deleting tokens for user {instance.id}: {e}")