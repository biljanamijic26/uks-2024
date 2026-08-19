"""
Views for accounts app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from .forms import RegistrationForm


class RegisterView(UserPassesTestMixin, CreateView):
    """Allows a new, non-authenticated user to create an account."""

    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = '/login/'

    def test_func(self):
        return not self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Registration successful. You can now log in.')
        return response
