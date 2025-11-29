# middleware.py
from django.utils import timezone
from django.db import OperationalError

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            try:
                # Try to update user profile, but don't crash if table doesn't exist
                from .models import UserProfile
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                profile.last_seen = timezone.now()
                profile.save()
            except OperationalError:
                # Table doesn't exist yet, just ignore for now
                pass
            except Exception as e:
                # Any other error, log it but don't crash
                print(f"Error in UserActivityMiddleware: {e}")
            
        return response