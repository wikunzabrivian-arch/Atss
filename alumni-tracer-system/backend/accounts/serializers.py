from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import CustomUser
from alumni.models import AlumniProfile
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed
from django.core.mail import send_mail
from rest_framework import generics, permissions

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    
    # Alumni profile fields
    student_id = serializers.CharField(write_only=True, required=False)
    year_graduated = serializers.IntegerField(write_only=True, required=False)
    program = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password', 'password2', 'first_name', 'last_name', 
                 'phone_number', 'student_id', 'year_graduated', 'program')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        # Remove alumni-specific fields if they exist
        student_id = validated_data.pop('student_id', None)
        year_graduated = validated_data.pop('year_graduated', None)
        program = validated_data.pop('program', None)
        validated_data.pop('password2')
        
        # Create user
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            user_type='alumni'  # Default to alumni for registration
        )
        
        # Create alumni profile if alumni-specific data provided
        if student_id and year_graduated and program:
            AlumniProfile.objects.create(
                user=user,
                student_id=student_id,
                year_graduated=year_graduated,
                program=program
            )
        
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError({
                "detail": "Email and password are required."
            })

        # Check if user exists
        try:
            User.objects.get(email=email)
        except User.DoesNotExist as e:
            raise serializers.ValidationError(
                {"email": ["No user found with this email address"]}
            ) from e

        # Authenticate using custom backend
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password
        )

        if user is None:
            raise serializers.ValidationError({
                "password": ["Invalid password"]
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "detail":["Account is disabled"]
            })

        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'user_type', 'profile_picture', 'date_joined')
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

class AlumniProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = AlumniProfile
        fields = '__all__'

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'phone_number', 'user_type', 'is_active')
        read_only_fields = ('id', 'email', 'username')
        
        
class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email address.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            raise AuthenticationFailed('Invalid reset link', 401) from e

        if not PasswordResetTokenGenerator().check_token(user, data['token']):
            raise AuthenticationFailed('Reset link is invalid or has expired', 401)

        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.save()
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value