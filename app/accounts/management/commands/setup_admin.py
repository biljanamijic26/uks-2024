"""
Management command that creates the super administrator account on first run.
"""
import secrets
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

ADMIN_USERNAME = "admin"
PASSWORD_LENGTH = 16


def _generate_password(length=PASSWORD_LENGTH):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Creates the super administrator account on first run and saves its password to a file."

    def handle(self, *args, **options):
        if User.objects.filter(username=ADMIN_USERNAME).exists():
            self.stdout.write(self.style.WARNING(
                f"Super admin '{ADMIN_USERNAME}' already exists, skipping."
            ))
            return

        password = _generate_password()
        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            email="admin@localhost",
            password=password,
            role=User.Role.SUPER_ADMIN,
            must_change_password=True,
        )

        password_file = getattr(settings, "ADMIN_PASSWORD_FILE", "admin_password.txt")
        with open(password_file, "w") as f:
            f.write(password + "\n")

        self.stdout.write(self.style.SUCCESS(
            f"Super admin '{ADMIN_USERNAME}' created. Password saved to {password_file}."
        ))
