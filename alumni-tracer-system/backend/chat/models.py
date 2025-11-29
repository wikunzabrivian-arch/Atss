from django.db import models
from django.conf import settings

import uuid

User= settings.AUTH_USER_MODEL
from django.utils import timezone

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified_at']

    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    body = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} -> {self.conversation}: {self.body[:50]}"

class DeletedConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['user', 'conversation']
        verbose_name = 'Deleted Conversation'
        verbose_name_plural = 'Deleted Conversations'
    
    def __str__(self):
        return f"{self.user.username} - {self.conversation.id}"