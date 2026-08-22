"""
Views for repositories app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import RepositoryCreateForm, RepositoryEditForm
from .models import Repository


class RepositoryOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts access to the repository's owner. Looks the repository up by owner
    username and name from the URL, matching the /repositories/<owner>/<name>/ scheme."""

    def get_object(self, queryset=None):
        if not hasattr(self, '_object'):
            self._object = get_object_or_404(
                Repository,
                owner__username=self.kwargs['owner'],
                name=self.kwargs['name'],
            )
        return self._object

    def test_func(self):
        return self.get_object().owner == self.request.user


class RepositoryListView(LoginRequiredMixin, ListView):
    """Lists the logged-in user's own repositories, most recently updated first."""

    model = Repository
    template_name = 'repositories/repository_list.html'
    context_object_name = 'repositories'

    def get_queryset(self):
        return Repository.objects.filter(owner=self.request.user).order_by('-updated_at')


class RepositoryDetailView(DetailView):
    """Shows a single repository. Private repositories are only visible to their owner."""

    model = Repository
    template_name = 'repositories/repository_detail.html'
    context_object_name = 'repository'

    def get_object(self, queryset=None):
        repository = get_object_or_404(
            Repository,
            owner__username=self.kwargs['owner'],
            name=self.kwargs['name'],
        )
        if repository.visibility == Repository.Visibility.PRIVATE and repository.owner != self.request.user:
            raise Http404
        return repository


class RepositoryCreateView(LoginRequiredMixin, CreateView):
    """Allows an authenticated user to create a new repository they own."""

    model = Repository
    form_class = RepositoryCreateForm
    template_name = 'repositories/repository_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Repository created successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy(
            'repository_detail',
            kwargs={'owner': self.object.owner.username, 'name': self.object.name},
        )


class RepositoryUpdateView(RepositoryOwnerRequiredMixin, UpdateView):
    """Allows the owner to edit a repository's description and visibility."""

    model = Repository
    form_class = RepositoryEditForm
    template_name = 'repositories/repository_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Repository updated successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy(
            'repository_detail',
            kwargs={'owner': self.object.owner.username, 'name': self.object.name},
        )


class RepositoryDeleteView(RepositoryOwnerRequiredMixin, DeleteView):
    """Allows the owner to delete a repository, after a confirmation page."""

    model = Repository
    template_name = 'repositories/repository_confirm_delete.html'
    success_url = reverse_lazy('repository_list')

    def form_valid(self, form):
        messages.success(self.request, 'Repository deleted successfully.')
        return super().form_valid(form)
