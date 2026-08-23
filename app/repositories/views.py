"""
Views for repositories app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import RepositoryCreateForm, RepositoryEditForm, TagCreateForm, TagEditForm
from .models import Repository, Tag


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


class TagOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts access to the parent repository's owner. Looks the repository up by
    owner username and name from the URL, matching the /repositories/<owner>/<name>/tags/... scheme."""

    def get_repository(self):
        if not hasattr(self, '_repository'):
            self._repository = get_object_or_404(
                Repository,
                owner__username=self.kwargs['owner'],
                name=self.kwargs['name'],
            )
        return self._repository

    def test_func(self):
        return self.get_repository().owner == self.request.user

    def get_success_url(self):
        repository = self.get_repository()
        return reverse_lazy(
            'repository_detail',
            kwargs={'owner': repository.owner.username, 'name': repository.name},
        )


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = self.object.tags.order_by('-created_at', '-id')
        return context


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


class TagCreateView(TagOwnerRequiredMixin, CreateView):
    """Allows the repository owner to create a new tag."""

    model = Tag
    form_class = TagCreateForm
    template_name = 'repositories/tag_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['repository'] = self.get_repository()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Tag(repository=self.get_repository())
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tag created successfully.')
        return response


class TagUpdateView(TagOwnerRequiredMixin, UpdateView):
    """Allows the repository owner to edit a tag's digest and size."""

    model = Tag
    form_class = TagEditForm
    template_name = 'repositories/tag_form.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Tag, repository=self.get_repository(), name=self.kwargs['tag_name'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['repository'] = self.get_repository()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tag updated successfully.')
        return response


class TagDeleteView(TagOwnerRequiredMixin, DeleteView):
    """Allows the repository owner to delete a tag, after a confirmation page."""

    model = Tag
    template_name = 'repositories/tag_confirm_delete.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Tag, repository=self.get_repository(), name=self.kwargs['tag_name'])

    def form_valid(self, form):
        messages.success(self.request, 'Tag deleted successfully.')
        return super().form_valid(form)
