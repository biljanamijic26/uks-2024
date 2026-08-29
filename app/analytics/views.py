"""
Views for analytics app.
"""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from elasticsearch import Elasticsearch, NotFoundError

from .forms import LogSearchForm
from .management.commands.index_logs import INDEX_NAME
from .query_parser import QueryParseError, parse_logical_query
from .services import RELEVANCE_SORT, build_log_search_query

PAGE_SIZE = 20


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated admins (ADMIN or SUPER_ADMIN)."""

    def test_func(self):
        return self.request.user.is_admin


class LogSearchView(AdminRequiredMixin, TemplateView):
    """Admin-only page for searching application logs indexed into Elasticsearch."""

    template_name = 'analytics/log_search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = LogSearchForm(self.request.GET)
        context['form'] = form
        mode = self.request.GET.get('mode')
        context['mode'] = 'advanced' if mode == 'advanced' else 'simple'

        if form.is_valid():
            try:
                context.update(self._search(form, context['mode']))
            except QueryParseError as error:
                context['query_error'] = str(error)

        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_string'] = params.urlencode()

        return context

    def _search(self, form, mode):
        if mode == 'advanced':
            raw_query = form.cleaned_data.get('advanced_q', '').strip()
            query = parse_logical_query(raw_query) if raw_query else {'match_all': {}}
            sort = RELEVANCE_SORT
        else:
            query, sort = build_log_search_query(form.cleaned_data)

        page = self._page_number()

        es = Elasticsearch(settings.ELASTICSEARCH_URL)
        try:
            result = es.search(
                index=INDEX_NAME, query=query, sort=sort,
                from_=(page - 1) * PAGE_SIZE, size=PAGE_SIZE,
            )
        except NotFoundError:
            # No logs have been indexed yet, so the index doesn't exist.
            result = {'hits': {'total': {'value': 0}, 'hits': []}}

        total = result['hits']['total']['value']
        return {
            'searched': True,
            'results': [hit['_source'] for hit in result['hits']['hits']],
            'page_number': page,
            'num_pages': max(1, -(-total // PAGE_SIZE)),
            'has_previous': page > 1,
            'has_next': page * PAGE_SIZE < total,
        }

    def _page_number(self):
        try:
            return max(1, int(self.request.GET.get('page', 1)))
        except ValueError:
            return 1
