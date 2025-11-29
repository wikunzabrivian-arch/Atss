import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('alumni', 'Alumni'),
        ('admin', 'Administrator'),
    )
    id=models.UUIDField(primary_key=True,default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='alumni')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active=models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        blank=True, 
        null=True
    )

    def get_full_name(self):
        """Returns the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()
    
    def __str__(self):
        return f"{self.username} - {self.user_type}"