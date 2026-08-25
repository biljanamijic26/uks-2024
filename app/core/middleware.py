"""
Middleware for core app.
"""
import logging

logger = logging.getLogger('core.request')


class RequestLoggingMiddleware:
    """Logs every request's method, path, status code, and authenticated user (if any)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = request.user.username if request.user.is_authenticated else None
        logger.info(
            f'{request.method} {request.path} {response.status_code}',
            extra={'user': user, 'path': request.path, 'method': request.method},
        )

        return response
