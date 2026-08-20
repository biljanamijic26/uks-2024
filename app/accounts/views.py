"""
Views for accounts app.
"""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView
from django.views.generic.edit import FormView

from .forms import LoginForm, ProfileEditForm, RegistrationForm, StyledPasswordChangeForm


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


class ForcedPasswordChangeView(LoginRequiredMixin, FormView):
    """Requires a logged-in user to set a new password before continuing."""

    form_class = StyledPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('home')
    extra_context = {'subtitle': 'You must set a new password before continuing.'}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'Password changed successfully.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    """Displays the logged-in user's own profile information."""

    template_name = 'accounts/profile.html'


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Allows the logged-in user to edit their own email address."""

    form_class = ProfileEditForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Profile updated successfully.')
        return response


class ProfilePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Allows the logged-in user to change their own password from their profile."""

    form_class = StyledPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('profile')
    extra_context = {'subtitle': 'Update your account password.'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Password changed successfully.')
        return response
