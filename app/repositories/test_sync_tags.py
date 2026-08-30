from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from .models import Repository, Tag
from .services import RegistryService


User = get_user_model()
DIGEST_A = 'sha256:' + 'a' * 64
DIGEST_B = 'sha256:' + 'b' * 64


class SyncTagsCommandTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='marija', password='secret-pass')
        self.repository = Repository.objects.create(owner=self.owner, name='my-app')

    def run_command(self, service, *args):
        with (
            patch(
                'repositories.management.commands.sync_tags.create_registry_token',
                return_value='signed-token',
            ),
            patch(
                'repositories.management.commands.sync_tags.RegistryService',
                return_value=service,
            ),
        ):
            call_command('sync_tags', *args, stdout=StringIO())

    def test_new_registry_tags_are_created(self):
        service = Mock()
        service.list_tags.return_value = ['latest', 'v1']
        service.get_manifest_metadata.side_effect = [
            {'digest': DIGEST_A, 'size': 100},
            {'digest': DIGEST_B, 'size': 200},
        ]

        self.run_command(service)

        self.assertTrue(Tag.objects.filter(
            repository=self.repository, name='latest', digest=DIGEST_A, size=100,
        ).exists())
        self.assertTrue(Tag.objects.filter(
            repository=self.repository, name='v1', digest=DIGEST_B, size=200,
        ).exists())

    def test_database_tags_missing_from_registry_are_deleted(self):
        Tag.objects.create(
            repository=self.repository, name='old', digest=DIGEST_A, size=100,
        )
        service = Mock()
        service.list_tags.return_value = []

        self.run_command(service)

        self.assertFalse(Tag.objects.filter(repository=self.repository, name='old').exists())

    def test_repo_flag_syncs_only_requested_repository(self):
        other_repository = Repository.objects.create(owner=self.owner, name='other-app')
        Tag.objects.create(
            repository=other_repository, name='keep-me', digest=DIGEST_A, size=100,
        )
        service = Mock()
        service.list_tags.return_value = []

        self.run_command(service, '--repo', 'marija/my-app')

        service.list_tags.assert_called_once_with('marija/my-app')
        self.assertTrue(Tag.objects.filter(repository=other_repository, name='keep-me').exists())

    def test_existing_tag_metadata_is_updated(self):
        tag = Tag.objects.create(
            repository=self.repository, name='latest', digest=DIGEST_A, size=100,
        )
        service = Mock()
        service.list_tags.return_value = ['latest']
        service.get_manifest_metadata.return_value = {'digest': DIGEST_B, 'size': 999}

        self.run_command(service)

        tag.refresh_from_db()
        self.assertEqual(tag.digest, DIGEST_B)
        self.assertEqual(tag.size, 999)


class RegistryManifestMetadataTest(TestCase):
    @patch('repositories.services.requests.request')
    def test_manifest_metadata_contains_digest_and_total_size(self, request):
        response = Mock()
        response.headers = {'Docker-Content-Digest': DIGEST_A}
        response.json.return_value = {
            'config': {'size': 10},
            'layers': [{'size': 100}, {'size': 200}],
        }
        response.raise_for_status.return_value = None
        request.return_value = response
        service = RegistryService(base_url='http://registry:5000', bearer_token='token')

        metadata = service.get_manifest_metadata('marija/my-app', 'latest')

        self.assertEqual(metadata, {'digest': DIGEST_A, 'size': 310})
        request.assert_called_once_with(
            'GET',
            'http://registry:5000/v2/marija/my-app/manifests/latest',
            auth=None,
            headers={
                'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
                'Authorization': 'Bearer token',
            },
        )
