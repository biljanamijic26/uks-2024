# Registry authentication

Registry traffic enters through NGINX on `localhost:5000`. NGINX asks Django
for a short-lived Bearer token containing only the allowed repository actions.
The Distribution container is not published directly, because that would
bypass repository access control.

Generate the local signing key and certificate once before starting the stack:

```powershell
docker run --rm -v "${PWD}/auth:/certs" alpine/openssl req -newkey rsa:4096 -nodes -sha256 -keyout /certs/registry-auth.key -x509 -days 3650 -out /certs/registry-auth.crt -subj "/CN=uks-registry-auth"
```

Both files are ignored by Git. The Django token service signs tokens with the
private key and Distribution verifies them with the certificate.

Docker clients use the username and password of an application account:

```bash
docker login localhost:5000
```

Image names must match a repository that already exists in the application:

- Personal repository: `localhost:5000/<username>/<repository>:<tag>`
- Official repository: `localhost:5000/<repository>:<tag>`

## Manual checks

Create public and private repositories in the application, then start the
stack with `docker compose up --build`.

An owner can push to their personal repository:

```bash
docker login localhost:5000
docker tag alpine localhost:5000/user/reponame:latest
docker push localhost:5000/user/reponame:latest
```

Log in as a different user and repeat the push to confirm it is rejected.
Anonymous pulls of public repositories work after `docker logout
localhost:5000`; private pulls require the owning user to log in. Admin users
can push an image named after an existing official repository.

The old `auth/htpasswd` file is no longer used and can be deleted locally.

## Synchronizing tags with Django

Synchronize every Django repository with the tags currently stored in
Distribution:

```bash
python manage.py sync_tags
```

Synchronize only one repository by its full Registry name:

```bash
python manage.py sync_tags --repo user/reponame
python manage.py sync_tags --repo official-alpine
```

The command creates new `Tag` records, updates digest and compressed size
metadata, and removes database tags that no longer exist in Distribution.
