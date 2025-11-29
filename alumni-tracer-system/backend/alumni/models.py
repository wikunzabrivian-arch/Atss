from django.db import models
from django.conf import settings
from django.utils import timezone



class AlumniProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alumni_profile'
    )
    student_id = models.CharField(max_length=20, unique=True)
    year_graduated = models.IntegerField()
    program = models.CharField(max_length=200)
    current_employer = models.CharField(max_length=200, blank=True, null=True)
    job_title = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
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

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.program} ({self.year_graduated})"

# models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)  # Use timezone.now as default
    
    def __str__(self):
        return f"{self.user.get_full_name()} Profile"

    def save(self, *args, **kwargs):
        # Always update last_seen when saving
        if not self.last_seen:
            self.last_seen = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'user_profile'




from django.db import models
from django.conf import settings
import os
import uuid

# models.py - Update Event model
def event_image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('event_images', filename)

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to=event_image_upload_path,
        blank=True,
        null=True,
        help_text="Event banner image"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return None

    @property
    def created_by_name(self):
        return self.created_by.get_full_name() or self.created_by.email

    @property
    def registrations_count(self):
        return self.registrations.count()

class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notices_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Invitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inviter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_invitations'
    )
    email = models.EmailField()
    name = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    token = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'invitations'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def mark_accepted(self):
        self.status = 'accepted'
        self.save()
    
    def get_invite_link(self, request):
        base_url = f"{request.scheme}://{request.get_host()}"
        return f"{base_url}/auth/register?invite={self.token}"


