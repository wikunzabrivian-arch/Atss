from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import   Count
from rest_framework.permissions import IsAdminUser
from rest_framework import permissions
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from accounts.models import CustomUser
from accounts.serializers import UserProfileSerializer



from .models import (
    AlumniProfile, Event, Notice,Invitation
)

from .serializers import (
    AlumniProfileListSerializer, AlumniProfileUpdateSerializer, EventSerializer,
    NoticeSerializer,InvitationSerializer, 
    InvitationCreateSerializer,
    InvitationDetailSerializer
)

User = get_user_model()
class AlumniPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow alumni and admin users
        return request.user.is_authenticated and request.user.user_type in [
            'alumni',
            'admin',
        ]

class AlumniProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AlumniProfileListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return AlumniProfile.objects.filter(user=self.request.user)
        return AlumniProfile.objects.all().select_related("user")

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AlumniProfileUpdateSerializer
        return self.serializer_class

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        try:
            profile = AlumniProfile.objects.get(user=request.user)
            return Response(self.get_serializer(profile).data)
        except AlumniProfile.DoesNotExist:
            return Response({"detail": "Alumni profile not found"}, status=404)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"detail": "You can only update your own profile."}, status=403)
        return super().update(request, *args, **kwargs)
    
    def get_permissions(self):
        if self.action in ['create', 'destroy', 'verify']:
            return [IsAdminUser()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.action in ['update', 'partial_update', 'destroy', 'my_profile']:
            return AlumniProfile.objects.filter(user=self.request.user)
        return AlumniProfile.objects.all().select_related("user")


    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        try:
            profile = AlumniProfile.objects.get(pk=pk)
            user = profile.user
            user.is_verified = not user.is_verified
            user.save()

            return Response({
                "message": "Verification updated",
                "is_verified": user.is_verified
            })
        except AlumniProfile.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

class UserAlumniProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AlumniProfileUpdateSerializer
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(CustomUser, id=user_id)
        return get_object_or_404(AlumniProfile, user=user)


class IsAdminOrReadOnly(permissions.BasePermission):
  
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.user_type == 'admin'

class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        return Event.objects.all().select_related('created_by').order_by('-date')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notice.objects.filter(is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

@api_view(["GET"])
def dashboard_stats(request):
    if request.user.user_type != "admin":
        return Response({"error": "Permission denied"}, status=403)

    return Response({
        "total_alumni": AlumniProfile.objects.count(),
        "total_events": Event.objects.count(),
        "active_notices": Notice.objects.filter(is_active=True).count(),
        "alumni_by_program": list(
            AlumniProfile.objects.values("program").annotate(count=Count("id"))
        ),
        "alumni_by_year": list(
            AlumniProfile.objects.values("year_graduated")
            .annotate(count=Count("id"))
            .order_by("year_graduated")
        ),
    })


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def invitation_list(request):
    if request.method == 'GET':
        invitations = Invitation.objects.filter(inviter=request.user)
        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = InvitationCreateSerializer(data=request.data)
        if serializer.is_valid():
            invitation = serializer.save(inviter=request.user)
            
            # Return the created invitation
            response_serializer = InvitationSerializer(invitation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def invitation_detail(request, token):
    try:
        invitation = Invitation.objects.get(token=token)
        
        # Check if invitation is expired
        if invitation.is_expired() and invitation.status == 'pending':
            invitation.status = 'expired'
            invitation.save()
        
        serializer = InvitationDetailSerializer(invitation)
        return Response(serializer.data)
    
    except Invitation.DoesNotExist:
        return Response(
            {'error': 'Invitation not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def accept_invitation(request, token):
    try:
        invitation = Invitation.objects.get(token=token)
        
        if invitation.status != 'pending':
            return Response(
                {'error': 'Invitation has already been processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if invitation.is_expired():
            invitation.status = 'expired'
            invitation.save()
            return Response(
                {'error': 'Invitation has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation.mark_accepted()
        serializer = InvitationSerializer(invitation)
        return Response(serializer.data)
    
    except Invitation.DoesNotExist:
        return Response(
            {'error': 'Invitation not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_invitation_email(request, invitation_id):
    try:
        invitation = Invitation.objects.get(id=invitation_id, inviter=request.user)
        
        if invitation.status != 'pending':
            return Response(
                {'error': 'Can only send emails for pending invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': 'Invitation email sent successfully'})
    
    except Invitation.DoesNotExist:
        return Response(
            {'error': 'Invitation not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )