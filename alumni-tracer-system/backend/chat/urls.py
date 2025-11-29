from django.urls import path
from . import api

urlpatterns = [
    path('conversations/', api.get_conversations, name='get_conversations'),
    path('messages/<str:user_id>/', api.get_messages, name='get_messages'),  # Changed to str
    path('send/', api.send_message, name='send_message'),
    path('conversations/<uuid:conversation_id>/delete/', api.delete_conversation, name='delete_conversation'),

]