"""Docker Distribution token service backed by Django."""

import base64
import hashlib
import time
import uuid

import jwt
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .registry_auth import allowed_actions, authenticate_header, parse_scope


def signing_key_id(private_key):
    """Build the libtrust-compatible key ID expected by Distribution."""
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    encoded = base64.b32encode(hashlib.sha256(public_der).digest()[:30]).decode().rstrip('=')
    return ':'.join(encoded[index:index + 4] for index in range(0, len(encoded), 4))


def token_response(subject, service, access):
    """Create a short-lived JWT accepted by the Distribution registry."""
    now = int(time.time())
    with open(settings.REGISTRY_AUTH_KEY_PATH, encoding='utf-8') as key_file:
        private_key = key_file.read()
    claims = {
        'iss': settings.REGISTRY_AUTH_ISSUER,
        'sub': subject,
        'aud': service,
        'exp': now + settings.REGISTRY_TOKEN_TTL,
        'nbf': now - 5,
        'iat': now,
        'jti': str(uuid.uuid4()),
        'access': access,
    }
    token = jwt.encode(
        claims, private_key, algorithm='RS256',
        headers={'kid': signing_key_id(private_key), 'typ': 'JWT'},
    )
    return JsonResponse({'token': token, 'access_token': token, 'expires_in': settings.REGISTRY_TOKEN_TTL})


@csrf_exempt
@require_GET
def registry_token(request):
    """Issue a token containing only actions allowed by the Django policy."""
    authorization = request.headers.get('Authorization', '')
    user = authenticate_header(authorization)
    if authorization and user is None:
        response = JsonResponse({'detail': 'Invalid username or password.'}, status=401)
        response['WWW-Authenticate'] = 'Basic realm="Registry Realm"'
        return response

    access = []
    for raw_scope in request.GET.getlist('scope'):
        scope = parse_scope(raw_scope)
        if scope is None:
            continue
        resource_type, name, requested = scope
        actions = allowed_actions(name, requested, user)
        if actions:
            access.append({'type': resource_type, 'name': name, 'actions': actions})

    subject = user.username if user else ''
    service = request.GET.get('service', settings.REGISTRY_AUTH_SERVICE)
    return token_response(subject, service, access)
