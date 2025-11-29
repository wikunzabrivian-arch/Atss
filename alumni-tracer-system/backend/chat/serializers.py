from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message, Conversation
from accounts.serializers import UserProfileSerializer

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)
    sender_id = serializers.CharField(source='sender.id', read_only=True)
    receiver_id = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "body", "sender", "sender_id", "receiver_id", "created_at"]
    
    def get_receiver_id(self, obj):
        # Get the other participant in the conversation
        request = self.context.get('request')
        if request and request.user:
            other_user = obj.conversation.get_other_participant(obj.sender)
            return str(other_user.id) if other_user else None
        return None

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserProfileSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "participants", "last_message", "other_user", "unread_count", "created_at", "modified_at"]

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and request.user:
            if other_user := obj.get_other_participant(request.user):
                return UserProfileSerializer(other_user).data
        return None

    def get_unread_count(self, obj):
        # Implement read receipts later
        return 0