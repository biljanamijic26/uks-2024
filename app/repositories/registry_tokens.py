"""JWT creation helpers for trusted Registry clients and the token endpoint."""

import base64
import hashlib
import time
import uuid

import jwt
from cryptography.hazmat.primitives import serialization
from django.conf import settings


def signing_key_id(private_key):
    """Build the libtrust-compatible key ID expected by Distribution."""
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    encoded = base64.b32encode(hashlib.sha256(public_der).digest()[:30]).decode().rstrip('=')
    return ':'.join(encoded[index:index + 4] for index in range(0, len(encoded), 4))


def create_registry_token(subject, access, service=None):
    """Return a short-lived token for the supplied Registry access entries."""
    now = int(time.time())
    with open(settings.REGISTRY_AUTH_KEY_PATH, encoding='utf-8') as key_file:
        private_key = key_file.read()
    claims = {
        'iss': settings.REGISTRY_AUTH_ISSUER,
        'sub': subject,
        'aud': service or settings.REGISTRY_AUTH_SERVICE,
        'exp': now + settings.REGISTRY_TOKEN_TTL,
        'nbf': now - 5,
        'iat': now,
        'jti': str(uuid.uuid4()),
        'access': access,
    }
    return jwt.encode(
        claims, private_key, algorithm='RS256',
        headers={'kid': signing_key_id(private_key), 'typ': 'JWT'},
    )
