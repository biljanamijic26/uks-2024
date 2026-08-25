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

        # "Verified Publisher" also appears once in the filter checkbox label.
        self.assertContains(response, 'Verified Publisher', count=2)

    def test_verified_publisher_badge_hidden_for_unverified_owner(self):
        """The Verified Publisher badge is not shown when the repository's owner isn't verified."""
        Repository.objects.create(owner=self.owner, name='my-repo')

        response = self.client.get('/explore/')

        # "Verified Publisher" still appears once, from the filter checkbox label.
        self.assertContains(response, 'Verified Publisher', count=1)

    def test_official_image_badge_shown_for_official_repository(self):
        """The 'Docker Official Image' badge is shown for an official repository."""
        Repository.objects.create(owner=self.owner, name='nginx', is_official=True)

        response = self.client.get('/explore/')

        self.assertContains(response, 'Docker Official Image')

    def test_official_repositories_are_ranked_first(self):
        """Official repositories appear before regular ones, regardless of update recency."""
        regular = Repository.objects.create(owner=self.owner, name='regular-repo')
        official = Repository.objects.create(owner=self.owner, name='nginx', is_official=True)
        regular.save()  # bump updated_at so it's more recently updated than the official repo

        response = self.client.get('/explore/')

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories[0], official)
        self.assertEqual(repositories[1], regular)

    def test_official_filter_returns_only_official_repositories(self):
        """The 'official' filter excludes non-official repositories."""
        Repository.objects.create(owner=self.owner, name='regular-repo')
        official = Repository.objects.create(owner=self.owner, name='nginx', is_official=True)

        response = self.client.get('/explore/', {'official': '1'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories, [official])

    def test_verified_publisher_filter_returns_only_repos_from_verified_owners(self):
        """The 'verified' filter excludes repositories owned by non-verified publishers."""
        verified_owner = User.objects.create_user(
            username='verified-owner', password='pass12345', is_verified_publisher=True,
        )
        verified_repo = Repository.objects.create(owner=verified_owner, name='verified-repo')
        Repository.objects.create(owner=self.owner, name='regular-repo')

        response = self.client.get('/explore/', {'verified': '1'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories, [verified_repo])

    def test_sponsored_oss_filter_returns_only_repos_from_sponsored_owners(self):
        """The 'sponsored' filter excludes repositories owned by non-sponsored publishers."""
        sponsored_owner = User.objects.create_user(
            username='sponsored-owner', password='pass12345', is_sponsored_oss=True,
        )
        sponsored_repo = Repository.objects.create(owner=sponsored_owner, name='sponsored-repo')
        Repository.objects.create(owner=self.owner, name='regular-repo')

        response = self.client.get('/explore/', {'sponsored': '1'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories, [sponsored_repo])

    def test_filters_combine_with_and_logic(self):
        """Multiple active filters are combined, requiring all to match."""
        verified_owner = User.objects.create_user(
            username='verified-owner', password='pass12345', is_verified_publisher=True,
        )
        official_and_verified = Repository.objects.create(
            owner=verified_owner, name='nginx', is_official=True,
        )
        Repository.objects.create(owner=verified_owner, name='non-official-repo')
        Repository.objects.create(owner=self.owner, name='non-verified-official', is_official=True)

        response = self.client.get('/explore/', {'official': '1', 'verified': '1'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories, [official_and_verified])

    def test_sort_by_updated_orders_most_recently_updated_first(self):
        """The 'updated' sort orders repositories by most recently updated, ignoring official status."""
        older = Repository.objects.create(owner=self.owner, name='older-repo', is_official=True)
        newer = Repository.objects.create(owner=self.owner, name='newer-repo')
        older.save()  # bump older's updated_at past newer's, despite being official

        response = self.client.get('/explore/', {'sort': 'updated'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories[0], older)
        self.assertEqual(repositories[1], newer)

    def test_sort_by_name_ascending(self):
        """The 'name_asc' sort orders repositories alphabetically from A to Z."""
        Repository.objects.create(owner=self.owner, name='zebra-repo')
        Repository.objects.create(owner=self.owner, name='alpha-repo')

        response = self.client.get('/explore/', {'sort': 'name_asc'})

        names = [repo.name for repo in response.context['repositories']]
        self.assertEqual(names, ['alpha-repo', 'zebra-repo'])

    def test_sort_by_name_descending(self):
        """The 'name_desc' sort orders repositories alphabetically from Z to A."""
        Repository.objects.create(owner=self.owner, name='zebra-repo')
        Repository.objects.create(owner=self.owner, name='alpha-repo')

        response = self.client.get('/explore/', {'sort': 'name_desc'})

        names = [repo.name for repo in response.context['repositories']]
        self.assertEqual(names, ['zebra-repo', 'alpha-repo'])

    def test_invalid_sort_falls_back_to_relevance(self):
        """An unrecognized sort value falls back to the default relevance ordering."""
        response = self.client.get('/explore/', {'sort': 'not-a-real-option'})

        self.assertEqual(response.context['sort'], 'relevance')

    def test_active_filter_count_reflects_selected_filters(self):
        """The active filter count reflects how many of the three filters are enabled."""
        response = self.client.get('/explore/', {'official': '1', 'sponsored': '1'})

        self.assertEqual(response.context['active_filter_count'], 2)

    def test_active_filter_count_is_zero_by_default(self):
        """The active filter count is zero when no filters are selected."""
        response = self.client.get('/explore/')

        self.assertEqual(response.context['active_filter_count'], 0)

    def test_clear_filters_link_hidden_when_no_filters_active(self):
        """The clear filters link isn't shown when no filters are active."""
        response = self.client.get('/explore/')

        self.assertNotContains(response, 'id="clear-filters-link"')

    def test_clear_filters_link_shown_when_filters_active(self):
        """The clear filters link is shown once at least one filter is active."""
        response = self.client.get('/explore/', {'official': '1'})

        self.assertContains(response, 'id="clear-filters-link"')

    def test_pagination_links_preserve_filters_and_sort(self):
        """Pagination links retain the active filters and sort in their query string."""
        for i in range(15):
            Repository.objects.create(owner=self.owner, name=f'repo-{i}', is_official=True)

        response = self.client.get('/explore/', {'official': '1', 'sort': 'name_asc'})

        self.assertContains(response, 'official=1')
        self.assertContains(response, 'sort=name_asc')
