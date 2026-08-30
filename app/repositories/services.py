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

    def __init__(self, base_url=None, username=None, password=None, bearer_token=None):
        self.base_url = (base_url or os.environ.get('REGISTRY_URL', '')).rstrip('/')
        self.username = username or os.environ.get('REGISTRY_USERNAME')
        self.password = password or os.environ.get('REGISTRY_PASSWORD')
        self.auth = (self.username, self.password)
        self.bearer_token = bearer_token

    def _request(self, method, path, **kwargs):
        url = f'{self.base_url}{path}'
        if self.bearer_token:
            headers = kwargs.setdefault('headers', {})
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        try:
            auth = None if self.bearer_token else self.auth
            response = requests.request(method, url, auth=auth, **kwargs)
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

    def get_manifest_metadata(self, repo_name, tag):
        """Return the manifest digest and total compressed image size."""
        response = self._request(
            'GET',
            f'/v2/{repo_name}/manifests/{tag}',
            headers={'Accept': MANIFEST_ACCEPT_HEADER},
        )
        manifest = response.json()
        size = manifest.get('config', {}).get('size', 0)
        size += sum(layer.get('size', 0) for layer in manifest.get('layers', []))
        return {
            'digest': response.headers.get('Docker-Content-Digest'),
            'size': size,
        }

    def delete_manifest(self, repo_name, digest):
        """Delete a manifest from a repository by its digest."""
        self._request(
            'DELETE',
            f'/v2/{repo_name}/manifests/{digest}',
            headers={'Accept': MANIFEST_ACCEPT_HEADER},
        )
        return True
