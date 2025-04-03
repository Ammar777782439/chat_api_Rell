"""Views for the chat application.

This module contains the views and viewsets for the chat application, including:
- MessageViewSet: API endpoints for CRUD operations on messages
- chat_room: View for rendering the chat room interface

The views handle user authentication, message filtering, pagination, and WebSocket integration.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import pytz
from rest_framework import serializers
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics, permissions, pagination
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from chat.serializers import MessageSerializer
from .models import Message

# def home_view(request):
#     # Check if access token is in URL parameters
#     access_token = request.GET.get('access_token')
#     refresh_token = request.GET.get('refresh_token')

#     # If tokens are present, store them in session
#     if access_token and refresh_token:
#         request.session['access_token'] = access_token
#         request.session['refresh_token'] = refresh_token

#     # Get messages
#     messages = Message.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:50]

#     # We don't check authentication here anymore since we're using client-side auth check
#     # The JavaScript in the template will handle redirecting unauthenticated users

#     return render(request, 'chat.html', {'messages': messages})

# نمط التصميم facory
class MessagePagination(PageNumberPagination):
    """
    Custom pagination class for the Message API.

    This class configures how messages are paginated in API responses, allowing
    clients to request specific page sizes and limiting the maximum page size.

    Attributes:
        page_size (int): Default number of messages per page (10).
        page_size_query_param (str): Query parameter name for specifying page size ('page_size').
        max_page_size (int): Maximum allowed page size (100).
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# نمط التصميم repository
class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Message model CRUD operations through the API.

    This ViewSet provides endpoints for creating, retrieving, updating, and deleting messages,
    with additional custom actions for specific operations. It includes authentication,
    pagination, and filtering capabilities.

    Attributes:
        serializer_class: The serializer class used for message serialization/deserialization.
        permission_classes: List of permission classes that restrict access to authenticated users.
        pagination_class: The pagination class used for paginating message lists.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination
    
    def get_queryset(self):
        """
        Get the queryset of messages for the current user.

        This method filters messages to only include those where the current user
        is either the sender or receiver. It also supports filtering by another user
        when the 'user' query parameter is provided.

        Returns:
            QuerySet: Filtered queryset of Message objects ordered by timestamp (newest first).
        """
        user = self.request.user
        other_user = self.request.query_params.get('user', None)

        # Base queryset: all messages where the current user is sender or receiver
        queryset = Message.objects.filter(
            (Q(sender=user) | Q(receiver=user))
        ).order_by('-timestamp')

        # Additional filtering by other user if specified
        if other_user:
            queryset = queryset.filter(
                Q(sender__username=other_user) |
                Q(receiver__username=other_user)
            )

        return queryset

    def perform_create(self, serializer):
        """
        Perform the creation of a new message.

        This method is called when a new message is being created through the API.
        It sets the sender to the current user and finds the receiver based on the
        provided username.

        Args:
            serializer: The serializer instance that will create the message.

        Raises:
            ValidationError: If the specified receiver username doesn't exist.
        """
        receiver_username = self.request.data.get('receiver')

        try:
            receiver = CustomUser.objects.get(id=receiver_username)
            serializer.save(sender=self.request.user, receiver=receiver)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Receiver not found")

    @action(detail=True, methods=['delete'])
    def delete_message(self, request, pk=None):
        """
        Custom action to delete a message.

        This endpoint allows a user to delete their own message. It checks that the
        current user is the sender of the message before allowing deletion.

        Args:
            request: The HTTP request object.
            pk: The primary key of the message to delete.

        Returns:
            Response: Empty response with 204 status code on success, or error response.
        """
        message = self.get_object()

        # Check if the user is the sender of the message
        if message.sender != request.user:
            return Response({"error": "You can only delete your own messages"}, status=status.HTTP_403_FORBIDDEN)

        # Delete the message
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def update_message(self, request, pk=None):
        """
        Custom action to update a message's content.

        This endpoint allows a user to edit the content of their own message. It checks that
        the current user is the sender of the message and that the new content is not empty.

        Args:
            request: The HTTP request object containing the new message content.
            pk: The primary key of the message to update.

        Returns:
            Response: Serialized message data on success, or error response.
        """
        message = self.get_object()

        # Check if the user is the sender of the message
        if message.sender != request.user:
            return Response({"error": "You can only edit your own messages"}, status=status.HTTP_403_FORBIDDEN)

        # Get and validate the new content
        content = request.data.get('content')
        if not content or not content.strip():
            return Response({"error": "Message content cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Update the message
        message.content = content
        message.save()

        # Return the updated message
        serializer = self.get_serializer(message)
        return Response(serializer.data)



@login_required
def chat_room(request, room_name):
    """
    View function for rendering the chat room interface.

    This view displays the chat interface for conversations between the current user
    and another user specified by room_name. It retrieves and displays messages between
    the users, supports searching within messages, and provides a list of all users
    with their last messages for the sidebar.

    Args:
        request: The HTTP request object.
        room_name: The username of the other user in the conversation.

    Returns:
        HttpResponse: Rendered chat.html template with context data.
    """
    # Get search query parameter (if any)
    search_query = request.GET.get('search', '')

    # Get all users except the current user for the sidebar
    users = CustomUser.objects.exclude(id=request.user.id)

    # Get messages between the current user and the specified user
    chats = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver__username=room_name)) |
        (Q(receiver=request.user) & Q(sender__username=room_name))
    )

    # Filter messages by search query if provided
    if search_query:
        chats = chats.filter(Q(content__icontains=search_query))

    # Order messages by timestamp (oldest first for chat display)
    chats = chats.order_by('timestamp')

    # Prepare data for the sidebar showing users and their last messages
    user_last_messages = []

    # Use a minimum datetime for users with no messages
    min_datetime = timezone.now().replace(year=1, month=1, day=1)

    # For each user, find the most recent message between them and the current user
    for user in users:
        last_message = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=user)) |
            (Q(receiver=request.user) & Q(sender=user))
        ).order_by('-timestamp').first()

        # Add user and their last message to the list
        user_last_messages.append({
            'user': user,
            'last_message': last_message,
            'timestamp': last_message.timestamp if last_message else min_datetime
        })

    # Sort users by the timestamp of their last message (newest first)
    user_last_messages = sorted(
        user_last_messages,
        key=lambda x: x['timestamp'],
        reverse=True
    )

    # Render the chat template with all necessary context data
    return render(request, 'chat.html', {
        'room_name': room_name,
        'chats': chats,
        'users': users,
        'user_last_messages': user_last_messages,
        'search_query': search_query,
        'slug': room_name  # Add slug variable for WebSocket connection
    })





