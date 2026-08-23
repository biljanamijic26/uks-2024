"""
Tests for explore app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from repositories.models import Repository

User = get_user_model()


class ExploreListViewTest(TestCase):
    """Test cases for the public repository search page."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')

    def test_unauthenticated_user_can_access(self):
        """An anonymous user can access the explore page."""
        response = self.client.get('/explore/')

        self.assertEqual(response.status_code, 200)

    def test_only_public_repositories_are_shown(self):
        """Private repositories never appear in explore results."""
        Repository.objects.create(owner=self.owner, name='public-repo', visibility=Repository.Visibility.PUBLIC)
        Repository.objects.create(owner=self.owner, name='private-repo', visibility=Repository.Visibility.PRIVATE)

        response = self.client.get('/explore/')

        repositories = list(response.context['repositories'])
        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0].name, 'public-repo')

    def test_search_filters_by_name(self):
        """Searching for a term matches repositories whose name contains it."""
        Repository.objects.create(owner=self.owner, name='nginx-server', short_description='unrelated')
        Repository.objects.create(owner=self.owner, name='redis-cache', short_description='unrelated')

        response = self.client.get('/explore/', {'q': 'nginx'})

        repositories = list(response.context['repositories'])
        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0].name, 'nginx-server')

    def test_search_filters_by_description(self):
        """Searching for a term matches repositories whose description contains it."""
        Repository.objects.create(owner=self.owner, name='my-app', short_description='A web server for static files')

        response = self.client.get('/explore/', {'q': 'web server'})

        repositories = list(response.context['repositories'])
        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0].name, 'my-app')

    def test_search_excludes_non_matching_repositories(self):
        """Repositories that don't match the search term are excluded."""
        Repository.objects.create(owner=self.owner, name='nginx-server')

        response = self.client.get('/explore/', {'q': 'postgres'})

        self.assertEqual(len(response.context['repositories']), 0)

    def test_relevance_sorting_ranks_name_matches_first(self):
        """A repository matching by name is ranked above one matching only by description."""
        description_match = Repository.objects.create(
            owner=self.owner, name='my-app', short_description='depends on redis',
        )
        name_match = Repository.objects.create(owner=self.owner, name='redis-cache')

        response = self.client.get('/explore/', {'q': 'redis'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories[0], name_match)
        self.assertEqual(repositories[1], description_match)

    def test_pagination_limits_results_per_page(self):
        """Search results are paginated."""
        for i in range(15):
            Repository.objects.create(owner=self.owner, name=f'repo-{i}')

        response = self.client.get('/explore/')

        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['repositories']), 12)

    def test_empty_state_when_no_public_repositories(self):
        """An empty-state message is shown when there are no public repositories."""
        response = self.client.get('/explore/')

        self.assertContains(response, 'No public repositories available yet.')

    def test_verified_publisher_badge_shown_for_verified_owner(self):
        """The Verified Publisher badge is shown when the repository's owner is verified."""
        self.owner.is_verified_publisher = True
        self.owner.save()
        Repository.objects.create(owner=self.owner, name='my-repo')

        response = self.client.get('/explore/')

        self.assertContains(response, 'Verified Publisher')

    def test_verified_publisher_badge_hidden_for_unverified_owner(self):
        """The Verified Publisher badge is not shown when the repository's owner isn't verified."""
        Repository.objects.create(owner=self.owner, name='my-repo')

        response = self.client.get('/explore/')

        self.assertNotContains(response, 'Verified Publisher')
