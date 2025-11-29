# chat/consumers.py

import json
import jwt
import logging
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    # ──────────────────────────────────────────────────────────
    # CONNECTION
    # ──────────────────────────────────────────────────────────
    async def connect(self):
        try:
            token = self._extract_token()

            self.user = (
                await self.get_user_from_jwt(token)
                if token else AnonymousUser()
            )

            if self.user.is_anonymous:
                return await self.close(code=4001)

            await self.accept()

            await self._join_core_groups()
            await self._send_online_notification()
            await self._confirm_connection()

        except Exception as exc:
            logger.error("WebSocket connection error: %s", exc)
            await self.close(code=4002)

    async def disconnect(self, close_code):
        if not getattr(self, "user", None) or self.user.is_anonymous:
            return

        await self._leave_core_groups()
        await self._send_offline_notification()

    # ──────────────────────────────────────────────────────────
    # MESSAGE ROUTER
    # ──────────────────────────────────────────────────────────
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        handler_map = {
            "join_conversation": self.handle_join_conversation,
            "send_message": self.handle_send_message,
            "mark_as_read": self.handle_mark_as_read,
            "typing_start": lambda d: self.handle_typing(d, True),
            "typing_stop": lambda d: self.handle_typing(d, False),
        }

        handler = handler_map.get(data.get("type"))
        if handler:
            try:
                await handler(data)
            except Exception as exc:
                logger.error("Handler error: %s", exc)

    # ──────────────────────────────────────────────────────────
    # HANDLERS
    # ──────────────────────────────────────────────────────────
    async def handle_join_conversation(self, data):
        cid = data.get("conversation_id")
        if cid:
            await self.channel_layer.group_add(f"conversation_{cid}", self.channel_name)

    async def handle_send_message(self, data):
        conversation_id = data.get("conversation_id")
        message_text = data.get("message")
        receiver_id = data.get("receiver_id")

        if not all([conversation_id, message_text, receiver_id]):
            return

        message_data, final_conversation_id = await self.save_message_to_db(
            conversation_id, message_text, receiver_id
        )
        if not message_data:
            return

        # broadcast to conversation
        await self.channel_layer.group_send(
            f"conversation_{final_conversation_id}",
            {"type": "chat_message", "message": message_data},
        )

        # notify receiver personally
        await self.channel_layer.group_send(
            f"user_{receiver_id}",
            {"type": "chat_message", "message": message_data},
        )

    async def handle_mark_as_read(self, data):
        message_id = data.get("message_id")
        cid = data.get("conversation_id")

        if not message_id:
            return

        if await self.mark_message_as_read(message_id):
            await self.channel_layer.group_send(
                f"conversation_{cid}",
                {
                    "type": "message_read",
                    "message_id": message_id,
                    "reader_id": str(self.user.id),
                    "reader_name": self.user.username,
                },
            )

    async def handle_typing(self, data, is_typing):
        if cid := data.get("conversation_id"):
            await self.channel_layer.group_send(
                f"conversation_{cid}",
                {
                    "type": "typing_indicator",
                    "user_id": str(self.user.id),
                    "user_name": self.user.username,
                    "is_typing": is_typing,
                },
            )

    # ──────────────────────────────────────────────────────────
    # GROUP EVENT HANDLERS (broadcast → client)
    # ──────────────────────────────────────────────────────────
    async def chat_message(self, event):
        await self._send_json("chat_message", event["message"])

    async def message_read(self, event):
        await self._send_json("message_read", event)

    async def user_online(self, event):
        await self._send_json("user_online", event)

    async def user_offline(self, event):
        await self._send_json("user_offline", event)

    async def typing_indicator(self, event):
        await self._send_json("typing_indicator", event)

    # ──────────────────────────────────────────────────────────
    # UTILITIES
    # ──────────────────────────────────────────────────────────
    def _extract_token(self):
        query = self.scope.get("query_string", b"").decode()
        if "token=" not in query:
            return None

        token = query.split("token=")[1].split("&")[0]
        return token.strip('"\' ')

    async def _send_json(self, event_type, payload):
        await self.send(
            text_data=json.dumps(
                {"type": event_type, **payload}
                if isinstance(payload, dict)
                else {"type": event_type, "message": payload}
            )
        )

    async def _confirm_connection(self):
        await self._send_json(
            "connection_established",
            {
                "message": "WebSocket connection established successfully",
                "user_id": str(self.user.id),
            },
        )

    async def _join_core_groups(self):
        self.user_room = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_room, self.channel_name)
        await self.channel_layer.group_add("online_users", self.channel_name)

    async def _leave_core_groups(self):
        if hasattr(self, "user_room"):
            await self.channel_layer.group_discard(self.user_room, self.channel_name)
        await self.channel_layer.group_discard("online_users", self.channel_name)

    async def _send_online_notification(self):
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_online",
                "user_id": str(self.user.id),
                "username": self.user.username,
            },
        )

    async def _send_offline_notification(self):
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_offline",
                "user_id": str(self.user.id),
                "username": self.user.username,
            },
        )

    # ──────────────────────────────────────────────────────────
    # DATABASE OPERATIONS
    # ──────────────────────────────────────────────────────────
    @database_sync_to_async
    def get_user_from_jwt(self, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            uid = payload.get("user_id")
            return User.objects.get(pk=uid)
        except Exception:
            return AnonymousUser()

    @database_sync_to_async
    def save_message_to_db(self, conversation_id, message_text, receiver_id):
        from .models import Conversation, Message

        try:
            is_new = conversation_id.startswith("temp-")

            if is_new:
                conversation = Conversation.objects.filter(
                    participants=self.user, participants__id=receiver_id
                ).first()

                if not conversation:
                    receiver = User.objects.get(id=receiver_id)
                    conversation = Conversation.objects.create()
                    conversation.participants.add(self.user, receiver)

                conversation_id = str(conversation.id)
            else:
                conversation = Conversation.objects.get(id=conversation_id)

            msg = Message.objects.create(
                conversation=conversation, sender=self.user, body=message_text
            )

            receiver = User.objects.get(id=receiver_id)

            return (
                {
                    "id": str(msg.id),
                    "sender": str(self.user.id),
                    "receiver": str(receiver.id),
                    "message": message_text,
                    "message_type": "text",
                    "timestamp": msg.created_at.isoformat(),
                    "conversation_id": conversation_id,
                    "is_new_conversation": is_new,
                },
                conversation_id,
            )

        except Exception as exc:
            logger.error("DB error saving message: %s", exc)
            return None, None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        from .models import Message

        try:
            msg = Message.objects.get(id=message_id)
            if str(msg.sender_id) != str(self.user.id):
                msg.is_read = True
                msg.save()
                return True
            return False
        except Message.DoesNotExist:
            return False
