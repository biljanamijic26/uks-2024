"""
Tests for analytics app.
"""
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from elasticsearch import Elasticsearch, NotFoundError

from analytics.management.commands.index_logs import INDEX_NAME
from analytics.services import build_log_search_query

User = get_user_model()


def _write_log(path, entries):
    with open(path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


@patch('analytics.management.commands.index_logs.bulk')
@patch('analytics.management.commands.index_logs.Elasticsearch')
class IndexLogsCommandTest(TestCase):
    """Test cases for the index_logs management command."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.logs_dir = Path(self.tmp_dir.name)
        self.app_log = self.logs_dir / 'app.log'

    def _mock_es(self, mock_es_cls, index_exists=False):
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = index_exists
        mock_es_cls.return_value = mock_es
        return mock_es

    def test_parses_and_indexes_log_entries(self, mock_es_cls, mock_bulk):
        self._mock_es(mock_es_cls)
        _write_log(self.app_log, [
            {'timestamp': '2026-08-25T10:00:00', 'level': 'INFO', 'logger': 'core', 'message': 'hello'},
        ])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        actions = mock_bulk.call_args[0][1]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['_source']['message'], 'hello')
        self.assertEqual(actions[0]['_index'], INDEX_NAME)

    def test_creates_index_with_mapping_when_missing(self, mock_es_cls, mock_bulk):
        mock_es = self._mock_es(mock_es_cls, index_exists=False)
        _write_log(self.app_log, [{'level': 'INFO', 'message': 'hello'}])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        mock_es.indices.create.assert_called_once()

    def test_skips_index_creation_when_it_already_exists(self, mock_es_cls, mock_bulk):
        mock_es = self._mock_es(mock_es_cls, index_exists=True)
        _write_log(self.app_log, [{'level': 'INFO', 'message': 'hello'}])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        mock_es.indices.create.assert_not_called()

    def test_skips_malformed_lines(self, mock_es_cls, mock_bulk):
        self._mock_es(mock_es_cls, index_exists=True)
        with open(self.app_log, 'w') as f:
            f.write('not valid json\n')
            f.write(json.dumps({'level': 'INFO', 'message': 'ok'}) + '\n')

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        actions = mock_bulk.call_args[0][1]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['_source']['message'], 'ok')

    def test_position_tracking_skips_already_indexed_lines(self, mock_es_cls, mock_bulk):
        self._mock_es(mock_es_cls, index_exists=True)
        _write_log(self.app_log, [{'level': 'INFO', 'message': 'first'}])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')
            first_actions = mock_bulk.call_args[0][1]
            self.assertEqual(len(first_actions), 1)
            self.assertEqual(first_actions[0]['_source']['message'], 'first')

            with open(self.app_log, 'a') as f:
                f.write(json.dumps({'level': 'INFO', 'message': 'second'}) + '\n')

            call_command('index_logs')
            second_actions = mock_bulk.call_args[0][1]
            self.assertEqual(len(second_actions), 1)
            self.assertEqual(second_actions[0]['_source']['message'], 'second')

    def test_full_flag_reindexes_from_start(self, mock_es_cls, mock_bulk):
        self._mock_es(mock_es_cls, index_exists=True)
        _write_log(self.app_log, [{'level': 'INFO', 'message': 'first'}])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')
            mock_bulk.reset_mock()

            call_command('index_logs')
            mock_bulk.assert_not_called()

            call_command('index_logs', full=True)
            actions = mock_bulk.call_args[0][1]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]['_source']['message'], 'first')

    def test_missing_log_files_are_skipped(self, mock_es_cls, mock_bulk):
        self._mock_es(mock_es_cls, index_exists=True)

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs')

        mock_bulk.assert_not_called()


class IndexLogsIntegrationTest(TestCase):
    """Integration test that indexes into a real Elasticsearch instance, when reachable."""

    def setUp(self):
        self.es = Elasticsearch(settings.ELASTICSEARCH_URL)
        try:
            reachable = self.es.ping()
        except Exception:
            reachable = False
        if not reachable:
            self.skipTest(f'Elasticsearch is not reachable at {settings.ELASTICSEARCH_URL}')

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.logs_dir = Path(self.tmp_dir.name)
        self.addCleanup(lambda: self.es.indices.delete(index=INDEX_NAME, ignore_unavailable=True))

    def test_indexed_entry_is_searchable(self):
        app_log = self.logs_dir / 'app.log'
        _write_log(app_log, [{'level': 'INFO', 'logger': 'core', 'message': 'integration-test-marker'}])

        with override_settings(LOGS_DIR=self.logs_dir):
            call_command('index_logs', full=True)

        self.es.indices.refresh(index=INDEX_NAME)
        result = self.es.search(index=INDEX_NAME, query={'match': {'message': 'integration-test-marker'}})

        self.assertGreaterEqual(result['hits']['total']['value'], 1)


class BuildLogSearchQueryTest(TestCase):
    """Test cases for build_log_search_query."""

    def _cleaned_data(self, **overrides):
        data = {'q': '', 'level': '', 'date_after': None, 'date_before': None}
        data.update(overrides)
        return data

    def test_matches_everything_when_no_filters_given(self):
        query, _ = build_log_search_query(self._cleaned_data())
        self.assertEqual(query['bool']['must'], [{'match_all': {}}])
        self.assertEqual(query['bool']['filter'], [])

    def test_text_query_uses_multi_match_on_message(self):
        query, _ = build_log_search_query(self._cleaned_data(q='timeout'))
        self.assertEqual(
            query['bool']['must'],
            [{'multi_match': {'query': 'timeout', 'fields': ['message'], 'type': 'bool_prefix'}}],
        )

    def test_level_becomes_a_term_filter(self):
        query, _ = build_log_search_query(self._cleaned_data(level='ERROR'))
        self.assertIn({'term': {'level': 'ERROR'}}, query['bool']['filter'])

    def test_date_range_becomes_a_range_filter(self):
        query, _ = build_log_search_query(self._cleaned_data(date_after=date(2026, 8, 1), date_before=date(2026, 8, 25)))
        self.assertIn(
            {'range': {'timestamp': {'gte': '2026-08-01', 'lte': '2026-08-25'}}},
            query['bool']['filter'],
        )

    def test_sort_ranks_relevance_before_recency(self):
        _, sort = build_log_search_query(self._cleaned_data())
        self.assertEqual(sort, [{'_score': 'desc'}, {'timestamp': 'desc'}])


@patch('analytics.views.Elasticsearch')
class LogSearchViewTest(TestCase):
    """Test cases for the admin log search page."""

    def setUp(self):
        self.url = reverse('log_search')
        self.admin = User.objects.create_user(username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN)
        self.regular_user = User.objects.create_user(username='janedoe', password='RegularPass123!')

    def test_anonymous_user_is_redirected_to_login(self, mock_es_cls):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_regular_user_is_forbidden(self, mock_es_cls):
        self.client.login(username='janedoe', password='RegularPass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_load_page_without_searching(self, mock_es_cls):
        self.client.login(username='siteadmin', password='AdminPass123!')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        mock_es_cls.return_value.search.assert_not_called()

    def test_search_displays_results_from_elasticsearch(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {
            'hits': {
                'total': {'value': 1},
                'hits': [
                    {'_source': {'timestamp': '2026-08-25 10:00:00,000', 'level': 'ERROR', 'message': 'boom'}},
                ],
            },
        }
        self.client.login(username='siteadmin', password='AdminPass123!')
        response = self.client.get(self.url, {'q': 'boom'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'boom')
        expected = {'timestamp': '2026-08-25 10:00:00,000', 'level': 'ERROR', 'message': 'boom'}
        self.assertEqual(response.context['results'], [expected])
        self.assertEqual(response.context['num_pages'], 1)

    def test_search_shows_empty_state_when_no_hits(self, mock_es_cls):
        mock_es_cls.return_value.search.return_value = {'hits': {'total': {'value': 0}, 'hits': []}}
        self.client.login(username='siteadmin', password='AdminPass123!')
        response = self.client.get(self.url, {'q': 'nomatch'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No log entries match your search.')

    def test_search_shows_empty_state_when_index_does_not_exist_yet(self, mock_es_cls):
        mock_es_cls.return_value.search.side_effect = NotFoundError.__new__(NotFoundError)
        self.client.login(username='siteadmin', password='AdminPass123!')
        response = self.client.get(self.url, {'q': 'anything'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No log entries match your search.')
