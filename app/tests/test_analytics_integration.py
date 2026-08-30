"""
Integration tests for analytics and log search functionality.

These exercise log indexing and the admin log search page end-to-end
through the Django test client, mocking Elasticsearch responses rather
than requiring a real cluster.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from analytics.management.commands.index_logs import INDEX_NAME
from analytics.query_parser import parse_logical_query

User = get_user_model()


def _write_log(path, entries):
    with open(path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


@patch('analytics.management.commands.index_logs.bulk')
@patch('analytics.management.commands.index_logs.Elasticsearch')
class LogIndexingIntegrationTest(TestCase):
    """Log indexing creates entries in Elasticsearch (mocked)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.logs_dir = Path(self.tmp_dir.name)

    def test_index_logs_sends_parsed_entries_to_elasticsearch(self, mock_es_cls, mock_bulk):
        mock_es_cls.return_value.indices.exists.return_value = False
        _write_log(self.logs_dir / 'app.log', [
            {'timestamp': '2026-08-25T10:00:00', 'level': 'INFO', 'logger': 'core', 'message': 'server started'},
        ])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        mock_es_cls.return_value.indices.create.assert_called_once()
        actions = mock_bulk.call_args[0][1]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['_index'], INDEX_NAME)
        self.assertEqual(actions[0]['_source']['message'], 'server started')

    def test_malformed_lines_are_not_sent_to_elasticsearch(self, mock_es_cls, mock_bulk):
        mock_es_cls.return_value.indices.exists.return_value = True
        with open(self.logs_dir / 'app.log', 'w') as f:
            f.write('not valid json\n')
            f.write(json.dumps({'level': 'ERROR', 'message': 'disk full'}) + '\n')

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        actions = mock_bulk.call_args[0][1]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['_source']['message'], 'disk full')

    @patch('analytics.views.Elasticsearch')
    def test_indexed_entry_is_what_the_search_page_then_displays(self, mock_search_es_cls, mock_index_es_cls, mock_bulk):
        """Ties the two mocked ES layers together: what index_logs would bulk-upload
        is the same document the search page renders once ES hands it back."""
        mock_index_es_cls.return_value.indices.exists.return_value = True
        _write_log(self.logs_dir / 'app.log', [
            {'timestamp': '2026-08-25 10:00:00,000', 'level': 'ERROR', 'logger': 'core', 'message': 'disk full on /var'},
        ])
        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')
        indexed_source = mock_bulk.call_args[0][1][0]['_source']

        User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.client.login(username='siteadmin', password='AdminPass123!')
        mock_search_es_cls.return_value.search.return_value = {
            'hits': {'total': {'value': 1}, 'hits': [{'_source': indexed_source}]},
        }

        response = self.client.get(reverse('log_search'), {'q': 'disk full'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'disk full on /var')
        self.assertEqual(response.context['results'], [indexed_source])


@patch('analytics.views.Elasticsearch')
class LogSearchAccessControlIntegrationTest(TestCase):
    """Only admins can access the analytics log search page."""

    def setUp(self):
        self.url = reverse('log_search')
        self.admin = User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.super_admin = User.objects.create_user(
            username='rootadmin', password='RootPass123!', role=User.Role.SUPER_ADMIN,
        )
        self.regular_user = User.objects.create_user(username='janedoe', password='RegularPass123!')

    def test_anonymous_user_is_redirected_to_login(self, mock_es_cls):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/login/?next={self.url}')
        mock_es_cls.return_value.search.assert_not_called()

    def test_regular_user_is_forbidden(self, mock_es_cls):
        self.client.login(username='janedoe', password='RegularPass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        mock_es_cls.return_value.search.assert_not_called()

    def test_admin_can_access(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}
        self.client.login(username='siteadmin', password='AdminPass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_super_admin_can_access(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}
        self.client.login(username='rootadmin', password='RootPass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


@patch('analytics.views.Elasticsearch')
class LogSearchQueryIntegrationTest(TestCase):
    """Basic search returns matching results from Elasticsearch (mocked)."""

    def setUp(self):
        self.url = reverse('log_search')
        User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.client.login(username='siteadmin', password='AdminPass123!')

    def test_basic_search_returns_matching_results(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {
            'hits': {
                'total': {'value': 1},
                'hits': [{
                    '_source': {
                        'timestamp': '2026-08-25 10:00:00,000',
                        'level': 'ERROR',
                        'message': 'connection timeout',
                    },
                }],
            },
        }

        response = self.client.get(self.url, {'q': 'timeout'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'connection timeout')
        self.assertEqual(len(response.context['results']), 1)

    def test_search_with_no_matches_returns_empty_results(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}

        response = self.client.get(self.url, {'q': 'nomatch'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results'], [])

    def test_combined_text_level_and_date_filters_build_expected_query(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}

        self.client.get(self.url, {
            'q': 'timeout', 'level': 'ERROR', 'date_after': '2026-08-01', 'date_before': '2026-08-25',
        })

        _, kwargs = mock_es_cls.return_value.search.call_args
        self.assertEqual(kwargs['query'], {
            'bool': {
                'must': [{'multi_match': {'query': 'timeout', 'fields': ['message'], 'type': 'bool_prefix'}}],
                'filter': [
                    {'term': {'level': 'ERROR'}},
                    {'range': {'timestamp': {'gte': '2026-08-01', 'lte': '2026-08-25'}}},
                ],
            },
        })


class LogicalQueryBuilderIntegrationTest(TestCase):
    """Logical query builder produces the correct Elasticsearch query."""

    def test_and_or_not_and_parentheses_build_expected_query(self):
        query = parse_logical_query('(level:warning OR level:error) AND NOT user:marija')

        self.assertEqual(query, {
            'bool': {
                'must': [
                    {'bool': {
                        'should': [
                            {'term': {'level': 'WARNING'}},
                            {'term': {'level': 'ERROR'}},
                        ],
                        'minimum_should_match': 1,
                    }},
                    {'bool': {'must_not': [{'term': {'user': 'marija'}}]}},
                ],
            },
        })

    @patch('analytics.views.Elasticsearch')
    def test_advanced_query_from_search_page_is_sent_to_elasticsearch_as_built(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}
        User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.client.login(username='siteadmin', password='AdminPass123!')

        self.client.get(reverse('log_search'), {'mode': 'advanced', 'advanced_q': 'message:"error occurred"'})

        _, kwargs = mock_es_cls.return_value.search.call_args
        self.assertEqual(kwargs['query'], {'match_phrase': {'message': 'error occurred'}})

    @patch('analytics.views.Elasticsearch')
    def test_invalid_advanced_query_shows_error_and_does_not_call_elasticsearch(self, mock_es_cls):
        User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.client.login(username='siteadmin', password='AdminPass123!')

        response = self.client.get(
            reverse('log_search'), {'mode': 'advanced', 'advanced_q': 'level:error AND'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('query_error', response.context)
        mock_es_cls.return_value.search.assert_not_called()
