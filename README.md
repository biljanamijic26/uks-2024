# Docker Registry Platform

Web application for sharing Docker images, developed as a project for the Software Configuration Management (UKS) course at Faculty of Technical Sciences, Novi Sad.

## Team

- [Anja Maksimović](https://github.com/AnjaMaksimovic) E2 77/2024
- [Biljana Mijić](https://github.com/biljanamijic26) E2 63/2024
- [Marija Ilić](https://github.com/Makiic) E2 28/2024

## About

This application is a simplified version of the DockerHub platform. It allows users to register, create and manage Docker image repositories, search public repositories, and provides administrators with system monitoring capabilities through log analysis.

Key features (planned):
- User registration and authentication with role-based access control
- Repository management (create, update, delete, visibility settings)
- Public repository search with relevance-based sorting
- Tag management for Docker images
- Admin panel for user and official repository management
- System analytics powered by Elasticsearch
- Local container registry integration (Distribution)

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Backend Framework | Django | 5.x |
| Database | PostgreSQL (SQLite for local dev) | 15 |
| Cache | Redis | 7 |
| Reverse Proxy | NGINX | alpine |
| Search Engine | Elasticsearch | 8.11 |
| Container Registry | Distribution | 2 |
| CI/CD | GitHub Actions | - |
| Containerization | Docker + Docker Compose | - |

## Git Workflow

This project follows the [GitFlow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) branching model.

### Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready releases only |
| `develop` | Active development, integration branch |
| `feature-*` | New features (e.g., `feature-user-registration`) |
| `bugfix-*` | Bug fixes (e.g., `bugfix-login-redirect`) |

### Rules

- All code changes must go through Pull Requests
- PRs require at least one approval before merging
- CI checks must pass before merging
- Feature and bugfix branches are created from `develop`
- Only `develop` is merged into `main` during releases

## Conventions

### Commit Messages

Format: `<type>: <description>`

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `test` | Adding or updating tests |
| `refactor` | Code refactoring |
| `chore` | Maintenance tasks |
| `style` | Code style changes (formatting, no logic change) |

### Branch Naming

- Features: `feature-<short-description>`
- Bug fixes: `bugfix-<short-description>`

Use lowercase letters and hyphens, no spaces.

## Local Setup

### Prerequisites

- Python 3.12+
- Git
- Docker and Docker Compose (only needed for the "With Docker" setup below)

### Getting Started (without Docker)

```bash
git clone <repo-url>
cd docker-registry-platform/app

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations (uses SQLite by default)
python manage.py migrate

# Run tests
python manage.py test

# Start the development server
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`.

By default, the project uses **SQLite** for local development (no extra setup needed). To use PostgreSQL instead, set the `DATABASE_URL` environment variable, e.g.:

```bash
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/docker_registry
```

### Super Admin Account

On first run, create the super administrator account:

```bash
python manage.py setup_admin
```

This creates a user named `admin` with `role=SUPER_ADMIN` and `must_change_password=True`, and generates a random password. The password is **not** printed to the console — it's saved to a file, by default `admin_password.txt` inside `app/` (path is configurable via the `ADMIN_PASSWORD_FILE` environment variable, see `.env.example`).

```bash
cat admin_password.txt
```

Log in at `http://127.0.0.1:8000/admin/` with username `admin` and the password from that file.

The command is safe to run more than once — if the `admin` user already exists, it does nothing and prints `Super admin 'admin' already exists, skipping.` instead of creating a duplicate or overwriting the password.

`admin_password.txt` is git-ignored — never commit it.

### Log Indexing (Analytics)

Application logs are written as JSON to `app/logs/` (see `LOGGING` in `config/settings.py`). To make them searchable, index them into Elasticsearch:

```bash
python manage.py index_logs
```

This parses `app.log`, `access.log`, and `error.log`, and sends new entries to the `app-logs` Elasticsearch index (`ELASTICSEARCH_URL`, default `http://localhost:9200`). It tracks how far it read into each file (in `app/logs/.index_logs_position.json`), so running it again only picks up newly appended lines — safe to run repeatedly, e.g. on a schedule. Use `--full` to ignore the tracked position and re-index every log entry from the start of each file (this does not create duplicates, since each entry gets a deterministic id).

Requires Elasticsearch to be reachable — either via `docker compose up -d elasticsearch`, or a local instance with `ELASTICSEARCH_URL` set accordingly.

### With Docker

```bash
git clone <repo-url>
cd docker-registry-platform

# Copy the example environment file and adjust as needed
cp .env.example .env

# Build and start all services (web, db, redis, nginx, elasticsearch)
docker compose up --build
```

The app will be available at `http://localhost/`, and Elasticsearch at `http://localhost:9200/`.

On first run, create the super admin account inside the `web` container:

```bash
docker compose exec web python manage.py setup_admin
docker compose exec web cat admin_password.txt
```

The `web` container runs migrations automatically on startup and waits for the `db` service to report healthy before starting.

## Project Structure

```
docker-registry-platform/
├── app/
│   ├── config/             # Django settings, URLs, WSGI
│   ├── accounts/           # User auth, profiles, admin management
│   ├── repositories/       # Repository and tag management
│   ├── explore/            # Public search and discovery
│   ├── analytics/          # Log collection and Elasticsearch
│   ├── core/               # Shared utilities
│   ├── templates/          # HTML templates
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── manage.py
├── nginx/
│   └── nginx.conf          # Reverse proxy config
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

*This structure will grow as more features are implemented (Docker configs, NGINX, CI/CD workflows, docs, etc.).*

## Documentation

- [UML Class Diagram](docs/uml-class-diagram.png) — domain model showing `User`, `Repository`, and `Tag`, their fields/methods, and relationships. Source: [docs/uml-class-diagram.puml](docs/uml-class-diagram.puml) (SVG version also available: [docs/uml-class-diagram.svg](docs/uml-class-diagram.svg)).