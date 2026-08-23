"""
Views for accounts app.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView
from django.views.generic.edit import FormView

from .forms import LoginForm, ProfileEditForm, RegistrationForm, StyledPasswordChangeForm

User = get_user_model()


class UserLoginView(LoginView):
    """Login page, restricted to non-authenticated users. Shares the auth.html template
    with RegisterView, rendering the login form in the active tab."""

    template_name = 'accounts/auth.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = context['form']
        context['register_form'] = RegistrationForm()
        context['active_tab'] = 'login'
        return context


class RegisterView(UserPassesTestMixin, CreateView):
    """Allows a new, non-authenticated user to create an account. Shares the auth.html
    template with UserLoginView, rendering the registration form in the active tab."""

    form_class = RegistrationForm
    template_name = 'accounts/auth.html'
    success_url = '/login/'

    def test_func(self):
        return not self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['register_form'] = context['form']
        context['login_form'] = LoginForm()
        context['active_tab'] = 'register'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Registration successful. You can now log in.')
        return response


class UserLogoutView(LoginRequiredMixin, LogoutView):
    """Logs the user out; only authenticated users may log out."""


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
    extra_context = {'subtitle': 'Update your account password.', 'back_url': reverse_lazy('profile')}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Password changed successfully.')
        return response


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated admins (ADMIN or SUPER_ADMIN)."""

    def test_func(self):
        return self.request.user.is_admin


class UserManagementView(AdminRequiredMixin, ListView):
    """Lets admins search users by username/email and manage their badges."""

    model = User
    template_name = 'accounts/user_management.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('username')
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(Q(username__icontains=query) | Q(email__icontains=query))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class ToggleUserBadgeView(AdminRequiredMixin, View):
    """Toggles a badge (verified publisher / sponsored OSS) on a target user."""

    BADGE_FIELDS = ('is_verified_publisher', 'is_sponsored_oss')

    def post(self, request, username):
        badge = request.POST.get('badge')
        if badge not in self.BADGE_FIELDS:
            raise Http404('Unknown badge.')

        user = get_object_or_404(User, username=username)
        setattr(user, badge, not getattr(user, badge))
        user.save(update_fields=[badge])

        messages.success(request, f"Updated {badge.replace('_', ' ')} badge for {user.username}.")

        url = reverse('user_management')
        query = request.POST.get('q', '')
        if query:
            url = f'{url}?q={query}'
        return redirect(url)
