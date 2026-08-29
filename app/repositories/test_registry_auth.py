import base64
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase

from .models import Repository
from .registry_auth import allowed_actions, parse_scope


User = get_user_model()


def basic_auth(username, password):
    value = base64.b64encode(f'{username}:{password}'.encode()).decode()
    return f'Basic {value}'


class RegistryAuthorizationTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='marija', password='secret-pass')
        self.other = User.objects.create_user(username='anja', password='secret-pass')
        self.admin = User.objects.create_user(
            username='admin', password='secret-pass', role=User.Role.ADMIN,
        )
        self.public_repo = Repository.objects.create(owner=self.owner, name='public')
        self.private_repo = Repository.objects.create(
            owner=self.owner, name='private', visibility=Repository.Visibility.PRIVATE,
        )
        self.official_repo = Repository.objects.create(
            owner=self.admin, name='nginx', is_official=True,
        )

    def actions(self, name, requested, user=None):
        return allowed_actions(name, requested, user)

    def test_registry_scope_is_parsed(self):
        self.assertEqual(
            parse_scope('repository:marija/public:pull,push'),
            ('repository', 'marija/public', ['pull', 'push']),
        )

    def test_anonymous_user_can_pull_public_repository(self):
        self.assertEqual(self.actions('marija/public', ['pull']), ['pull'])

    def test_anonymous_user_cannot_pull_private_repository(self):
        self.assertEqual(self.actions('marija/private', ['pull']), [])

    def test_owner_can_pull_private_repository(self):
        self.assertEqual(self.actions('marija/private', ['pull'], self.owner), ['pull'])

    def test_other_user_cannot_pull_private_repository(self):
        self.assertEqual(self.actions('marija/private', ['pull'], self.other), [])

    def test_push_requires_authentication(self):
        self.assertEqual(self.actions('marija/public', ['push']), [])

    def test_owner_can_push_to_own_repository(self):
        self.assertEqual(self.actions('marija/public', ['push'], self.owner), ['push'])

    def test_user_cannot_push_to_another_users_repository(self):
        self.assertEqual(self.actions('marija/public', ['push'], self.other), [])

    def test_admin_can_push_to_official_repository(self):
        self.assertEqual(self.actions('nginx', ['push'], self.admin), ['push'])

    def test_regular_user_cannot_push_to_official_repository(self):
        self.assertEqual(self.actions('nginx', ['push'], self.owner), [])

    def test_unknown_repository_is_rejected(self):
        self.assertEqual(self.actions('marija/missing', ['pull']), [])


class RegistryTokenViewTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='marija', password='secret-pass')
        Repository.objects.create(owner=self.owner, name='public')

    @patch('repositories.registry_views.token_response')
    def test_anonymous_token_grants_only_public_pull(self, token_response):
        token_response.return_value = HttpResponse(status=200)
        self.client.get('/registry/token/', {'scope': 'repository:marija/public:pull,push'})
        token_response.assert_called_once_with(
            '', 'uks-registry',
            [{'type': 'repository', 'name': 'marija/public', 'actions': ['pull']}],
        )

    @patch('repositories.registry_views.token_response')
    def test_owner_token_grants_pull_and_push(self, token_response):
        token_response.return_value = HttpResponse(status=200)
        self.client.get(
            '/registry/token/',
            {'scope': 'repository:marija/public:pull,push'},
            HTTP_AUTHORIZATION=basic_auth('marija', 'secret-pass'),
        )
        token_response.assert_called_once_with(
            'marija', 'uks-registry',
            [{'type': 'repository', 'name': 'marija/public', 'actions': ['pull', 'push']}],
        )

    def test_invalid_credentials_are_rejected(self):
        response = self.client.get(
            '/registry/token/', HTTP_AUTHORIZATION=basic_auth('marija', 'wrong-password'),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['WWW-Authenticate'], 'Basic realm="Registry Realm"')
