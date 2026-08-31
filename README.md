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

| Component          | Technology                        | Version |
| ------------------ | --------------------------------- | ------- |
| Backend Framework  | Django                            | 5.x     |
| Database           | PostgreSQL (SQLite for local dev) | 15      |
| Cache              | Redis                             | 7       |
| Reverse Proxy      | NGINX                             | alpine  |
| Search Engine      | Elasticsearch                     | 8.11    |
| Container Registry | Distribution                      | 2       |
| CI/CD              | GitHub Actions                    | -       |
| Containerization   | Docker + Docker Compose           | -       |

## How the application and Docker Registry work

### 1. What is a Docker Registry?

A Docker Registry is a server that stores and distributes Docker images. It
plays the same role as Docker Hub, but this project runs its own local Registry
using the official Docker Distribution image.

An image name such as:

```text
localhost:5000/user/reponame:1.0
```

contains four important parts:

1. `localhost:5000` is the Registry address exposed on the host machine.
2. `user` is the owner namespace.
3. `reponame` is the repository name.
4. `1.0` is the image tag or version.

The Registry stores manifests and binary image layers. Django does not store
those binary layers. Django stores application users, repository ownership,
visibility, and synchronized tag metadata in PostgreSQL.

### 2. Service responsibilities

| Service         | Responsibility                                                  |
| --------------- | --------------------------------------------------------------- |
| `nginx`         | Public entry point; forwards web and Registry requests          |
| `web`           | Django application, UI, authorization policy, and token service |
| `registry`      | Stores Docker manifests and image layers                        |
| `db`            | Stores Django users, repositories, roles, and tag metadata      |
| `redis`         | Cache and temporary application data                            |
| `elasticsearch` | Stores indexed application logs for analytics search            |

Repository information therefore exists in two related places:

1. PostgreSQL knows that a repository exists, who owns it, whether it is
   public or private, and which tags Django currently displays.
2. The Registry stores the actual image content and the authoritative list of
   pushed image tags.

The `sync_tags` command reads tag information from the Registry and updates
the corresponding Django records. It does not copy image layers into the
database.

### 3. Host ports and internal container ports

Docker Compose gives every service an internal DNS name equal to its service
name. Containers communicate using these names and their internal ports.
Only ports explicitly published in `docker-compose.yml` are reachable from the
host machine.

| Host address            | Docker mapping | Destination               | Purpose                            |
| ----------------------- | -------------- | ------------------------- | ---------------------------------- |
| `http://localhost:80`   | `80:80`        | NGINX port `80`           | Web application                    |
| `http://localhost:5000` | `5000:80`      | NGINX port `80`           | Docker Registry client entry point |
| `http://localhost:9200` | `9200:9200`    | Elasticsearch port `9200` | Elasticsearch API and diagnostics  |

The following ports are internal and are not published directly to the host:

| Internal address | Used by                                          |
| ---------------- | ------------------------------------------------ |
| `web:8000`       | NGINX forwards Django requests here              |
| `registry:5000`  | NGINX forwards `/v2/` Registry API requests here |
| `db:5432`        | Django connects to PostgreSQL here               |
| `redis:6379`     | Django connects to Redis here                    |

Both host ports `80` and `5000` lead to port `80` of the same NGINX container.
NGINX then routes requests by URL path:

1. `/v2/` is forwarded to `registry:5000`.
2. `/static/` is served from the static-files volume.
3. Every other path, including `/registry/token/`, is forwarded to
   `web:8000`.

The Registry container uses `expose: 5000`, not `ports: 5000:5000`. This is
intentional: clients cannot bypass NGINX and the Django authorization policy by
connecting directly to the Registry container.

### 4. Authentication and authorization flow

When `docker login`, `docker push`, or `docker pull` is executed, the following
flow takes place:

1. The Docker client connects to `localhost:5000`.
2. NGINX forwards `/v2/` to the Registry.
3. The Registry requests a Bearer token from
   `http://localhost:5000/registry/token/`.
4. NGINX forwards that token request to Django.
5. Django authenticates the application username and password and checks the
   requested repository, owner, visibility, and role.
6. Django signs a short-lived token containing only the allowed actions, such
   as `pull` or `pull,push`.
7. The Docker client sends that token to the Registry.
8. The Registry verifies the signature with `registry-auth.crt` and permits
   only the actions listed in the token.

The private key `auth/registry-auth.key` is used by Django to sign tokens. The
certificate `auth/registry-auth.crt` is used by the Registry to verify them.
These files must be generated before the first startup and must not be
committed to Git.

### 5. Persistent Docker volumes

Container removal does not normally remove application data because the
Compose stack uses named volumes:

