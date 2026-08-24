"""
Views for repositories app.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import OfficialRepositoryCreateForm, RepositoryCreateForm, RepositoryEditForm, TagCreateForm, TagEditForm
from .models import Repository, Tag


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated admins (ADMIN or SUPER_ADMIN)."""

    def test_func(self):
        return self.request.user.is_admin


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

    TAG_SORT_OPTIONS = {
        'newest': ('-created_at', '-id'),
        'oldest': ('created_at', 'id'),
        'name': ('name',),
        'size': ('-size',),
    }
    DEFAULT_TAG_SORT = 'newest'
    TAG_SORT_SESSION_KEY = 'tag_sort'

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

        sort = self.request.GET.get('sort')
        if sort in self.TAG_SORT_OPTIONS:
            self.request.session[self.TAG_SORT_SESSION_KEY] = sort
        else:
            sort = self.request.session.get(self.TAG_SORT_SESSION_KEY, self.DEFAULT_TAG_SORT)
            if sort not in self.TAG_SORT_OPTIONS:
                sort = self.DEFAULT_TAG_SORT

        query = self.request.GET.get('q', '').strip()

        tags = self.object.tags.all()
        if query:
            tags = tags.filter(name__icontains=query)
        tags = tags.order_by(*self.TAG_SORT_OPTIONS[sort])

        context['tags'] = tags
        context['tag_sort'] = sort
        context['tag_query'] = query
        context['tags_tab_active'] = 'sort' in self.request.GET or 'q' in self.request.GET
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


class OfficialRepositoryCreateView(AdminRequiredMixin, CreateView):
    """Allows an admin to create an official repository, owned by the admin's account
    but displayed without a username prefix (see Repository.full_name)."""

    model = Repository
    form_class = OfficialRepositoryCreateForm
    template_name = 'repositories/official_repository_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.is_official = True
        response = super().form_valid(form)
        messages.success(self.request, f"Official repository '{self.object.full_name}' created successfully.")
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
