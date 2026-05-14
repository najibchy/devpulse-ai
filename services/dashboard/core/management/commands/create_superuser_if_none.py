from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser if none exists"

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@devpulse.ai",
                password="admin123",
            )
            self.stdout.write(self.style.SUCCESS(
                "Superuser created: admin / admin123"
            ))
            self.stdout.write(self.style.WARNING(
                "⚠️  CHANGE THIS PASSWORD IMMEDIATELY in production!"
            ))
        else:
            self.stdout.write("Superuser already exists.")
