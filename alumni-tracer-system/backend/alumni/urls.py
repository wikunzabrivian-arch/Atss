from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'alumni', views.AlumniProfileViewSet, basename='alumni')
router.register(r'events', views.EventViewSet, basename='events')
router.register(r'notices', views.NoticeViewSet, basename='notices')

urlpatterns = [
   
    path('invitations/', views.invitation_list, name='invitation-list'),
    path('invitations/send/', views.invitation_list, name='invitation-send'),
    path('invitations/<str:token>/', views.invitation_detail, name='invitation-detail'),
    path('invitations/<str:token>/accept/', views.accept_invitation, name='accept-invitation'),
    path('invitations/<uuid:invitation_id>/resend/', views.send_invitation_email, name='resend-invitation'),
    
    path('alumni/my_profile/', views.AlumniProfileViewSet.as_view({'get': 'my_profile'}), name='alumni-my-profile'),
    path('alumni/', views.AlumniProfileViewSet.as_view({'get': 'list', 'post': 'create'}), name='alumni-list'),
    path('alumni/<int:pk>/', views.AlumniProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='alumni-detail'),
    
    # Add this for user management
    path('users/<uuid:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<uuid:user_id>/alumni-profile/', views.UserAlumniProfileView.as_view(), name='user-alumni-profile'),
    path('', include(router.urls)),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
]