| Volume               | Stored data                                        |
| -------------------- | -------------------------------------------------- |
| `postgres_data`      | Users, repositories, roles, and Django tag records |
| `registry_data`      | Docker image manifests and layers                  |
| `redis_data`         | Redis data                                         |
| `elasticsearch_data` | Indexed application logs                           |
| `static_volume`      | Collected Django static files                      |
| `logs_volume`        | Django application log files                       |

`docker compose down` stops and removes containers but keeps these volumes.
`docker compose down -v` also deletes the volumes and permanently resets the
local application data.

## Git Workflow

This project follows the [GitFlow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) branching model.

### Branches

| Branch      | Purpose                                          |
| ----------- | ------------------------------------------------ |
| `main`      | Production-ready releases only                   |
| `develop`   | Active development, integration branch           |
| `feature-*` | New features (e.g., `feature-user-registration`) |
| `bugfix-*`  | Bug fixes (e.g., `bugfix-login-redirect`)        |

### Rules

- All code changes must go through Pull Requests
- PRs require at least one approval before merging
- CI checks must pass before merging
- Feature and bugfix branches are created from `develop`
- Only `develop` is merged into `main` during releases

## Conventions

### Commit Messages

Format: `<type>: <description>`

| Type       | Description                                      |
| ---------- | ------------------------------------------------ |
| `feat`     | New feature                                      |
| `fix`      | Bug fix                                          |
| `docs`     | Documentation changes                            |
| `test`     | Adding or updating tests                         |
| `refactor` | Code refactoring                                 |
| `chore`    | Maintenance tasks                                |
| `style`    | Code style changes (formatting, no logic change) |

### Branch Naming

- Features: `feature-<short-description>`
- Bug fixes: `bugfix-<short-description>`

Use lowercase letters and hyphens, no spaces.

## Local Setup

### Prerequisites

- Python 3.12+
- Git
- Docker and Docker Compose (only needed for the "With Docker" setup below)

### Commands for running the entire application (PowerShell)

Run every command in this section from the project root, which is the
directory containing `docker-compose.yml`.

#### 1. First startup

Copy the environment configuration:

```powershell
Copy-Item .env.example .env
```

Generate the key and certificate for the local Docker Registry. This is
required only once:

```powershell
docker run --rm -v "${PWD}/auth:/certs" alpine/openssl req -newkey rsa:4096 -nodes -sha256 -keyout /certs/registry-auth.key -x509 -days 3650 -out /certs/registry-auth.crt -subj "/CN=uks-registry-auth"
```

Build the images and start every service:

```powershell
docker compose up -d --build
docker compose ps
```

The `web` container runs migrations automatically during startup. Migrations
can also be run manually when needed:

```powershell
docker compose exec web python manage.py migrate
```

Create the initial super administrator and display the generated password:

```powershell
docker compose exec web python manage.py setup_admin
docker compose exec web cat admin_password.txt
```

Sign in at `http://localhost/admin/` with the username `admin`. On the first
sign-in, the application requires the generated password to be changed.

#### 2. Application checks and tests

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

Follow the web application logs:

```powershell
docker compose logs -f web
```

Stop following the logs with `Ctrl+C`.

#### 3. Elasticsearch and log search

Elasticsearch starts as part of the Docker Compose stack. Check its container
status and API availability:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:9200
```

The `log-indexer` service also starts automatically as part of the Compose
stack. It runs `index_logs` in a loop every 60 seconds, so new log entries are
indexed without any manual step. Its output can be followed with:

```powershell
docker compose logs -f log-indexer
```

The command remembers its last position and indexes only new entries each
time it runs. To re-index every log entry, run it manually with `--full`:

```powershell
docker compose exec web python manage.py index_logs --full
```

Indexed log search is available at `http://localhost/admin-panel/analytics/`.

#### 4. Every subsequent startup

```powershell
docker compose up -d
docker compose ps
```

Stop the application without deleting its data:

```powershell
docker compose down
```

#### 5. Completely clean startup

WARNING: The following command deletes the PostgreSQL database, Redis data,
Elasticsearch index, Registry images, and all other Docker volumes belonging
to this project.

```powershell
docker compose down -v --remove-orphans
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose exec web python manage.py setup_admin
docker compose exec web cat admin_password.txt
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

#### 6. Push, pull, and tag synchronization

Docker images are stored in the Distribution Registry, while repository and
tag information displayed by Django is stored in PostgreSQL. A repository
must therefore exist in the web application before an image can be pushed to
it. After a push, run `sync_tags` to copy the Registry tag metadata into
Django.

##### 6.1. Create an application user

Open `http://localhost/`, register a regular user, and sign in. The examples
below use `user` as the username. Replace it with the username of the account
that you created.

The initial `admin` account can also sign in, but a regular user is recommended
when testing personal repositories.

##### 6.2. Create a repository in the web application

While signed in, create a personal repository named `reponame`. Choose whether
it should be public or private. Its full Registry name is composed of the
username and repository name:

