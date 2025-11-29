from datetime import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Conversation, DeletedConversation, Message
from django.db.models import Prefetch
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """Get all conversations for the current user (excluding deleted ones)"""
    try:
        print(f"🔐 User: {request.user.username}")
        
        # Get deleted conversation IDs for this user
        deleted_conversation_ids = DeletedConversation.objects.filter(
            user=request.user
        ).values_list('conversation_id', flat=True)
        
        print(f"🗑️ Excluding {len(deleted_conversation_ids)} deleted conversations")
        
        conversations = Conversation.objects.filter(
            participants=request.user
        ).exclude(
            id__in=deleted_conversation_ids
        ).prefetch_related(
            Prefetch('participants'),
            Prefetch('messages', queryset=Message.objects.select_related('sender').order_by('-created_at'))
        ).order_by('-modified_at')
        
        print(f"📞 Found {conversations.count()} active conversations")
        
        # ... rest of your existing get_conversations code remains the same
        conversation_list = []
        for conv in conversations:
            other_user = conv.get_other_participant(request.user)
            if other_user:
                last_message = conv.messages.last()
                
                other_user_name = other_user.get_full_name()
                if not other_user_name.strip():
                    other_user_name = f"{other_user.first_name} {other_user.last_name}".strip()
                if not other_user_name.strip():
                    other_user_name = other_user.username
                
                conversation_list.append({
                    'id': str(conv.id),
                    'other_user_id': str(other_user.id),
                    'other_user_name': other_user_name,
                    'other_user': {
                        'id': str(other_user.id),
                        'username': other_user.username,
                        'first_name': other_user.first_name,
                        'last_name': other_user.last_name,
                        'email': other_user.email,
                        'role': other_user.user_type,
                        'is_active': other_user.is_active,
                        'profile_picture': other_user.profile_picture.url if other_user.profile_picture else None,
                    },
                    'last_message': {
                        'id': str(last_message.id),
                        'sender': str(last_message.sender.id),
                        'receiver': str(other_user.id),
                        'message': last_message.body,
                        'message_type': 'text',
                        'timestamp': last_message.created_at.isoformat(),
                        'is_read': False,
                        'sender_name': last_message.sender.get_full_name() or last_message.sender.username,
                        'receiver_name': other_user_name,
                    } if last_message else None,
                    'unread_count': 0,
                    'timestamp': conv.modified_at.isoformat(),
                })
        
        return JsonResponse(conversation_list, safe=False)
        
    except Exception as e:
        print(f"❌ Error in get_conversations: {str(e)}")
        return JsonResponse(
            {'error': f'Failed to fetch conversations: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    """Get all messages between current user and specified user"""
    try:
        print(f"📨 Fetching messages between {request.user.id} and {user_id}")
        
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants__id=user_id
        ).prefetch_related('messages__sender').first()

        if not conversation:
            print("📨 No conversation found, returning empty list")
            return JsonResponse([], safe=False)

        messages = conversation.messages.select_related('sender').order_by('created_at')
        
        message_list = []
        for msg in messages:
            # FIX: Pass the sender as argument to get_other_participant
            other_user = conversation.get_other_participant(msg.sender)
            message_list.append({
                'id': str(msg.id),
                'sender': str(msg.sender.id),
                'receiver': str(other_user.id) if other_user else str(request.user.id),
                'message': msg.body,
                'message_type': 'text',
                'timestamp': msg.created_at.isoformat(),
                'is_read': False,
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'receiver_name': other_user.get_full_name() or other_user.username if other_user else request.user.get_full_name() or request.user.username,
            })
            
        print(f"📨 Returning {len(message_list)} messages")
        return JsonResponse(message_list, safe=False)

    except Exception as e:
        print(f"❌ Error in get_messages: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Failed to fetch messages: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Send a message to another user"""
    receiver_id = request.data.get('receiver_id')
    message_text = request.data.get('message')
    
    print(f"📤 Sending message from {request.user.id} to {receiver_id}: {message_text}")
    
    if not receiver_id or not message_text:
        return JsonResponse(
            {'error': 'receiver_id and message are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        receiver = User.objects.get(id=receiver_id)
        
        # Find or create conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=receiver
        ).first()
        
        if not conversation:
            print("📤 Creating new conversation")
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, receiver)
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=message_text
        )
        
        # Update conversation modified time
        conversation.save()
        
        # Get the other participant for the response
        other_user = conversation.get_other_participant(request.user)
        
        # Return formatted response
        response_data = {
            'id': str(message.id),
            'sender': str(request.user.id),
            'receiver': str(receiver.id),
            'message': message_text,
            'message_type': 'text',
            'timestamp': message.created_at.isoformat(),
            'is_read': False,
            'sender_name': request.user.get_full_name() or request.user.username,
            'receiver_name': other_user.get_full_name() or other_user.username if other_user else receiver.get_full_name() or receiver.username,
        }
        
        print(f"✅ Message sent successfully: {response_data}")
        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
        
    except User.DoesNotExist:
        print(f"❌ Receiver not found: {receiver_id}")
        return JsonResponse(
            {'error': 'Receiver not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ Error in send_message: {str(e)}")
        return JsonResponse(
            {'error': f'Failed to send message: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
# chat/api.py - ADD THIS FUNCTION
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_conversation(request, conversation_id):
    """Delete a conversation for the current user (soft delete)"""
    try:
        print(f"🗑️ User {request.user.username} deleting conversation {conversation_id}")
        
        # Get the conversation
        conversation = Conversation.objects.filter(
            id=conversation_id,
            participants=request.user
        ).first()
        
        if not conversation:
            print(f"❌ Conversation {conversation_id} not found or user not a participant")
            return JsonResponse(
                {'error': 'Conversation not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create deleted conversation record
        deleted_conv, created = DeletedConversation.objects.get_or_create(
            user=request.user,
            conversation=conversation,
            defaults={'deleted_at': timezone.now()}
        )
        
        if not created:
            deleted_conv.deleted_at = timezone.now()
            deleted_conv.save()
        
        print(f"✅ Conversation {conversation_id} deleted for user {request.user.username}")
        return JsonResponse({
            'success': True,
            'message': 'Conversation deleted successfully'
        })
        
    except Exception as e:
        print(f"❌ Error deleting conversation: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Failed to delete conversation: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )