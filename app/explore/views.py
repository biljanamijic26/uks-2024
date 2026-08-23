"""
Views for explore app.
"""
from django.db.models import Case, IntegerField, Q, When
from django.views.generic import ListView

from repositories.models import Repository


class ExploreListView(ListView):
    """Lets anyone search public repositories, ranked by relevance to the search term."""

    model = Repository
    template_name = 'explore/explore.html'
    context_object_name = 'repositories'
    paginate_by = 12

    def get_queryset(self):
        queryset = Repository.objects.filter(visibility=Repository.Visibility.PUBLIC)
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(short_description__icontains=query),
            ).annotate(
                relevance=Case(
                    When(name__icontains=query, then=0),
                    default=1,
                    output_field=IntegerField(),
                ),
            ).order_by('relevance', '-updated_at')
        else:
            queryset = queryset.order_by('-updated_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context
