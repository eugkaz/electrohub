
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.templatetags.static import static 
from django.utils import timezone
from .models import ChatRoom, ChatMessage, User 
import uuid 
from django.core.exceptions import ValidationError

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_id = str(uuid.UUID(self.scope['url_route']['kwargs']['room_id']))
        except ValueError:
            await self.close(code=4000) 
            return
            
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        has_access = await self.check_room_access()
        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_update_broadcast',
                'user_id': str(self.user.id),
                'is_online': True
            }
        )
        print(f"User {self.user.username} connected to room {self.room_id}. Group: {self.room_group_name}")


    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and hasattr(self, 'user') and self.user and self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status_update_broadcast',
                    'user_id': str(self.user.id),
                    'is_online': False
                }
            )
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"User {self.user.username} disconnected from room {self.room_id}. Code: {close_code}")


    async def receive(self, text_data):
        if not hasattr(self, 'user') or not self.user or not self.user.is_authenticated:
            return

        print(f"Consumer RAW received text_data from {self.user.username}: {text_data}") 
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error_message("Invalid JSON format.")
            return
            
        message_type_from_client = data.get('type')
        print(f"Received message from {self.user.username} in room {self.room_id}: type='{message_type_from_client}'. Parsed data: {data}") 

        if message_type_from_client == 'text_message_from_client':
            
            
            
            text_content_value = data.get('content') 
            
            
            print(f"DEBUG: Attempting to get 'content'. Value: '{text_content_value}', Type: {type(text_content_value)}")

            if text_content_value is None: 
                print("ERROR: 'content' key not found in data or its value is None.")
                text_content = "" 
            elif not isinstance(text_content_value, str): 
                print(f"ERROR: Value for 'content' is not a string. Got type: {type(text_content_value)}. Value: {text_content_value}")
                text_content = "" 
            else: 
                text_content = text_content_value.strip()
            
            print(f"Consumer extracted text_content: '{text_content}' (after potential strip)") 

            if not text_content: 
                print("text_content is empty after strip, not saving or broadcasting.")
                return

            chat_message_obj = await self.save_db_message(text_content, 'text')
            if not chat_message_obj:
                await self.send_error_message("Failed to save message.")
                return

            sender_avatar_url = await self.get_user_avatar(self.user)
            
            
            message_payload_for_broadcast = {
                'id': chat_message_obj.id,
                'sender_id': str(chat_message_obj.sender_id),
                'sender_display_name': chat_message_obj.sender.get_full_name() or chat_message_obj.sender.username,
                'sender_avatar_url': sender_avatar_url,
                'content': chat_message_obj.content, 
                'timestamp': chat_message_obj.timestamp.isoformat(),
                'message_type': chat_message_obj.message_type,
                'image_url': chat_message_obj.image.url if chat_message_obj.message_type == 'image' and chat_message_obj.image else None,
                'is_edited': chat_message_obj.is_edited,
                'is_deleted_by_sender': chat_message_obj.is_deleted_by_sender,
            }
            print(f"Broadcasting message payload: {message_payload_for_broadcast}") 

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': message_payload_for_broadcast
                }
            )
        elif message_type_from_client == 'user_active_in_room':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status_update_broadcast',
                    'user_id': str(self.user.id),
                    'is_online': True
                }
            )
        else:
            print(f"Unknown message type from client: {message_type_from_client}")


    async def chat_message_broadcast(self, event):
        message_data = event['message']
        
        print(f"Client {self.user.username} in room {self.room_id} is about to receive broadcast: {message_data}")
        await self.send(text_data=json.dumps({
            'type': 'chat_message_broadcast',
            'message': message_data
        }))

    async def user_status_update_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status_update',
            'user_id': event['user_id'],
            'is_online': event['is_online']
        }))

    async def send_error_message(self, error_text):
        await self.send(text_data=json.dumps({
            'type': 'error_message',
            'message': error_text
        }))

    @database_sync_to_async
    def save_db_message(self, content, msg_type, image_file_obj=None):
        try:
            room_instance = ChatRoom.objects.get(id=self.room_id)
            message = ChatMessage(
                room=room_instance,
                sender=self.user,
                content=content,
                message_type=msg_type,
                image=image_file_obj
            )
            message.full_clean()
            message.save()
            print(f"DB: Saved message ID {message.id} with content: '{content}'") 
            return message
        except ChatRoom.DoesNotExist:
            print(f"ChatConsumer DB Error: Room {self.room_id} does not exist.")
            return None
        except ValidationError as e:
            print(f"ChatConsumer DB Error: Validation error saving message - {e}")
            return None
        except Exception as e:
            print(f"ChatConsumer DB Error: Generic error saving message - {e}")
            return None

    @database_sync_to_async
    def get_user_avatar(self, user_obj):
        profile = getattr(user_obj, 'profile', None)
        default_avatar_url = static('images/default_avatar.png')
        if profile and profile.avatar and hasattr(profile.avatar, 'url'):
            return profile.avatar.url
        return default_avatar_url

    @database_sync_to_async
    def check_room_access(self):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            return self.user == room.buyer or self.user == room.seller
        except ChatRoom.DoesNotExist:
            return False
    
    async def chat_message_deleted_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message_deleted',
            'message_id': event['message_id'],
            'room_id': event['room_id'], 
        }))
    
    async def chat_message_edited_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message_edited',
            'message_id': event['message_id'],
            'new_content': event['new_content'],
            'is_edited_flag': event['is_edited_flag'],
        }))