"""
Middleware for accounts app.
"""
from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_URL_NAMES = ('login', 'logout', 'password_change')


class ForcePasswordChangeMiddleware:
    """Forces users with must_change_password=True to change their password
    before accessing any other page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._requires_redirect(request):
            return redirect('password_change')
        return self.get_response(request)

    def _requires_redirect(self, request):
        user = request.user
        if not user.is_authenticated or not user.must_change_password:
            return False
        if request.path.startswith('/static/'):
            return False
        exempt_urls = {reverse(name) for name in EXEMPT_URL_NAMES}
        return request.path not in exempt_urls
