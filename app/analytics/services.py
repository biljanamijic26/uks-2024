"""
Elasticsearch query building for the admin log search page.
"""

RELEVANCE_SORT = [{'_score': 'desc'}, {'timestamp': 'desc'}]


def build_log_search_query(cleaned_data):
    """Builds an Elasticsearch query DSL dict and sort clause from LogSearchForm.cleaned_data.

    Text matches contribute to the relevance score; level and date range narrow the
    result set without affecting it, so results stay sorted by relevance first.
    """
    must = []
    filters = []

    text = cleaned_data.get('q')
    if text:
        # bool_prefix treats the last (possibly still-being-typed) word as a prefix match,
        # so results appear before the user finishes typing a whole word.
        must.append({'multi_match': {'query': text, 'fields': ['message'], 'type': 'bool_prefix'}})
    else:
        must.append({'match_all': {}})

    level = cleaned_data.get('level')
    if level:
        filters.append({'term': {'level': level}})

    date_after = cleaned_data.get('date_after')
    date_before = cleaned_data.get('date_before')
    if date_after or date_before:
        date_range = {}
        if date_after:
            date_range['gte'] = date_after.isoformat()
        if date_before:
            date_range['lte'] = date_before.isoformat()
        filters.append({'range': {'timestamp': date_range}})

    query = {'bool': {'must': must, 'filter': filters}}
    return query, RELEVANCE_SORT
