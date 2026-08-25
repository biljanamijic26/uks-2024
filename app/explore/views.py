"""
Views for explore app.
"""
from django.db.models import Case, IntegerField, Q, When
from django.views.generic import ListView

from repositories.models import Repository

SORT_OPTIONS = ('relevance', 'updated', 'name_asc', 'name_desc')


class ExploreListView(ListView):
    """Lets anyone search, filter, and sort public repositories."""

    model = Repository
    template_name = 'explore/explore.html'
    context_object_name = 'repositories'
    paginate_by = 12

    def get_queryset(self):
        queryset = Repository.objects.filter(visibility=Repository.Visibility.PUBLIC).select_related('owner')
        query = self.request.GET.get('q', '').strip()
        sort = self._get_sort()

        if self.request.GET.get('official') == '1':
            queryset = queryset.filter(is_official=True)
        if self.request.GET.get('verified') == '1':
            queryset = queryset.filter(owner__is_verified_publisher=True)
        if self.request.GET.get('sponsored') == '1':
            queryset = queryset.filter(owner__is_sponsored_oss=True)

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(short_description__icontains=query),
            ).annotate(
                relevance=Case(
                    When(name__icontains=query, then=0),
                    default=1,
                    output_field=IntegerField(),
                ),
            )

        if sort == 'updated':
            queryset = queryset.order_by('-updated_at')
        elif sort == 'name_asc':
            queryset = queryset.order_by('name')
        elif sort == 'name_desc':
            queryset = queryset.order_by('-name')
        elif query:
            queryset = queryset.order_by('-is_official', 'relevance', '-updated_at')
        else:
            queryset = queryset.order_by('-is_official', '-updated_at')

        return queryset

    def _get_sort(self):
        sort = self.request.GET.get('sort', 'relevance')
        return sort if sort in SORT_OPTIONS else 'relevance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filters = {
            'official': self.request.GET.get('official') == '1',
            'verified': self.request.GET.get('verified') == '1',
            'sponsored': self.request.GET.get('sponsored') == '1',
        }

        querystring = self.request.GET.copy()
        querystring.pop('page', None)

        context['query'] = self.request.GET.get('q', '')
        context['sort'] = self._get_sort()
        context['filters'] = filters
        context['active_filter_count'] = sum(filters.values())
        context['querystring'] = querystring.urlencode()

        return context
