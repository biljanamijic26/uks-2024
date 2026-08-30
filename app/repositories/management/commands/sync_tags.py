"""Synchronize Registry tags and manifest metadata with the Django database."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from repositories.models import Repository, Tag
from repositories.registry_tokens import create_registry_token
from repositories.services import RegistryError, RegistryService


class Command(BaseCommand):
    help = 'Synchronize tags from the Distribution registry.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repo',
            help='Sync one repository by Registry name, for example marija/my-app or nginx.',
        )

    def handle(self, *args, **options):
        repositories = list(Repository.objects.select_related('owner').all())
        requested_repo = options.get('repo')
        if requested_repo:
            repositories = [repository for repository in repositories if repository.full_name == requested_repo]
            if not repositories:
                raise CommandError(f'Repository "{requested_repo}" does not exist.')

        total_created = 0
        total_updated = 0
        total_deleted = 0
        for repository in repositories:
            created, updated, deleted = self._sync_repository(repository)
            total_created += created
            total_updated += updated
            total_deleted += deleted

        self.stdout.write(self.style.SUCCESS(
            f'Synchronized {len(repositories)} repositories: '
            f'{total_created} created, {total_updated} updated, {total_deleted} deleted.',
        ))

    @transaction.atomic
    def _sync_repository(self, repository):
        registry_name = repository.full_name
        access = [{'type': 'repository', 'name': registry_name, 'actions': ['pull']}]
        token = create_registry_token('sync-tags', access, settings.REGISTRY_AUTH_SERVICE)
        service = RegistryService(bearer_token=token)

        try:
            registry_tags = service.list_tags(registry_name)
            created_count = 0
            updated_count = 0
            for tag_name in registry_tags:
                metadata = service.get_manifest_metadata(registry_name, tag_name)
                if not metadata['digest']:
                    raise RegistryError(f'Missing digest for {registry_name}:{tag_name}')
                _, created = Tag.objects.update_or_create(
                    repository=repository,
                    name=tag_name,
                    defaults={'digest': metadata['digest'], 'size': metadata['size']},
                )
                created_count += int(created)
                updated_count += int(not created)

            deleted_count, _ = repository.tags.exclude(name__in=registry_tags).delete()
        except RegistryError as exc:
            raise CommandError(f'Could not sync {registry_name}: {exc}') from exc

        self.stdout.write(
            f'{registry_name}: {created_count} created, {updated_count} updated, {deleted_count} deleted.',
        )
        return created_count, updated_count, deleted_count
