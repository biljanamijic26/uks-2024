"""
Tests for repositories app.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from .models import Repository, Tag

User = get_user_model()


class RepositoryModelTest(TestCase):
    """Test cases for Repository model."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')

    def test_create_repository_with_valid_data(self):
        """A repository can be created with valid data."""
        repo = Repository.objects.create(
            owner=self.owner,
            name='my-repo',
            short_description='A test repository',
        )
        self.assertEqual(repo.name, 'my-repo')
        self.assertEqual(repo.owner, self.owner)
        self.assertEqual(repo.visibility, Repository.Visibility.PUBLIC)
        self.assertFalse(repo.is_official)

    def test_full_name_for_regular_repo(self):
        """full_name returns 'owner/name' for a non-official repository."""
        repo = Repository.objects.create(owner=self.owner, name='my-repo')
        self.assertEqual(repo.full_name, 'owner/my-repo')

    def test_full_name_for_official_repo(self):
        """full_name returns just 'name' for an official repository."""
        repo = Repository.objects.create(owner=self.owner, name='nginx', is_official=True)
        self.assertEqual(repo.full_name, 'nginx')

    def test_owner_name_uniqueness_constraint(self):
        """The same owner cannot have two repositories with the same name."""
        Repository.objects.create(owner=self.owner, name='my-repo')

        with self.assertRaises(IntegrityError):
            Repository.objects.create(owner=self.owner, name='my-repo')

    def test_different_owners_can_use_same_name(self):
        """Two different owners can each have a repository with the same name."""
        other_owner = User.objects.create_user(username='other', password='pass12345')
        Repository.objects.create(owner=self.owner, name='my-repo')

        repo = Repository.objects.create(owner=other_owner, name='my-repo')
        self.assertEqual(repo.name, 'my-repo')

    def test_invalid_name_with_uppercase_fails_validation(self):
        """Names with uppercase letters fail model validation."""
        repo = Repository(owner=self.owner, name='My-Repo')
        with self.assertRaises(Exception):
            repo.full_clean()

    def test_invalid_name_with_spaces_fails_validation(self):
        """Names with spaces fail model validation."""
        repo = Repository(owner=self.owner, name='my repo')
        with self.assertRaises(Exception):
            repo.full_clean()


class TagModelTest(TestCase):
    """Test cases for Tag model."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.repo = Repository.objects.create(owner=self.owner, name='my-repo')

    def test_create_tag_with_valid_data(self):
        """A tag can be created with valid data."""
        tag = Tag.objects.create(
            repository=self.repo,
            name='latest',
            digest='sha256:' + 'a' * 64,
            size=1024,
        )
        self.assertEqual(tag.name, 'latest')
        self.assertEqual(tag.repository, self.repo)
        self.assertEqual(tag.size, 1024)

    def test_full_name_returns_correct_format(self):
        """full_name returns 'repository_full_name:tag_name'."""
        tag = Tag.objects.create(
            repository=self.repo,
            name='v1.0.0',
            digest='sha256:' + 'a' * 64,
            size=1024,
        )
        self.assertEqual(tag.full_name, 'owner/my-repo:v1.0.0')

    def test_short_digest_truncates_correctly(self):
        """short_digest returns the first 12 characters of the hash part."""
        digest = 'sha256:' + 'abcdef1234567890' * 4
        tag = Tag.objects.create(repository=self.repo, name='latest', digest=digest, size=1024)
        self.assertEqual(tag.short_digest, 'abcdef123456')

    def test_size_display_returns_human_readable_format(self):
        """size_display converts bytes into a human-readable string."""
        cases = [
            (512, '512 B'),
            (2048, '2.0 KB'),
            (5 * 1024 * 1024, '5.0 MB'),
            (int(1.2 * 1024 * 1024 * 1024), '1.2 GB'),
        ]
        for size, expected in cases:
            tag = Tag(repository=self.repo, name='latest', digest='sha256:' + 'a' * 64, size=size)
            self.assertEqual(tag.size_display, expected)

    def test_uniqueness_constraint_prevents_duplicate_tag_names(self):
        """The same repository cannot have two tags with the same name."""
        Tag.objects.create(repository=self.repo, name='latest', digest='sha256:' + 'a' * 64, size=1024)

        with self.assertRaises(IntegrityError):
            Tag.objects.create(repository=self.repo, name='latest', digest='sha256:' + 'b' * 64, size=2048)


class RepositoryListViewTest(TestCase):
    """Test cases for the 'my repositories' list view."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other_user = User.objects.create_user(username='other', password='pass12345')

    def test_lists_only_users_repositories(self):
        """The list page shows only repositories owned by the logged-in user."""
        Repository.objects.create(owner=self.owner, name='my-repo')
        Repository.objects.create(owner=self.owner, name='another-repo')
        self.client.login(username='owner', password='pass12345')

        response = self.client.get('/repositories/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['repositories']), 2)

    def test_does_not_show_other_users_repositories(self):
        """The list page does not include repositories owned by other users."""
        Repository.objects.create(owner=self.other_user, name='not-mine')
        self.client.login(username='owner', password='pass12345')

        response = self.client.get('/repositories/')

        self.assertEqual(len(response.context['repositories']), 0)
        self.assertNotContains(response, 'not-mine')

    def test_unauthenticated_user_redirected_to_login(self):
        """An anonymous user is redirected to login when visiting the list page."""
        response = self.client.get('/repositories/')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_sorted_by_most_recently_updated(self):
        """Repositories are ordered by most recently updated first."""
        older = Repository.objects.create(owner=self.owner, name='older-repo')
        newer = Repository.objects.create(owner=self.owner, name='newer-repo')
        older.short_description = 'touched'
        older.save()
        self.client.login(username='owner', password='pass12345')

        response = self.client.get('/repositories/')

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories[0], older)
        self.assertEqual(repositories[1], newer)

    def test_empty_state_when_no_repositories(self):
        """An empty-state message is shown when the user has no repositories."""
        self.client.login(username='owner', password='pass12345')

        response = self.client.get('/repositories/')

        self.assertContains(response, "don't have any repositories")


