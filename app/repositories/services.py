"""
Service for communicating with the Distribution registry via its HTTP API.
"""
import os

import requests

MANIFEST_ACCEPT_HEADER = 'application/vnd.docker.distribution.manifest.v2+json'


class RegistryError(Exception):
    """Raised when the registry cannot be reached or returns an error."""


class RegistryService:
    """Client for the Distribution registry's HTTP API (Registry V2)."""

    def __init__(self, base_url=None, username=None, password=None):
        self.base_url = (base_url or os.environ.get('REGISTRY_URL', '')).rstrip('/')
        self.username = username or os.environ.get('REGISTRY_USERNAME')
        self.password = password or os.environ.get('REGISTRY_PASSWORD')
        self.auth = (self.username, self.password)

    def _request(self, method, path, **kwargs):
        url = f'{self.base_url}{path}'
        try:
            response = requests.request(method, url, auth=self.auth, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RegistryError(f'Registry request failed: {exc}') from exc
        return response

    def list_repositories(self):
        """Return the list of repository names in the registry catalog."""
        response = self._request('GET', '/v2/_catalog')
        return response.json().get('repositories', [])

    def list_tags(self, repo_name):
        """Return the list of tags for a given repository."""
        response = self._request('GET', f'/v2/{repo_name}/tags/list')
        return response.json().get('tags', []) or []

    def get_manifest(self, repo_name, tag):
        """Return the manifest for a given repository and tag."""
        response = self._request(
            'GET',
            f'/v2/{repo_name}/manifests/{tag}',
            headers={'Accept': MANIFEST_ACCEPT_HEADER},
        )
        return response.json()

    def delete_manifest(self, repo_name, digest):
        """Delete a manifest from a repository by its digest."""
        self._request(
            'DELETE',
            f'/v2/{repo_name}/manifests/{digest}',
            headers={'Accept': MANIFEST_ACCEPT_HEADER},
        )
        return True
