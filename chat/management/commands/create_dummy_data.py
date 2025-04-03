import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from chat.models import Message
from faker import Faker

class Command(BaseCommand):
    help = 'Creates dummy users and messages for testing'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=10, help='Number of users to create')
        parser.add_argument('--messages', type=int, default=200, help='Number of messages to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before creating new data')

    def handle(self, *args, **options):
        num_users = options['users']
        num_messages = options['messages']
        clear_data = options['clear']

        fake = Faker()

        if clear_data:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            # Only delete non-superuser accounts
            User.objects.filter(is_superuser=False).delete()
            Message.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared!'))

        # Create users
        self.stdout.write(self.style.NOTICE(f'Creating {num_users} dummy users...'))
        users = []

        # Check if admin user exists, if not create one
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            users.append(admin)
            self.stdout.write(self.style.SUCCESS(f'Created admin user: admin / admin123'))
        else:
            admin = User.objects.get(username='admin')
            users.append(admin)

        # Create regular users
        for i in range(num_users):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}{i}"

            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="123",
                    first_name=first_name,
                    last_name=last_name
                )
                users.append(user)
                self.stdout.write(self.style.SUCCESS(f'Created user: {username} / 123'))

        # Create messages
        self.stdout.write(self.style.NOTICE(f'Creating {num_messages} dummy messages...'))

        # Get all users if we need more than the ones we just created
        if len(users) < 2:
            users = list(User.objects.all())

        now = timezone.now()

        for i in range(num_messages):
            # Select random sender and receiver
            sender = random.choice(users)
            # Make sure sender and receiver are different
            receiver = random.choice([u for u in users if u != sender])

            # Create a random timestamp within the last 30 days
            random_days = random.randint(0, 30)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            timestamp = now - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)

            # Generate message content
            if random.random() < 0.2:  # 20% chance for a question
                content = fake.sentence(nb_words=random.randint(5, 15)) + "?"
            elif random.random() < 0.1:  # 10% chance for a longer message
                content = fake.paragraph(nb_sentences=random.randint(2, 5))
            else:  # 70% chance for a regular message
                content = fake.sentence(nb_words=random.randint(3, 12))

            # Create the message
            message = Message.objects.create(
                sender=sender,
                receiver=receiver,
                content=content,
                timestamp=timestamp
            )

            if (i + 1) % 50 == 0 or i + 1 == num_messages:
                self.stdout.write(self.style.SUCCESS(f'Created {i + 1} messages'))

        self.stdout.write(self.style.SUCCESS('Dummy data creation completed!'))
        self.stdout.write(self.style.NOTICE('You can login with any of these accounts:'))
        self.stdout.write(self.style.NOTICE('Admin: admin / admin123'))
        self.stdout.write(self.style.NOTICE('Users: [username] / password123'))