```text
user/reponame
```

Do not push the image before this repository exists in the application. The
token service rejects pushes to unknown repositories and pushes made by users
who do not own the repository.

##### 6.3. Sign in to the local Docker Registry

Use the same username and password that you use in the web application:

```powershell
docker login localhost:5000
```

Enter the application username and password when Docker prompts for them. A
successful login prints `Login Succeeded`.

##### 6.4. Download an image to use for testing

For example, download Alpine from Docker Hub:

```powershell
docker pull alpine:latest
```

##### 6.5. Tag the image for the local Registry

The target name must contain `localhost:5000`, the application username, the
repository name, and the tag:

```powershell
docker tag alpine:latest localhost:5000/user/reponame:latest
```

Confirm that the new local tag exists:

```powershell
docker image ls localhost:5000/user/reponame
```

##### 6.6. Push the image

```powershell
docker push localhost:5000/user/reponame:latest
```

If the push returns `unauthorized`, check that:

1. `docker login localhost:5000` used the correct application account.
2. `user/reponame` already exists in the web application.
3. The signed-in user is the owner of `user/reponame`.
4. The `web`, `nginx`, and `registry` containers are running.

Container status and relevant logs can be checked with:

```powershell
docker compose ps
docker compose logs --tail 100 web
docker compose logs --tail 100 nginx
docker compose logs --tail 100 registry
```

##### 6.7. Synchronize tags with Django

Pushing stores the image in the Registry, but it does not immediately create
the corresponding Django `Tag` record. Synchronize the repository after the
push:

```powershell
docker compose exec web python manage.py sync_tags --repo user/reponame
```

To synchronize every repository known to Django, run:

```powershell
docker compose exec web python manage.py sync_tags
```

The command creates missing `Tag` records, updates digest and compressed-size
metadata, and removes Django tags that no longer exist in the Registry. It is
safe to run repeatedly.

After synchronization, refresh the repository page in the browser. The
`latest` tag should be displayed with its Registry metadata.

##### 6.8. Test pulling a public repository

Log out of the Registry to test anonymous access, remove only the local test
tag, and pull it again:

```powershell
docker logout localhost:5000
docker image rm localhost:5000/user/reponame:latest
docker pull localhost:5000/user/reponame:latest
```

Anonymous pull should succeed when `user/reponame` is public.

##### 6.9. Test pulling a private repository

Change the repository visibility to private in the web application. Anonymous
pull should then fail:

```powershell
docker logout localhost:5000
docker pull localhost:5000/user/reponame:latest
```

Sign in as the repository owner and try again:

```powershell
docker login localhost:5000
docker pull localhost:5000/user/reponame:latest
```

The authenticated pull should succeed for the owner. A different regular user
must not be able to push to this repository.

##### 6.10. Push and synchronize an additional version

The text after the final colon is the Docker tag. For example, push the same
image as version `1.0` and synchronize it:

```powershell
docker tag alpine:latest localhost:5000/user/reponame:1.0
docker push localhost:5000/user/reponame:1.0
docker compose exec web python manage.py sync_tags --repo user/reponame
```

Both `latest` and `1.0` should now appear on the repository page.

##### 6.11. Official repositories

Official repository image names do not contain a username. An administrator
must first create an official repository in the web application. For an
official repository named `official-alpine`, an authorized administrator can
run:

```powershell
docker login localhost:5000
docker tag alpine:latest localhost:5000/official-alpine:latest
docker push localhost:5000/official-alpine:latest
docker compose exec web python manage.py sync_tags --repo official-alpine
```

Regular users must not be allowed to push to official repositories.

#### 7. Diagnostics

```powershell
docker compose ps
docker compose logs --tail 100 web
docker compose logs --tail 100 elasticsearch
docker compose logs --tail 100 db
```

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

Once logs are indexed, admins can search them at `/admin-panel/analytics/` — by text, log level, and date range. An **Advanced** tab supports logical queries with `AND`/`OR`/`NOT`, parentheses, and `field:value` terms (e.g. `(level:warning OR level:error) AND message:"error occurred"`).

### With Docker

```bash
git clone <repo-url>
cd docker-registry-platform

# Copy the example environment file and adjust as needed
cp .env.example .env

# Build and start all services (web, db, redis, nginx, elasticsearch, log-indexer)
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

_This structure will grow as more features are implemented (Docker configs, NGINX, CI/CD workflows, docs, etc.)._

## Documentation

- [UML Class Diagram](docs/uml-class-diagram.png) — domain model showing `User`, `Repository`, and `Tag`, their fields/methods, and relationships. Source: [docs/uml-class-diagram.puml](docs/uml-class-diagram.puml) (SVG version also available: [docs/uml-class-diagram.svg](docs/uml-class-diagram.svg)).
