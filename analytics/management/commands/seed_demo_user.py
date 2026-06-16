from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the local demo user for this SQLite-only stage."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password("admin123")
        user.is_staff = True
        user.is_superuser = True
        user.save()

        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Demo user {status}: admin / admin123"))
        self.stdout.write(self.style.WARNING("This account is for local demo use only. Do not use it in production."))
