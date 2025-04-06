# Generated by Django 5.1.7 on 2025-04-03 19:42

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content", models.TextField(help_text="The content of the message")),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The date and time when the message was sent",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="The date and time when the message was deleted",
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Message",
                "verbose_name_plural": "Messages",
                "ordering": ["-timestamp"],
            },
        ),
    ]
