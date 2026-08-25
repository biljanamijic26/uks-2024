"""
Tests for core app.
"""
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from pythonjsonlogger.jsonlogger import JsonFormatter

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


class RequestLoggingMiddlewareTest(TestCase):
    """Test cases for the request logging middleware."""

    def test_logs_are_created_on_request(self):
        """Every request produces a log entry on the 'core.request' logger."""
        with self.assertLogs('core.request', level='INFO') as captured:
            self.client.get('/login/')

        self.assertEqual(len(captured.records), 1)
        self.assertIn('GET /login/', captured.records[0].getMessage())

    def test_log_record_includes_method_path_and_user(self):
        """The log record carries method, path, and user as structured fields."""
        User.objects.create_user(username='logginguser', password='pass12345')
        self.client.login(username='logginguser', password='pass12345')

        with self.assertLogs('core.request', level='INFO') as captured:
            self.client.get('/profile/')

        record = captured.records[0]
        self.assertEqual(record.method, 'GET')
        self.assertEqual(record.path, '/profile/')
        self.assertEqual(record.user, 'logginguser')

    def test_log_record_has_no_user_when_anonymous(self):
        """The user field is None for requests from anonymous visitors."""
        with self.assertLogs('core.request', level='INFO') as captured:
            self.client.get('/login/')

        self.assertIsNone(captured.records[0].user)


class JsonLoggingConfigurationTest(TestCase):
    """Test cases for the JSON log formatting configured in settings.LOGGING."""

    def test_json_formatter_produces_valid_json_with_expected_keys(self):
        """The configured JSON formatter renders a log record as valid JSON with
        timestamp, level, logger, and message keys, plus any extra fields."""
        formatter_config = dict(settings.LOGGING['formatters']['json'])
        formatter_config.pop('()')
        formatter = JsonFormatter(**formatter_config)

        record = logging.LogRecord(
            name='core.request', level=logging.INFO, pathname='', lineno=0,
            msg='GET /login/ 200', args=(), exc_info=None,
        )
        record.user = 'someuser'
        record.path = '/login/'
        record.method = 'GET'

        parsed = json.loads(formatter.format(record))

        self.assertEqual(parsed['level'], 'INFO')
        self.assertEqual(parsed['logger'], 'core.request')
        self.assertEqual(parsed['message'], 'GET /login/ 200')
        self.assertIn('timestamp', parsed)
        self.assertEqual(parsed['user'], 'someuser')
        self.assertEqual(parsed['path'], '/login/')
        self.assertEqual(parsed['method'], 'GET')
