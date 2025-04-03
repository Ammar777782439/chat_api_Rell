from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Message(models.Model):
    """
    Message model for storing chat messages between users.

    This model represents a single message in the chat system. Each message has a sender,
    a receiver, content text, and a timestamp. Messages are stored in the database and can
    be retrieved, updated, or deleted through the API.

    Attributes:
        sender (ForeignKey): The user who sent the message.
        receiver (ForeignKey): The user who received the message.
        content (TextField): The text content of the message.
        timestamp (DateTimeField): The date and time when the message was sent.
    """
    sender = models.ForeignKey(
        User,
        related_name="sent_messages",
        on_delete=models.CASCADE,
        help_text="The user who sent this message"
    )
    receiver = models.ForeignKey(
        User,
        related_name="received_messages",
        on_delete=models.CASCADE,
        help_text="The user who received this message"
    )
    content = models.TextField(help_text="The content of the message")
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when the message was sent"
    )
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the message was deleted")

    class Meta:
        """
        Meta options for the Message model.
        """
        ordering = ['-timestamp']  # Order messages by timestamp (newest first)
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        indexes = [
            models.Index(fields=['sender', 'receiver']),  # Index for faster queries
            models.Index(fields=['timestamp']),  # Index for timestamp-based sorting
        ]

    def __str__(self):
        """
        String representation of the Message object.

        Returns:
            str: A string in the format "sender -> receiver: content_preview"
        """
        return f"{self.sender} -> {self.receiver}: {self.content[:20]}"
