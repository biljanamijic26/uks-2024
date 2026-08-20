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
