"""WebSocket consumers for the chat application.

This module contains the WebSocket consumer classes that handle real-time
communication between users in the chat application. The consumers manage
WebSocket connections, message sending/receiving, and database operations.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import CustomUser
from .models import Message
from asgiref.sync import sync_to_async
from django.utils import timezone
from .kafka_producer import KafkaProducerService
import asyncio
import functools


async def run_in_thread(func, *args, **kwargs):
    """
    Run a synchronous function in a separate thread to avoid blocking the event loop.

    Args:
        func: The synchronous function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, functools.partial(func, *args, **kwargs)
    )


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling real-time chat communication.

    This consumer manages WebSocket connections for the chat application, including
    connecting users to chat rooms, sending and receiving messages, and updating
    or deleting messages in real-time.

    The consumer uses Django Channels to handle WebSocket connections and groups,
    and interacts with the database using asynchronous methods.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Kafka producer
        self.kafka_producer = KafkaProducerService(bootstrap_servers=['192.168.117.128:9094'])

    async def connect(self):
        """
        Handle WebSocket connection.

        This method is called when a WebSocket connection is established. It extracts
        the room name from the URL, creates a unique group name for the chat room,
        adds the channel to the group, and accepts the connection.

        The group name is created by sorting and joining the usernames of both users
        to ensure that the same group is used regardless of who initiated the chat.
        """
        try:
            # جلب اسم الغرفة من الرابط
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            print(f"WebSocket connecting to room: {self.room_name}")

            # جلب اسم المستخدمين الاثنين
            user1 = self.scope['user'].username
            user2 = self.room_name
            print(f"Chat between users: {user1} and {user2}")


            # تنظيف أسماء المستخدمين لإزالة الأحرف غير المسموح بها
            clean_user1 = ''.join(c for c in user1 if c.isalnum() or c in '-_.')
            clean_user2 = ''.join(c for c in user2 if c.isalnum() or c in '-_.')

            # التأكد من أن الأسماء المنظفة ليست فارغة
            if not clean_user1:
                clean_user1 = "user1"
            if not clean_user2:
                clean_user2 = "user2"

            self.room_group_name = f"chat_{''.join(sorted([clean_user1, clean_user2]))}"
            print(f"Group name created: {self.room_group_name}")

            # إضافة القناة إلى مجموعة الغرفة
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            print(f"Added to group: {self.room_group_name}")

            # قبول الاتصال عبر WebSocket
            await self.accept()
            print(f"WebSocket connection accepted for {user1} in room {self.room_name}")
        except Exception as e:
            print(f"Error in WebSocket connect: {str(e)}")
            # محاولة قبول الاتصال حتى في حالة الخطأ لتجنب تعليق المتصفح
            await self.accept()
            # إرسال رسالة خطأ للعميل
            await self.send(text_data=json.dumps({
                'error': f"Connection error: {str(e)}"
            }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        This method is called when a WebSocket connection is closed. It removes
        the channel from the room group.

        Args:
            close_code: The code indicating why the connection was closed.
        """
        try:
            # إزالة القناة من مجموعة الغرفة عند قطع الاتصال
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                print(f"Disconnected from group: {self.room_group_name} with code: {close_code}")
            else:
                print(f"Disconnected with code: {close_code} (no group name available)")
        except Exception as e:
            print(f"Error in disconnect: {str(e)}")

    async def receive(self, text_data):
        """
        Handle receiving messages from WebSocket.

        This method is called when a message is received from the WebSocket. It processes
        the message data, determines if it's a new message, an update to an existing one,
        or a message deletion request. It performs the appropriate database operation and
        broadcasts the action to all users in the room.

        Args:
            text_data: The JSON string containing the message data.
        """
        # تحليل البيانات المستلمة
        text_data_json = json.loads(text_data)
        sender = self.scope['user']
        receiver = await self.get_receiver_user()

        # التحقق من نوع العملية (إرسال، تحديث، أو حذف)
        message_id = text_data_json.get('message_id', None)
        delete_message_id = text_data_json.get('delete_message_id', None)

        # حالة حذف رسالة
        if delete_message_id:
            # حذف الرسالة
            deleted = await self.delete_message(delete_message_id, sender)
            if deleted:
                # إرسال إشعار الحذف إلى جميع المشتركين في الغرفة
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'sender': sender.username,
                        'receiver': receiver.username,
                        'deleted_message_id': delete_message_id
                    }
                )

                # إرسال إشعار الحذف إلى Kafka
                await self.send_to_kafka(
                    action='delete',
                    sender=sender,
                    receiver=receiver,
                    message_id=delete_message_id
                )
            return

        # الحصول على محتوى الرسالة للإرسال أو التحديث
        message = text_data_json['message']

        # حالة تحديث رسالة موجودة
        if message_id:
            # تحديث الرسالة
            updated = await self.update_message(message_id, sender, message)
            if updated:
                # إرسال التحديث إلى جميع المشتركين في الغرفة
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'sender': sender.username,
                        'receiver': receiver.username,
                        'message': message,
                        'message_id': message_id
                    }
                )

                # إرسال التحديث إلى Kafka
                await self.send_to_kafka(
                    action='update',
                    sender=sender,
                    receiver=receiver,
                    message_id=message_id,
                    content=message
                )
        # حالة إرسال رسالة جديدة
        else:
            # حفظ الرسالة الجديدة في قاعدة البيانات
            saved_message = await self.save_message(sender, receiver, message)

            # إخطار جميع المستخدمين بالرسالة الجديدة
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': sender.username,
                    'receiver': receiver.username,
                    'message': message,
                    'id': saved_message.id
                }
            )

            # إرسال الرسالة الجديدة إلى Kafka
            await self.send_to_kafka(
                action='create',
                sender=sender,
                receiver=receiver,
                message_id=saved_message.id,
                content=message
            )

    async def chat_message(self, event):
        """
        Handle chat messages sent to the room group.

        This method is called when a message is received from the room group.
        It sends the message to the WebSocket for the client to receive. It handles
        different types of events including new messages, message updates, and message deletions.

        Args:
            event: The event data containing the message information.
        """
        sender = event['sender']
        receiver = event['receiver']

        # تجهيز البيانات لإرسالها إلى العميل
        response_data = {
            'sender': sender,
            'receiver': receiver,
        }

        # التعامل مع حالة حذف رسالة
        if 'deleted_message_id' in event:
            response_data['deleted_message_id'] = event['deleted_message_id']
        # التعامل مع حالة إرسال أو تحديث رسالة
        else:
            message = event['message']
            response_data['message'] = message

            if 'message_id' in event:
                response_data['message_id'] = event['message_id']

            if 'id' in event:
                response_data['id'] = event['id']

        # إرسال البيانات عبر WebSocket
        await self.send(text_data=json.dumps(response_data))

    @sync_to_async
    def save_message(self, sender, receiver, message):
        """
        Save a new message to the database.
        """
        return Message.objects.create(sender=sender, receiver=receiver, content=message)

    @sync_to_async
    def update_message(self, message_id, sender, new_content):
        """
        Update an existing message in the database.
        """
        try:
            # البحث عن الرسالة والتأكد من ملكية المرسل لها
            message = Message.objects.get(id=message_id, sender=sender)
            message.content = new_content
            message.save()
            return True
        except Message.DoesNotExist:
            return False
    @sync_to_async
    def delete_message(self, message_id, sender):
        """
        delete an existing message in the database.
        """
        try:

            message = Message.objects.get(id=message_id, sender=sender, deleted_at__isnull=True)

            message.deleted_at = timezone.now()
            message.save(update_fields=['deleted_at'])
            print(f"Soft deleted message ID: {message_id} by sender: {sender.username}")
            return True
        except Message.DoesNotExist:
            print(f"Message ID: {message_id} not found or already deleted for sender: {sender.username}")
            return False

    async def send_to_kafka(self, action, sender, receiver, message_id=None, content=None):
        """
        Send a message to Kafka asynchronously.

        Args:
            action (str): The action type ('create', 'update', or 'delete')
            sender (User): The sender of the message
            receiver (User): The receiver of the message
            message_id (int, optional): The ID of the message (for updates and deletes)
            content (str, optional): The content of the message (for creates and updates)
        """
        try:
            # Prepare the message data
            message_data = {
                'action': action,
                'sender': sender.username,
                'receiver': receiver.username
            }

            if message_id is not None:
                message_data['message_id'] = message_id

            if content is not None:
                message_data['content'] = content

            # Send the message to Kafka in a separate thread
            await run_in_thread(
                self.kafka_producer.send_message,
                'chat_messages',
                message_data
            )
            print(f"Sent message to Kafka: {message_data}")
        except Exception as e:
            print(f"Error sending to Kafka: {str(e)}")

    @sync_to_async
    def get_receiver_user(self):
        """
        Get the User object for the receiver.
        """
        try:
            print(f"Looking for receiver with username: {self.room_name}")
            receiver = CustomUser.objects.get(username=self.room_name)
            print(f"Found receiver: {receiver.username} (ID: {receiver.id})")
            return receiver
        except CustomUser.DoesNotExist:
            print(f"Receiver not found: {self.room_name}, using current user as fallback")
            return self.scope['user']
        except Exception as e:
            print(f"Error getting receiver user: {str(e)}")
            return self.scope['user']
