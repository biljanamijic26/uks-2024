"""
Views for accounts app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.views.generic import CreateView

from .forms import LoginForm, RegistrationForm


class UserLoginView(LoginView):
    """Login page, restricted to non-authenticated users."""

    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LoginRequiredMixin, LogoutView):
    """Logs the user out; only authenticated users may log out."""


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
