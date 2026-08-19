"""
Tests for accounts app.
"""
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_verified_publisher)
        self.assertFalse(user.is_sponsored_oss)
        self.assertFalse(user.must_change_password)
        self.assertTrue(user.check_password("testpass123"))

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)

    def test_user_string_representation(self):
        """Test User __str__ method."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.assertEqual(str(user), "testuser")

    def test_is_admin_property(self):
        """Test is_admin property for different roles."""
        user = User.objects.create_user(username="user1", password="pass123")
        admin = User.objects.create_user(username="admin1", password="pass123", role=User.Role.ADMIN)
        super_admin = User.objects.create_user(username="sadmin1", password="pass123", role=User.Role.SUPER_ADMIN)

        self.assertFalse(user.is_admin)
        self.assertTrue(admin.is_admin)
        self.assertTrue(super_admin.is_admin)

    def test_is_super_admin_property(self):
        """Test is_super_admin property."""
        admin = User.objects.create_user(username="admin1", password="pass123", role=User.Role.ADMIN)
        super_admin = User.objects.create_user(username="sadmin1", password="pass123", role=User.Role.SUPER_ADMIN)

        self.assertFalse(admin.is_super_admin)
        self.assertTrue(super_admin.is_super_admin)


class SetupAdminCommandTest(TestCase):
    """Test cases for the setup_admin management command."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.password_file = os.path.join(self.tmp_dir.name, "admin_password.txt")
        self.addCleanup(self.tmp_dir.cleanup)

    def test_command_creates_admin_user(self):
        """Running the command creates a user named 'admin'."""
        with override_settings(ADMIN_PASSWORD_FILE=self.password_file):
            call_command("setup_admin")

        self.assertTrue(User.objects.filter(username="admin").exists())

    def test_command_is_idempotent(self):
        """Running the command twice does not create a duplicate admin."""
        with override_settings(ADMIN_PASSWORD_FILE=self.password_file):
            call_command("setup_admin")
            call_command("setup_admin")

        self.assertEqual(User.objects.filter(username="admin").count(), 1)

    def test_command_writes_password_file(self):
        """Running the command creates the password file with content."""
        with override_settings(ADMIN_PASSWORD_FILE=self.password_file):
            call_command("setup_admin")

        self.assertTrue(os.path.exists(self.password_file))
        with open(self.password_file) as f:
            password = f.read().strip()
        self.assertTrue(len(password) > 0)

    def test_admin_has_correct_role_and_flag(self):
        """The created admin has role=SUPER_ADMIN and must_change_password=True."""
        with override_settings(ADMIN_PASSWORD_FILE=self.password_file):
            call_command("setup_admin")

        admin = User.objects.get(username="admin")
        self.assertEqual(admin.role, User.Role.SUPER_ADMIN)
        self.assertTrue(admin.must_change_password)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)


class RegisterViewTest(TestCase):
    """Test cases for the registration view."""

    def _valid_data(self, **overrides):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        data.update(overrides)
        return data

    def test_valid_registration_creates_user(self):
        """A valid submission creates a user with role=USER and redirects to login."""
        response = self.client.post("/register/", self._valid_data())

        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")

    def test_duplicate_username_shows_error(self):
        """Registering with an existing username re-renders the form with an error."""
        User.objects.create_user(username="existing", email="existing@example.com", password="pass12345")

        response = self.client.post("/register/", self._valid_data(username="existing"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.filter(username="existing").count(), 1)

    def test_password_mismatch_shows_error(self):
        """Registering with mismatched passwords re-renders the form with an error."""
        response = self.client.post("/register/", self._valid_data(password2="DifferentPass456!"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_authenticated_user_redirected_away(self):
        """Authenticated users are redirected away from the registration page."""
        User.objects.create_user(username="loggedin", password="pass12345")
        self.client.login(username="loggedin", password="pass12345")

        response = self.client.get("/register/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
