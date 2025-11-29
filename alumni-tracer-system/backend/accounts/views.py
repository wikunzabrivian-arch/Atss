from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, get_user_model
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .serializers import (
    EmailSerializer, 
    ResetPasswordSerializer, 
    ChangePasswordSerializer
)

from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    AdminUserSerializer
)

CustomUser = get_user_model()   # FIXED
User = get_user_model()

password_reset_token_generator = PasswordResetTokenGenerator()

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    if user:
        # Send verification email
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = f"{request.build_absolute_uri('/')}verify-email/{uid}/{token}/"

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_user_profile(request):
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])  # Accept both PUT and PATCH
def update_user_profile(request):
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()    # FIXED
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
import uuid
from rest_framework import generics

from .serializers import (
    EmailSerializer, 
    ResetPasswordSerializer, 
    ChangePasswordSerializer
)

User = get_user_model()

# Create a single token generator instance for consistency
password_reset_token_generator = PasswordResetTokenGenerator()
class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    serializer = EmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate password reset token using single instance
        token = password_reset_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create reset link
        reset_url = f"http://localhost:3000/reset-password/{uid}/{token}"
        
        # Send email
        subject = 'Password Reset Request - Alumni Tracker'
        message = f'''
        Hello {user.get_full_name() or user.username},
        
        You requested a password reset for your Alumni Tracker account.
        
        Please click the link below to reset your password:
        {reset_url}
        
        This link will expire in 24 hours.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        Alumni Tracker Team
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response(
            {'message': 'Password reset email sent successfully'},
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Send confirmation email
        subject = 'Password Reset Successful - Alumni Tracker'
        message = f'''
        Hello {user.get_full_name() or user.username},
        
        Your password has been successfully reset.
        
        If you did not perform this action, please contact support immediately.
        
        Best regards,
        Alumni Tracker Team
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response(
            {'message': 'Password reset successfully'},
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_reset_token(request, uidb64, token):
    try:
        # Decode the user ID
        uid_str = force_str(urlsafe_base64_decode(uidb64))
        user_uuid = uuid.UUID(uid_str)
        user = User.objects.get(pk=user_uuid)
        
        # Verify the token using the single instance
        is_valid = password_reset_token_generator.check_token(user, token)
        
        if not is_valid:
            return Response(
                {'error': 'Reset link is invalid or has expired'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {'message': 'Token is valid', 'email': user.email},
            status=status.HTTP_200_OK
        )
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {'error': 'Invalid reset link'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Invalid reset link'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_email(request):
    email = request.data.get('email')
    
    try:
        user = CustomUser.objects.get(email=email)
        if user.is_verified:
            return Response({'message': 'Email is already verified'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate verification token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create verification URL
        verification_url = f"{request.build_absolute_uri('/')}verify-email/{uid}/{token}/"
        
        # Send email
        subject = 'Verify Your ACCES Alumni Account'
        html_message = render_to_string('emails/verification_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            'noreply@acces-alumni.com',
            [user.email],
            html_message=html_message,
        )
        
        return Response({'message': 'Verification email sent'})
        
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            user.is_verified = True
            user.save()
            return Response({'message': 'Email verified successfully'})
        else:
            return Response({'error': 'Invalid verification link'}, status=status.HTTP_400_BAD_REQUEST)
            
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return Response({'error': 'Invalid verification link'}, status=status.HTTP_400_BAD_REQUEST)
