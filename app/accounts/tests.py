"""
Tests for accounts app.
"""
from django.test import TestCase
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
