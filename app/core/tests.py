"""
Tests for core app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class HomeViewTest(TestCase):
    """Test cases for the home view."""

    def test_anonymous_user_redirected_to_login(self):
        """Anonymous visitors to the root URL are redirected to the login page."""
        response = self.client.get('/')

        self.assertRedirects(response, '/login/')

    def test_authenticated_user_sees_home_page(self):
        """Authenticated users see the home page instead of being redirected."""
        User.objects.create_user(username='homeuser', password='pass12345')
        self.client.login(username='homeuser', password='pass12345')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
