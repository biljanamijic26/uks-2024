"""Integration tests for repository, tag, and Explore user flows."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from repositories.models import Repository, Tag

User = get_user_model()


class RepositoryIntegrationTestCase(TestCase):
    """Shared factories and helpers for repository integration tests."""

    password = 'StrongPass123!'

    def create_user(self, username='owner', **kwargs):
        return User.objects.create_user(username=username, password=self.password, **kwargs)

    def create_repository(self, owner=None, name='sample-repo', **kwargs):
        owner = owner or self.create_user()
        return Repository.objects.create(owner=owner, name=name, **kwargs)

    def create_tag(self, repository, name='latest', digest_character='a', size=1024):
        return Tag.objects.create(
            repository=repository,
            name=name,
            digest=f"sha256:{digest_character * 64}",
            size=size,
        )

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password=self.password))

    def repository_detail_url(self, repository):
        return reverse(
            'repository_detail',
            kwargs={'owner': repository.owner.username, 'name': repository.name},
        )


class RepositoryTagLifecycleTests(RepositoryIntegrationTestCase):
    def test_create_repository_add_view_and_delete_tag(self):
        owner = self.create_user()
        self.login(owner)

        create_repository_response = self.client.post(reverse('repository_create'), {
            'name': 'application',
            'short_description': 'Integration test repository',
            'visibility': Repository.Visibility.PUBLIC,
        })
        repository = Repository.objects.get(owner=owner, name='application')
        self.assertRedirects(create_repository_response, self.repository_detail_url(repository))

        tag_url = reverse('tag_create', kwargs={'owner': owner.username, 'name': repository.name})
        create_tag_response = self.client.post(tag_url, {
            'name': 'v1.0',
            'digest': f"sha256:{'a' * 64}",
            'size': 2048,
        })
        self.assertRedirects(create_tag_response, self.repository_detail_url(repository))
        tag = Tag.objects.get(repository=repository, name='v1.0')

        detail_response = self.client.get(self.repository_detail_url(repository), {'q': 'v1'})
        self.assertContains(detail_response, tag.name)
        self.assertContains(detail_response, tag.short_digest)

        delete_url = reverse('tag_delete', kwargs={
            'owner': owner.username,
            'name': repository.name,
            'tag_name': tag.name,
        })
        delete_response = self.client.post(delete_url)
        self.assertRedirects(delete_response, self.repository_detail_url(repository))
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())


class RepositoryExploreIntegrationTests(RepositoryIntegrationTestCase):
    def test_visibility_change_is_reflected_in_explore(self):
        owner = self.create_user()
        repository = self.create_repository(
            owner=owner,
            name='visibility-test',
            visibility=Repository.Visibility.PRIVATE,
        )
        self.login(owner)

        explore_before = self.client.get(reverse('explore'))
        self.assertNotIn(repository, explore_before.context['repositories'])

        edit_url = reverse('repository_edit', kwargs={'owner': owner.username, 'name': repository.name})
        update_response = self.client.post(edit_url, {
            'short_description': 'Now public',
            'visibility': Repository.Visibility.PUBLIC,
        })
        self.assertRedirects(update_response, self.repository_detail_url(repository))

        explore_after = self.client.get(reverse('explore'))
        self.assertIn(repository, explore_after.context['repositories'])
        self.assertContains(explore_after, repository.full_name)

    def test_official_repository_appears_with_badge_in_explore(self):
        admin = self.create_user(username='admin', role=User.Role.ADMIN)
        repository = self.create_repository(
            owner=admin,
            name='official-image',
            is_official=True,
        )

        response = self.client.get(reverse('explore'))

        self.assertIn(repository, response.context['repositories'])
        self.assertContains(response, 'Docker Official Image')

    def test_private_repository_is_not_visible_in_explore(self):
        repository = self.create_repository(
            name='private-image',
            visibility=Repository.Visibility.PRIVATE,
        )

        response = self.client.get(reverse('explore'))

        self.assertNotIn(repository, response.context['repositories'])
        self.assertNotContains(response, repository.full_name)


class TagSortingAndFilteringIntegrationTests(RepositoryIntegrationTestCase):
    def test_tag_sorting_and_filtering_end_to_end(self):
        owner = self.create_user()
        repository = self.create_repository(owner=owner)
        small = self.create_tag(repository, name='alpha', digest_character='a', size=100)
        large = self.create_tag(repository, name='beta-release', digest_character='b', size=300)
        medium = self.create_tag(repository, name='beta-stable', digest_character='c', size=200)
        now = timezone.now()
        Tag.objects.filter(pk=small.pk).update(created_at=now - timedelta(days=2))
        Tag.objects.filter(pk=large.pk).update(created_at=now - timedelta(days=1))
        Tag.objects.filter(pk=medium.pk).update(created_at=now)

        response = self.client.get(self.repository_detail_url(repository), {
            'q': 'beta',
            'sort': 'size',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['tags']), [large, medium])
        self.assertNotContains(response, small.name)
        self.assertEqual(response.context['tag_query'], 'beta')
        self.assertEqual(response.context['tag_sort'], 'size')

        name_response = self.client.get(self.repository_detail_url(repository), {'sort': 'name'})
        self.assertEqual(list(name_response.context['tags']), [small, large, medium])
