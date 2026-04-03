# Migrate PostgreSQL data from Heroku to the cluster

One-time logical migration: dump from **Heroku Postgres**, restore into the **Bitnami PostgreSQL** instance installed by Helm in namespace `destino-docente`.

## Prerequisites

- `pg_dump` and `pg_restore` installed locally (version compatible with Heroku’s Postgres major version).
- `kubectl` configured for the homelab cluster.
- Helm release synced so **PostgreSQL is running** and the target database exists (e.g. `destino_docente`).

## 1. Capture Heroku credentials

From the Heroku dashboard or CLI:

```bash
heroku config:get DATABASE_URL -a destino-docente
```

Treat this URL as a **secret**. Do not commit it.

## 2. Dump from Heroku

Custom format (recommended):

```bash
export HEROKU_DATABASE_URL='postgres://...'
pg_dump --no-owner --no-acl --format=custom -d "$HEROKU_DATABASE_URL" -f destino-docente.dump
```

Heroku usually requires **SSL**; `pg_dump` follows the URL.

## 3. Port-forward in-cluster Postgres

Replace service name if your Helm release name differs (`kubectl get svc -n destino-docente`):

```bash
kubectl port-forward -n destino-docente svc/destino-docente-postgresql 5433:5432
```

## 4. Restore

Use the **postgres** user password from your Terraform / Kubernetes secret (`destino-docente-credentials`, key `postgres-password`), not the Heroku URL.

```bash
export PGPASSWORD='...'
pg_restore --no-owner --no-acl -h 127.0.0.1 -p 5433 -U postgres -d destino_docente --verbose destino-docente.dump
```

If the target DB is empty and restore complains about roles, `--no-owner --no-acl` (above) is usually enough.

Django connects as the **application user** `destino_docente` (not the `postgres` superuser). After a restore, objects are often still owned by `postgres`. Reassign ownership so migrations and the app work:

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d destino_docente -c "REASSIGN OWNED BY postgres TO destino_docente;"
```

(Use the same port-forward and `PGPASSWORD` as above.)

## 5. Migrations vs dump

- Prefer Heroku to be **fully migrated** before the dump (`heroku run python manage.py migrate`).
- After restore, start the Django pod; its entrypoint runs `migrate --noinput` (should be no-ops if the dump already matches migrations).

## 6. Verify

- Row counts / spot-check in Django admin.
- Test login and a few critical pages before switching DNS.

## 7. SSL note

- Heroku: `DATABASE_URL` typically needs `sslmode=require`.
- In-cluster Django: use the **in-cluster** `DATABASE_URL` from Terraform (usually **no** SSL to the service). Do not reuse the Heroku URL in production.
