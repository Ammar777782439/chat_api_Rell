from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from users.models import CustomUser
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from chat.models import Message
from chat.serializers import MessageSerializer
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from chat.consumers import ChatConsumer
from chat_app.asgi import application
import json

class MessageViewSetTest(APITestCase):
    def setUp(self):
        """إعداد البيانات اللي بنستخدمها في الاختبارات"""

        # إنشاء مستخدمين للتجربة
        self.user1 = CustomUser.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user2',
            password='testpass123'
        )

        # إنشاء رسالتين اختبار
        self.message1 = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content='Hello user2'
        )
        self.message2 = Message.objects.create(
            sender=self.user2,
            receiver=self.user1,
            content='Hi user1'
        )

        # تجهيز API Client وتسجيل دخول user1
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_get_messages(self):
        """اختبار جلب جميع الرسائل"""
        response = self.client.get('/api/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # لازم يكون فيه رسالتين

    def test_get_filtered_messages(self):
        """اختبار جلب الرسائل المرسلة أو المستقبلة من مستخدم معين"""
        response = self.client.get(f'/api/messages/?user={self.user2.username}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # لازم يجيب كل الرسائل بينهم

    def test_create_message(self):
        """اختبار إرسال رسالة جديدة"""
        data = {
            'receiver': self.user2.id,
            'content': 'New test message'
        }
        response = self.client.post('/api/messages/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 3)  # لازم يصير عدد الرسائل 3

    def test_delete_message(self):
        """اختبار حذف رسالة خاصة بالمستخدم"""
        # اختبار الحذف الناعم عبر API
        response = self.client.delete(f'/api/messages/{self.message1.id}/delete_message/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # التأكد من أن الرسالة تم حذفها ناعماً (تحديث deleted_at)
        self.message1.refresh_from_db()
        self.assertIsNotNone(self.message1.deleted_at)
        # التأكد من أن الرسالة المحذوفة ناعماً لا تظهر في الاستعلامات العادية
        response = self.client.get(f'/api/messages/?user={self.user2.username}')
        self.assertEqual(len(response.data['results']), 1) # يجب أن تظهر رسالة واحدة فقط (message2)

    def test_delete_others_message(self):
        """اختبار محاولة حذف رسالة لشخص ثاني (المفروض يرفض)"""
        response = self.client.delete(f'/api/messages/{self.message2.id}/delete_message/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # ما يسمح له بالحذف

    def test_update_message(self):
        """اختبار تعديل رسالة خاصة بالمستخدم"""
        data = {'content': 'Updated content'}
        response = self.client.post(f'/api/messages/{self.message1.id}/update_message/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message1.refresh_from_db()  # تحديث البيانات بعد التعديل
        self.assertEqual(self.message1.content, 'Updated content')  # لازم المحتوى يتغير

    def test_update_others_message(self):
        """اختبار محاولة تعديل رسالة شخص ثاني (المفروض يرفض)"""
        data = {'content': 'Updated content'}
        response = self.client.post(f'/api/messages/{self.message2.id}/update_message/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # ما يسمح له بالتعديل

class ChatRoomViewTest(TestCase):
    def setUp(self):
        """إعداد بيانات الاختبار الخاصة بغرف الدردشة"""

        # إنشاء مستخدمين للتجربة
        self.user1 = CustomUser.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user2',
            password='testpass123'
        )

        # إنشاء رسالة اختبارية بينهم
        self.message1 = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content='Hello user2'
        )

        # تجهيز Client وتسجيل دخول user1
        self.client = Client()
        self.client.login(username='user1', password='testpass123')

    def test_chat_room_view(self):
        """اختبار صفحة الدردشة عند تسجيل الدخول"""
        response = self.client.get(f'/chat/{self.user2.username}/')
        self.assertEqual(response.status_code, 200)  # الصفحة لازم تفتح عادي
        self.assertTemplateUsed(response, 'chat.html')  # يتأكد إنه استخدم القالب الصح

    def test_chat_room_view_unauthenticated(self):
        """اختبار محاولة دخول صفحة الدردشة بدون تسجيل دخول"""
        self.client.logout()  # تسجيل خروج
        response = self.client.get(f'/chat/{self.user2.username}/')
        self.assertEqual(response.status_code, 302)  # لازم يعيد التوجيه لصفحة تسجيل الدخول

    def test_chat_room_search(self):
        """اختبار البحث عن رسالة داخل صفحة الدردشة"""
        response = self.client.get(f'/chat/{self.user2.username}/?search=Hello')
        self.assertEqual(response.status_code, 200)  # الصفحة تفتح بدون مشاكل
        self.assertTemplateUsed(response, 'chat.html')  # يتأكد إنه استخدم القالب الصح

class MessageModelTest(TestCase):
    """Test cases for the Message model"""

    def setUp(self):
        """Set up test data"""
        self.user1 = CustomUser.objects.create_user(
            username='testuser1',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='testuser2',
            password='testpass123'
        )

        self.message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content='Test message content'
        )

    def test_message_creation(self):
        """Test that a message can be created"""
        self.assertEqual(self.message.content, 'Test message content')
        self.assertEqual(self.message.sender, self.user1)
        self.assertEqual(self.message.receiver, self.user2)
        self.assertIsNone(self.message.deleted_at)

    def test_message_str_representation(self):
        """Test the string representation of a message"""
        expected_str = f"{self.user1} -> {self.user2}: Test message content"
        self.assertEqual(str(self.message), expected_str)

class MessageSerializerTest(TestCase):
    """Test cases for the MessageSerializer"""

    def setUp(self):
        """Set up test data"""
        self.user1 = CustomUser.objects.create_user(
            username='testuser1',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='testuser2',
            password='testpass123'
        )

        self.message_data = {
            'sender': self.user1,
            'receiver': self.user2.id,
            'content': 'Test message content'
        }

        self.message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content='Existing message'
        )

    def test_valid_serializer(self):
        """Test serializer with valid data"""
        serializer = MessageSerializer(data={
            'receiver': self.user2.id,
            'content': 'Valid content'
        })
        self.assertTrue(serializer.is_valid())

    def test_invalid_serializer_empty_content(self):
        """Test serializer with empty content"""
        serializer = MessageSerializer(data={
            'receiver': self.user2.id,
            'content': '   '
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

class WebSocketTests(TransactionTestCase):
    """Test cases for WebSocket functionality"""

    @database_sync_to_async
    def create_user(self, username, password):
        return CustomUser.objects.create_user(username=username, password=password)

    @database_sync_to_async
    def create_message(self, sender, receiver, content):
        return Message.objects.create(sender=sender, receiver=receiver, content=content)

    @database_sync_to_async
    def get_message(self, message_id):
        return Message.objects.get(id=message_id)

    @database_sync_to_async
    def count_messages(self, include_deleted=False):
        if include_deleted:
            return Message.objects.count()
        return Message.objects.filter(deleted_at__isnull=True).count()

    @database_sync_to_async
    def get_message_with_deleted(self, message_id):
        # جلب الرسالة حتى لو كانت محذوفة ناعماً
        return Message.objects.get(id=message_id)

    async def test_websocket_connect(self):
        """Test WebSocket connection"""
        user1 = await self.create_user('wsuser1', 'password123')
        user2 = await self.create_user('wsuser2', 'password123')

        # Create a communicator for testing
        communicator = WebsocketCommunicator(
            application=application,
            path=f'/ws/chat/{user2.username}/'
        )

        # Set the user in the scope (simulating authentication)
        communicator.scope['user'] = user1

        # Connect to the WebSocket
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Disconnect
        await communicator.disconnect()

    async def test_websocket_send_message(self):
        """Test sending a message through WebSocket"""
        user1 = await self.create_user('wsuser3', 'password123')
        user2 = await self.create_user('wsuser4', 'password123')

        # Create a communicator for testing
        communicator = WebsocketCommunicator(
            application=application,
            path=f'/ws/chat/{user2.username}/'
        )

        # Set the user in the scope (simulating authentication)
        communicator.scope['user'] = user1

        # Connect to the WebSocket
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a message
        initial_count = await self.count_messages()
        await communicator.send_json_to({
            'message': 'Hello from WebSocket test'
        })

        # Receive the response
        response = await communicator.receive_json_from()

        # Check the response
        self.assertEqual(response['message'], 'Hello from WebSocket test')
        self.assertEqual(response['sender'], user1.username)
        self.assertEqual(response['receiver'], user2.username)

        # Check that a message was created in the database
        new_count = await self.count_messages()
        self.assertEqual(new_count, initial_count + 1)

        # Disconnect
        await communicator.disconnect()

    async def test_websocket_update_message(self):
        """Test updating a message through WebSocket"""
        user1 = await self.create_user('wsuser5', 'password123')
        user2 = await self.create_user('wsuser6', 'password123')

        # Create a message to update
        message = await self.create_message(user1, user2, 'Original message')

        # Create a communicator for testing
        communicator = WebsocketCommunicator(
            application=application,
            path=f'/ws/chat/{user2.username}/'
        )

        # Set the user in the scope (simulating authentication)
        communicator.scope['user'] = user1

        # Connect to the WebSocket
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Update the message
        await communicator.send_json_to({
            'message_id': message.id,
            'message': 'Updated message content'
        })

        # Receive the response
        response = await communicator.receive_json_from()

        # Check the response
        self.assertEqual(response['message'], 'Updated message content')
        self.assertEqual(response['message_id'], message.id)

        # Check that the message was updated in the database
        updated_message = await self.get_message(message.id)
        self.assertEqual(updated_message.content, 'Updated message content')

        # Disconnect
        await communicator.disconnect()

    async def test_websocket_delete_message(self):
        """Test deleting a message through WebSocket"""
        user1 = await self.create_user('wsuser7', 'password123')
        user2 = await self.create_user('wsuser8', 'password123')

        # Create a message to delete
        message = await self.create_message(user1, user2, 'Message to delete')

        # Create a communicator for testing
        communicator = WebsocketCommunicator(
            application=application,
            path=f'/ws/chat/{user2.username}/'
        )

        # Set the user in the scope (simulating authentication)
        communicator.scope['user'] = user1

        # Connect to the WebSocket
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Initial message count
        initial_count = await self.count_messages()

        # Delete the message
        await communicator.send_json_to({
            'delete_message_id': message.id
        })

        # Receive the response
        response = await communicator.receive_json_from()

        # Check the response
        self.assertEqual(response['deleted_message_id'], message.id)

        # Check that the message was soft-deleted in the database
        deleted_message = await self.get_message_with_deleted(message.id)
        self.assertIsNotNone(deleted_message.deleted_at)

        # Check that the count of non-deleted messages decreased
        new_count = await self.count_messages() # Counts only non-deleted by default
        self.assertEqual(new_count, initial_count - 1)

        # Disconnect
        await communicator.disconnect()
