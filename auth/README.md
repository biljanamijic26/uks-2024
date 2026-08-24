# Registry authentication

The `registry` service in `docker-compose.yml` reads htpasswd credentials
from `auth/htpasswd`. That file is generated locally and is not committed
(see `.gitignore`).

Generate it before starting the stack, using the credentials from your
`.env` (`REGISTRY_USERNAME` / `REGISTRY_PASSWORD`):

```bash
docker run --rm httpd:2.4-alpine htpasswd -Bbn admin Admin123 > auth/htpasswd
```

**Windows PowerShell:** `>` is `Out-File`, which defaults to UTF-16LE with a
BOM and breaks the registry's htpasswd parser (login fails with
`400 Bad Request`). Use `Set-Content` with an explicit ASCII encoding
instead:

```powershell
docker run --rm httpd:2.4-alpine htpasswd -Bbn admin Admin123 | Set-Content -Path auth\htpasswd -Encoding ascii -NoNewline
```

If you already generated the file with `>` in PowerShell, regenerate it with
the command above and restart the registry container so it re-reads the file.
