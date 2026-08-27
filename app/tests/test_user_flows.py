"""
Integration tests for complete user flows across multiple components.

Unlike the per-app unit tests, these exercise a full sequence of
requests through the Django test client, the way a real user would
move through the site.
"""
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from repositories.models import Repository

User = get_user_model()


class RegistrationLoginCreateRepositoryFlowTest(TransactionTestCase):
    """Register -> log in -> create a repository -> view it."""

    def test_full_registration_to_repository_view_flow(self):
        register_response = self.client.post('/register/', {
            'username': 'flowuser',
            'email': 'flowuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(register_response, '/login/')
        user = User.objects.get(username='flowuser')
        self.assertEqual(user.role, User.Role.USER)

        login_response = self.client.post('/login/', {
            'username': 'flowuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(login_response, '/')
        self.assertIn('_auth_user_id', self.client.session)

        create_response = self.client.post('/repositories/new/', {
            'name': 'my-first-repo',
            'short_description': 'Created during the integration flow.',
            'visibility': Repository.Visibility.PUBLIC,
        })
        self.assertRedirects(create_response, '/repositories/flowuser/my-first-repo/')
        repo = Repository.objects.get(owner=user, name='my-first-repo')
        self.assertEqual(repo.short_description, 'Created during the integration flow.')

        detail_response = self.client.get('/repositories/flowuser/my-first-repo/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'my-first-repo')
        self.assertContains(detail_response, 'Created during the integration flow.')

    def test_flow_stops_when_login_credentials_are_wrong(self):
        """If registration succeeds but login fails, the user never reaches repository creation."""
        self.client.post('/register/', {
            'username': 'flowuser2',
            'email': 'flowuser2@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        login_response = self.client.post('/login/', {
            'username': 'flowuser2',
            'password': 'WrongPassword!',
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

        create_response = self.client.get('/repositories/new/')
        self.assertEqual(create_response.status_code, 302)
        self.assertTrue(create_response.url.startswith('/login/'))


class OfficialRepositoryVisibleInExploreFlowTest(TransactionTestCase):
    """Admin creates an official repository -> it shows up in Explore."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='siteadmin', password='AdminPass123!', role=User.Role.ADMIN,
        )

    def test_official_repository_created_by_admin_appears_in_explore(self):
        explore_before = self.client.get('/explore/')
        self.assertEqual(len(explore_before.context['repositories']), 0)

        self.client.login(username='siteadmin', password='AdminPass123!')
        create_response = self.client.post('/repositories/official/new/', {
            'name': 'nginx',
            'short_description': 'Official build of nginx.',
            'visibility': Repository.Visibility.PUBLIC,
        })
        self.assertRedirects(create_response, '/repositories/siteadmin/nginx/')
        repo = Repository.objects.get(name='nginx')
        self.assertTrue(repo.is_official)

        self.client.logout()
        explore_after = self.client.get('/explore/')
        repositories = list(explore_after.context['repositories'])
        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0], repo)
        self.assertContains(explore_after, 'Docker Official Image')

    def test_private_official_repository_does_not_appear_in_explore(self):
        self.client.login(username='siteadmin', password='AdminPass123!')

        self.client.post('/repositories/official/new/', {
            'name': 'internal-tool',
            'short_description': 'Not meant to be public.',
            'visibility': Repository.Visibility.PRIVATE,
        })

        self.client.logout()
        explore_response = self.client.get('/explore/')
        self.assertEqual(len(explore_response.context['repositories']), 0)


class ExploreSearchFlowTest(TransactionTestCase):
    """A user searches Explore and only the matching repositories are returned."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.matching_repo = Repository.objects.create(
            owner=self.owner, name='nginx-server', short_description='A fast web server',
        )
        self.other_repo = Repository.objects.create(
            owner=self.owner, name='redis-cache', short_description='An in-memory data store',
        )

    def test_search_returns_only_matching_repositories(self):
        response = self.client.get('/explore/', {'q': 'nginx'})

        repositories = list(response.context['repositories'])
        self.assertEqual(repositories, [self.matching_repo])
        self.assertContains(response, 'nginx-server')
        self.assertNotContains(response, 'redis-cache')

    def test_search_with_no_matches_shows_empty_results(self):
        response = self.client.get('/explore/', {'q': 'postgres'})

        self.assertEqual(len(response.context['repositories']), 0)

    def test_search_excludes_private_repositories_even_when_name_matches(self):
        Repository.objects.create(
            owner=self.owner, name='nginx-private', visibility=Repository.Visibility.PRIVATE,
        )

        response = self.client.get('/explore/', {'q': 'nginx'})

        names = [repo.name for repo in response.context['repositories']]
        self.assertIn('nginx-server', names)
        self.assertNotIn('nginx-private', names)


class SuperAdminCreatesAdminFlowTest(TransactionTestCase):
    """Super admin creates a new admin -> the new admin can log in."""

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='rootadmin', password='RootPass123!', role=User.Role.SUPER_ADMIN,
        )

    def test_new_admin_can_log_in_with_chosen_password(self):
        self.client.login(username='rootadmin', password='RootPass123!')

        create_response = self.client.post('/admin-panel/create-admin/', {
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'ChosenPass123!',
        })
        self.assertEqual(create_response.status_code, 302)
        new_admin = User.objects.get(username='newadmin')
        self.assertEqual(new_admin.role, User.Role.ADMIN)
        self.assertTrue(new_admin.must_change_password)

        self.client.logout()
        login_response = self.client.post('/login/', {
            'username': 'newadmin',
            'password': 'ChosenPass123!',
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.url, '/')
        self.assertIn('_auth_user_id', self.client.session)

        home_response = self.client.get('/')
        self.assertRedirects(home_response, '/password-change/')

    def test_new_admin_can_manage_official_repositories_after_first_login(self):
        self.client.login(username='rootadmin', password='RootPass123!')
        self.client.post('/admin-panel/create-admin/', {
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'ChosenPass123!',
        })
        self.client.logout()

        self.client.login(username='newadmin', password='ChosenPass123!')
        self.client.post('/password-change/', {
            'old_password': 'ChosenPass123!',
            'new_password1': 'FreshPass456!',
            'new_password2': 'FreshPass456!',
        })

        create_response = self.client.post('/repositories/official/new/', {
            'name': 'redis',
            'short_description': 'Official build of redis.',
            'visibility': Repository.Visibility.PUBLIC,
        })
        self.assertRedirects(create_response, '/repositories/newadmin/redis/')
        self.assertTrue(Repository.objects.get(name='redis').is_official)
