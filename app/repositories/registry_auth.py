"""Token authorization policy for the Distribution registry."""

import base64
import binascii
from django.contrib.auth import authenticate

from .models import Repository


def credentials_from_header(header):
    """Return username and password from an HTTP Basic authorization header."""
    try:
        scheme, encoded = header.split(' ', 1)
        if scheme.lower() != 'basic':
            return None
        decoded = base64.b64decode(encoded, validate=True).decode('utf-8')
        return tuple(decoded.split(':', 1))
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def authenticate_header(header):
    """Authenticate Registry token-service credentials, if supplied."""
    credentials = credentials_from_header(header)
    if credentials is None:
        return None
    return authenticate(username=credentials[0], password=credentials[1])


def find_repository(registry_name):
    """Resolve a registry name to an official or user-owned repository."""
    parts = registry_name.split('/')
    if len(parts) == 1:
        return Repository.objects.filter(name=parts[0], is_official=True).select_related('owner').first()
    if len(parts) == 2:
        return Repository.objects.filter(
            owner__username__iexact=parts[0],
            name=parts[1],
            is_official=False,
        ).select_related('owner').first()
    return None


def allowed_actions(repository_name, requested_actions, user=None):
    """Return the requested Registry actions that the principal may perform."""
    repository = find_repository(repository_name)
    if repository is None:
        return []

    allowed = set()
    if repository.visibility == Repository.Visibility.PUBLIC or user == repository.owner:
        allowed.add('pull')
    if user is not None:
        if repository.is_official and user.is_admin:
            allowed.add('push')
        elif not repository.is_official and user == repository.owner:
            allowed.add('push')
    return [action for action in requested_actions if action in allowed]


def parse_scope(scope):
    """Parse ``repository:name:pull,push`` into its component parts."""
    parts = scope.split(':', 2)
    if len(parts) != 3 or parts[0] != 'repository':
        return None
    return parts[0], parts[1], [action for action in parts[2].split(',') if action]
