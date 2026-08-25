"""
Management command that indexes JSON log entries into Elasticsearch.
"""
import hashlib
import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

INDEX_NAME = 'app-logs'
LOG_FILENAMES = ['app.log', 'access.log', 'error.log']
# Both loggers write to the root handlers (hence app.log) by default. Since this command
# itself talks to Elasticsearch over HTTP, leaving them at INFO would make each run log its
# own requests into app.log, which the next run would then pick back up as new entries.
NOISY_CLIENT_LOGGERS = ['elastic_transport', 'elasticsearch']
POSITION_FILENAME = '.index_logs_position.json'

INDEX_MAPPING = {
    'properties': {
        'timestamp': {
            'type': 'date',
            # Matches the LOGGING 'json' formatter's asctime output (e.g. "2026-08-25 08:04:04,521"),
            # with ISO/epoch kept as fallbacks for other sources.
            'format': 'yyyy-MM-dd HH:mm:ss,SSS||strict_date_optional_time||epoch_millis',
        },
        'level': {'type': 'keyword'},
        'logger': {'type': 'keyword'},
        'message': {'type': 'text'},
        'method': {'type': 'keyword'},
        'path': {'type': 'keyword'},
        'user': {'type': 'keyword'},
    },
}


def parse_log_line(line):
    """Parse a single JSON log line into a dict, or None if malformed/blank."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


class Command(BaseCommand):
    help = 'Parses JSON log files from LOGS_DIR and indexes new entries into Elasticsearch.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full', action='store_true',
            help='Ignore the tracked position and re-index every log entry from the start of each file.',
        )

    def handle(self, *args, **options):
        for logger_name in NOISY_CLIENT_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        positions = {} if options['full'] else self._load_positions()

        es = Elasticsearch(settings.ELASTICSEARCH_URL)
        if not es.indices.exists(index=INDEX_NAME):
            es.indices.create(index=INDEX_NAME, mappings=INDEX_MAPPING)

        total_indexed = 0
        for filename in LOG_FILENAMES:
            file_path = Path(settings.LOGS_DIR) / filename
            if not file_path.exists():
                continue

            actions, new_offset = self._read_new_entries(file_path, positions.get(filename, 0), filename)
            if actions:
                bulk(es, actions)
                total_indexed += len(actions)

            positions[filename] = new_offset

        self._save_positions(positions)
        self.stdout.write(self.style.SUCCESS(f'Indexed {total_indexed} log entries into "{INDEX_NAME}".'))

    def _read_new_entries(self, file_path, offset, filename):
        actions = []
        with open(file_path, 'r') as f:
            f.seek(offset)
            line = f.readline()
            while line:
                line_offset = offset
                entry = parse_log_line(line)
                if entry is not None:
                    doc_id = hashlib.md5(f'{filename}:{line_offset}'.encode()).hexdigest()
                    actions.append({'_index': INDEX_NAME, '_id': doc_id, '_source': entry})
                offset = f.tell()
                line = f.readline()
        return actions, offset

    def _position_file_path(self):
        return Path(settings.LOGS_DIR) / POSITION_FILENAME

    def _load_positions(self):
        path = self._position_file_path()
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def _save_positions(self, positions):
        with open(self._position_file_path(), 'w') as f:
            json.dump(positions, f)
