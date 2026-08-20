"""
Tests for repositories app.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from .models import Repository

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
