
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers


from .models import (
    AlumniProfile,
    Event,
    Notice,Invitation

)
from accounts.serializers import UserProfileSerializer  # This one is fine

User = get_user_model()


# -----------------------------
#  SIMPLE USER SERIALIZER
# -----------------------------
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email')


# -----------------------------
#  ALUMNI PROFILE LIST
# -----------------------------
class AlumniProfileListSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = AlumniProfile
        fields = (
            'id',
            'user',
            'student_id',
            'year_graduated',
            'program',
            'current_employer',
            'job_title',
            'location',
            'bio',  # Add missing fields
            'linkedin_url',
            'twitter_url',
            'gender',
        )

# serializers.py
class AlumniProfileUpdateSerializer(serializers.ModelSerializer):
    # Add user fields that admins should be able to update
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False, allow_blank=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    is_verified = serializers.BooleanField(source='user.is_verified', required=False)
    user_gender = serializers.CharField(source='user.gender', required=False, allow_blank=True)

    class Meta:
        model = AlumniProfile
        fields = (
            'current_employer',
            'job_title',
            'location',
            'bio',
            'linkedin_url',
            'twitter_url',
            'gender',
            # User fields
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'is_active',
            'is_verified',
            'user_gender',
        )

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update alumni profile
        instance = super().update(instance, validated_data)
        
        # Update user data if provided
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                if value is not None:  # Only update if value is provided
                    setattr(user, attr, value)
            user.save()
        
        return instance
    
class EventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'location', 
            'image', 'image_url', 'created_by', 'created_by_name',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle image separately to avoid required field issues
        image = validated_data.pop('image', None)
        if image is not None:
            instance.image = image
        return super().update(instance, validated_data)
# -----------------------------
#  NOTICES
# -----------------------------
class NoticeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )

    class Meta:
        model = Notice
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at')

class InvitationSerializer(serializers.ModelSerializer):
    inviter_name = serializers.CharField(source='inviter.get_full_name', read_only=True)
    
    class Meta:
        model = Invitation
        fields = [
            'id', 'email', 'name', 'message', 'token', 
            'status', 'created_at', 'expires_at', 'inviter_name'
        ]
        read_only_fields = ['id', 'token', 'status', 'created_at', 'expires_at', 'inviter_name']

class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['email', 'name', 'message']
    
    def validate_email(self, value):
        value = value.lower().strip()  # Normalize email
        
        # Check if user with this email already exists
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        # Check if pending invitation already exists for this email
        if Invitation.objects.filter(
            email=value, 
            status='pending',
            expires_at__gt=timezone.now()  # Use Django's timezone.now()
        ).exists():
            raise serializers.ValidationError("A pending invitation already exists for this email.")
        
        return value
    
    def create(self, validated_data):
        try:
            inviter = self.context['request'].user
            return Invitation.objects.create(inviter=inviter, **validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create invitation: {str(e)}")

class InvitationDetailSerializer(serializers.ModelSerializer):
    inviter_name = serializers.CharField(source='inviter.get_full_name')
    inviter_email = serializers.CharField(source='inviter.email')
    
    class Meta:
        model = Invitation
        fields = [
            'id', 'email', 'name', 'message', 'token', 'status',
            'created_at', 'expires_at', 'inviter_name', 'inviter_email'
        ]
        
