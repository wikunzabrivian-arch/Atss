from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    UserViewSet, 
    register_user, 
    login_user, 
    get_user_profile, 
    update_user_profile,
    request_password_reset,
    reset_password_confirm,
    change_password,
    verify_reset_token,
    UserDetailView,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('register/', register_user),
    path('login/', login_user),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', get_user_profile),
    path('profile/update/', update_user_profile),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),path('api/auth/', include('allauth.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Password reset endpoints
    path('password/reset/', request_password_reset, name='password_reset'),
    path('password/reset/confirm/', reset_password_confirm, name='password_reset_confirm'),
    path('password/change/', change_password, name='change_password'),
    path('password/reset/verify/<str:uidb64>/<str:token>/', verify_reset_token, name='verify_reset_token'),
    path('verify-email/send/', views.send_verification_email, name='send-verification-email'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify-email'),
    
    path('', include(router.urls)),
]