class RepositoryViewsTest(TestCase):
    """Test cases for repository CRUD views."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other_user = User.objects.create_user(username='other', password='pass12345')

    def test_create_repository(self):
        """An authenticated user can create a repository they own."""
        self.client.login(username='owner', password='pass12345')

        response = self.client.post('/repositories/new/', {
            'name': 'my-repo',
            'short_description': 'A test repository',
            'visibility': Repository.Visibility.PUBLIC,
        })

        self.assertRedirects(response, '/repositories/owner/my-repo/')
        repo = Repository.objects.get(owner=self.owner, name='my-repo')
        self.assertEqual(repo.short_description, 'A test repository')

    def test_unauthenticated_user_cannot_create_repository(self):
        """An anonymous user is redirected to login when trying to create a repository."""
        response = self.client.get('/repositories/new/')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_view_own_repository(self):
        """The owner can view their own repository's detail page."""
        Repository.objects.create(owner=self.owner, name='my-repo', short_description='Hello')
        self.client.login(username='owner', password='pass12345')

        response = self.client.get('/repositories/owner/my-repo/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'my-repo')
        self.assertContains(response, 'Hello')

    def test_public_repository_visible_to_everyone(self):
        """A public repository is visible to anonymous users."""
        Repository.objects.create(owner=self.owner, name='public-repo', visibility=Repository.Visibility.PUBLIC)

        response = self.client.get('/repositories/owner/public-repo/')

        self.assertEqual(response.status_code, 200)

    def test_private_repository_not_visible_to_others(self):
        """A private repository returns 404 for anyone but its owner."""
        Repository.objects.create(owner=self.owner, name='private-repo', visibility=Repository.Visibility.PRIVATE)
        self.client.login(username='other', password='pass12345')

        response = self.client.get('/repositories/owner/private-repo/')

        self.assertEqual(response.status_code, 404)

    def test_update_repository(self):
        """The owner can update a repository's description and visibility."""
        Repository.objects.create(owner=self.owner, name='my-repo', short_description='Old')
        self.client.login(username='owner', password='pass12345')

        response = self.client.post('/repositories/owner/my-repo/edit/', {
            'short_description': 'Updated description',
            'visibility': Repository.Visibility.PRIVATE,
        })

        self.assertRedirects(response, '/repositories/owner/my-repo/')
        repo = Repository.objects.get(owner=self.owner, name='my-repo')
        self.assertEqual(repo.short_description, 'Updated description')
        self.assertEqual(repo.visibility, Repository.Visibility.PRIVATE)

    def test_delete_repository(self):
        """The owner can delete their own repository via the confirmation page."""
        Repository.objects.create(owner=self.owner, name='my-repo')
        self.client.login(username='owner', password='pass12345')

        response = self.client.post('/repositories/owner/my-repo/delete/')

        self.assertRedirects(response, '/repositories/')
        self.assertFalse(Repository.objects.filter(owner=self.owner, name='my-repo').exists())

    def test_cannot_edit_other_users_repository(self):
        """A non-owner cannot edit another user's repository."""
        Repository.objects.create(owner=self.owner, name='my-repo', short_description='Old')
        self.client.login(username='other', password='pass12345')

        response = self.client.post('/repositories/owner/my-repo/edit/', {
            'short_description': 'Hacked',
            'visibility': Repository.Visibility.PUBLIC,
        })

        self.assertEqual(response.status_code, 403)
        repo = Repository.objects.get(owner=self.owner, name='my-repo')
        self.assertEqual(repo.short_description, 'Old')

    def test_cannot_delete_other_users_repository(self):
        """A non-owner cannot delete another user's repository."""
        Repository.objects.create(owner=self.owner, name='my-repo')
        self.client.login(username='other', password='pass12345')

        response = self.client.post('/repositories/owner/my-repo/delete/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Repository.objects.filter(owner=self.owner, name='my-repo').exists())
