from django.test import TestCase

from .query_parser import QueryParseError, parse_logical_query


class ParseLogicalQueryTest(TestCase):
    """Test cases for parse_logical_query."""

    def test_bare_word_matches_message(self):
        query = parse_logical_query('timeout')
        self.assertEqual(query, {'match': {'message': 'timeout'}})

    def test_quoted_phrase_matches_message_as_phrase(self):
        query = parse_logical_query('"error occurred"')
        self.assertEqual(query, {'match_phrase': {'message': 'error occurred'}})

    def test_keyword_field_term_uses_term_query(self):
        query = parse_logical_query('user:marija')
        self.assertEqual(query, {'term': {'user': 'marija'}})

    def test_level_value_is_uppercased(self):
        query = parse_logical_query('level:warning')
        self.assertEqual(query, {'term': {'level': 'WARNING'}})

    def test_simple_and_query_parses_correctly(self):
        query = parse_logical_query('level:error AND user:marija')
        self.assertEqual(query, {
            'bool': {'must': [{'term': {'level': 'ERROR'}}, {'term': {'user': 'marija'}}]},
        })

    def test_or_query_parses_correctly(self):
        query = parse_logical_query('level:warning OR level:error')
        self.assertEqual(query, {
            'bool': {
                'should': [{'term': {'level': 'WARNING'}}, {'term': {'level': 'ERROR'}}],
                'minimum_should_match': 1,
            },
        })

    def test_not_query_parses_correctly(self):
        query = parse_logical_query('NOT level:info')
        self.assertEqual(query, {'bool': {'must_not': [{'term': {'level': 'INFO'}}]}})

    def test_nested_parentheses_parse_correctly(self):
        query = parse_logical_query('(level:warning OR level:error) AND message:"error occurred"')
        self.assertEqual(query, {
            'bool': {
                'must': [
                    {
                        'bool': {
                            'should': [{'term': {'level': 'WARNING'}}, {'term': {'level': 'ERROR'}}],
                            'minimum_should_match': 1,
                        },
                    },
                    {'match_phrase': {'message': 'error occurred'}},
                ],
            },
        })

    def test_operators_are_case_insensitive(self):
        query = parse_logical_query('level:error and not level:critical')
        self.assertEqual(query, {
            'bool': {'must': [
                {'term': {'level': 'ERROR'}},
                {'bool': {'must_not': [{'term': {'level': 'CRITICAL'}}]}},
            ]},
        })

    def test_empty_query_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('   ')

    def test_unmatched_opening_parenthesis_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('(level:error')

    def test_unmatched_closing_parenthesis_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('level:error)')

    def test_dangling_operator_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('level:error AND')

    def test_consecutive_terms_without_operator_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('level:error level:warning')

    def test_unknown_field_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('severity:high')

    def test_unterminated_quote_shows_error(self):
        with self.assertRaises(QueryParseError):
            parse_logical_query('message:"error occurred')
