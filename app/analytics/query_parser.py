"""
Parses a logical log-search query string (AND/OR/NOT, parentheses, and
field:value terms) into an Elasticsearch bool query DSL dict.

Grammar (OR binds loosest, NOT binds tightest):
    or_expr   := and_expr (OR and_expr)*
    and_expr  := not_expr (AND not_expr)*
    not_expr  := NOT not_expr | primary
    primary   := '(' or_expr ')' | term
    term      := [field ':'] value, where value may be a "quoted phrase"
"""

KEYWORD_FIELDS = {'level', 'logger', 'method', 'path', 'user'}
TEXT_FIELDS = {'message'}
DEFAULT_FIELD = 'message'
OPERATORS = {'AND', 'OR', 'NOT'}


class QueryParseError(Exception):
    """Raised when a logical query string is not syntactically valid."""


def parse_logical_query(query):
    """Parses `query` into an Elasticsearch bool query DSL dict, or raises QueryParseError."""
    tokens = _tokenize(query.strip())
    if not tokens:
        raise QueryParseError('Query is empty.')
    return _Parser(tokens).parse()


def _tokenize(query):
    tokens = []
    i, n = 0, len(query)
    while i < n:
        char = query[i]
        if char.isspace():
            i += 1
            continue
        if char in '()':
            tokens.append(char)
            i += 1
            continue

        buf = []
        while i < n and not query[i].isspace() and query[i] not in '()':
            if query[i] == '"':
                buf.append(query[i])
                i += 1
                while i < n and query[i] != '"':
                    buf.append(query[i])
                    i += 1
                if i >= n:
                    raise QueryParseError('Unterminated quoted string.')
                buf.append(query[i])
                i += 1
                continue
            buf.append(query[i])
            i += 1
        tokens.append(''.join(buf))
    return tokens


def _build_term_clause(token):
    if ':' in token:
        field, value = token.split(':', 1)
    else:
        field, value = DEFAULT_FIELD, token

    if not field or not value:
        raise QueryParseError(f'Invalid term "{token}".')

    quoted = value.startswith('"') and value.endswith('"') and len(value) >= 2
    if quoted:
        value = value[1:-1]
    if not value:
        raise QueryParseError(f'Empty value in term "{token}".')

    if field == 'level':
        return {'term': {'level': value.upper()}}
    if field in KEYWORD_FIELDS:
        return {'term': {field: value}}
    if field in TEXT_FIELDS:
        return {'match_phrase': {field: value}} if quoted else {'match': {field: value}}

    raise QueryParseError(f'Unknown field "{field}".')


class _Parser:
    """Recursive-descent parser over a flat token list."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def parse(self):
        node = self._parse_or()
        if self.pos != len(self.tokens):
            raise QueryParseError(f'Unexpected token "{self._peek()}".')
        return node

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        token = self._peek()
        self.pos += 1
        return token

    def _next_is(self, keyword):
        token = self._peek()
        return token is not None and token.upper() == keyword

    def _parse_or(self):
        clauses = [self._parse_and()]
        while self._next_is('OR'):
            self._advance()
            clauses.append(self._parse_and())
        if len(clauses) == 1:
            return clauses[0]
        return {'bool': {'should': clauses, 'minimum_should_match': 1}}

    def _parse_and(self):
        clauses = [self._parse_not()]
        while self._next_is('AND'):
            self._advance()
            clauses.append(self._parse_not())
        if len(clauses) == 1:
            return clauses[0]
        return {'bool': {'must': clauses}}

    def _parse_not(self):
        if self._next_is('NOT'):
            self._advance()
            return {'bool': {'must_not': [self._parse_not()]}}
        return self._parse_primary()

    def _parse_primary(self):
        token = self._peek()
        if token is None:
            raise QueryParseError('Unexpected end of query.')

        if token == '(':
            self._advance()
            node = self._parse_or()
            if self._peek() != ')':
                raise QueryParseError('Missing closing parenthesis.')
            self._advance()
            return node

        if token == ')':
            raise QueryParseError('Unexpected closing parenthesis.')

        if token.upper() in OPERATORS:
            raise QueryParseError(f'Unexpected operator "{token}".')

        self._advance()
        return _build_term_clause(token)
