"""Docker Distribution token service backed by Django."""

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .registry_auth import allowed_actions, authenticate_header, parse_scope
from .registry_tokens import create_registry_token


def token_response(subject, service, access):
    """Create a short-lived JWT accepted by the Distribution registry."""
    token = create_registry_token(subject, access, service)
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
