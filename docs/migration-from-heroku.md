# Migrate PostgreSQL data from Heroku to the cluster

One-time logical copy from **Heroku Postgres** into the **Bitnami PostgreSQL** Helm release in namespace `destino-docente`.

## Checklist (order)

1. On Heroku, run migrations so the dump matches code: `heroku run python manage.py migrate -a destino-docente`
2. Save `DATABASE_URL` from Heroku (`heroku config:get DATABASE_URL -a destino-docente`).
3. `pg_dump` from your laptop into a **custom** `.dump` file (below).
4. `kubectl port-forward` to `svc/destino-docente-postgresql` (or use a Job on the cluster).
5. `pg_restore` as **`postgres`** into database **`destino_docente`** with `--no-owner --no-acl`.
6. **`REASSIGN OWNED BY postgres TO destino_docente;`** so the app user owns tables (Django uses `destino_docente`, not `postgres`).
7. Restart web pods / let Argo roll; `migrate` should be mostly no-ops.
8. Smoke-test admin, login, and a few pages **before** you point public DNS at the new site.
9. After traffic is on the cluster and you are happy, decommission Heroku (§9).

## Prerequisites

- `pg_dump` / `pg_restore` on your laptop (major version **≥** Heroku Postgres is safest).
- `kubectl` pointed at the homelab cluster.
- Postgres running in `destino-docente`; DB `destino_docente` already exists (Bitnami creates it).

## 1. Capture Heroku credentials

```bash
heroku config:get DATABASE_URL -a destino-docente
```

Do not commit this URL.

## 2. Dump from Heroku

```bash
export HEROKU_DATABASE_URL='postgres://...'
pg_dump --no-owner --no-acl --format=custom -d "$HEROKU_DATABASE_URL" -f destino-docente.dump
```

Heroku normally uses **SSL**; the URL usually includes that. Keep the dump file off git (already in `.gitignore` patterns for `*.dump`).

## 3. Port-forward in-cluster Postgres

```bash
kubectl port-forward -n destino-docente svc/destino-docente-postgresql 5433:5432
```

Adjust the service name if your release name differs (`kubectl get svc -n destino-docente`).

## 4. Restore

Superuser password: Secret `destino-docente-credentials`, key **`postgres-password`** (decode with `kubectl get secret … | base64 -d`).

**Always capture stderr** so you can see what failed:

```bash
export PGPASSWORD='<postgres-password>'
pg_restore --no-owner --no-acl -h 127.0.0.1 -p 5433 -U postgres -d destino_docente --verbose destino-docente.dump 2>&1 | tee restore.log
```

`pg_restore` applies objects **one by one**; later steps can succeed even if earlier ones error, so you can end up with **most** data but **missing** indexes, constraints, triggers, or specific tables.

If restore errors on **existing** objects (second run into a non-empty DB), drop and recreate the database, then restore once into a **clean** `destino_docente`.

### Critical: restore into an **empty** database only

If the cluster database already has tables (e.g. you ran **Django `migrate`** first, or a failed restore left objects behind), `pg_restore` will:

1. Fail **`CREATE TABLE` / `CREATE SEQUENCE`** with **“already exists”**.
2. Still run **`COPY`** into those tables → **“duplicate key value violates unique constraint”** on primary keys.
3. Leave you with **old cluster rows**, not a full replace of Heroku data — and **inconsistent** partial loads (some `COPY` lines succeed on empty tables, others fail).

**Fix:** wipe `public` (or drop/recreate database `destino_docente`), then run **one** full `pg_restore` **before** relying on the app. Do **not** run `migrate` on the empty DB first if you are loading a full Heroku dump that already includes schema + data (the dump carries `django_migrations`). After restore, run **`REASSIGN OWNED BY postgres TO destino_docente;`**, then start Django (its `migrate` should be no-ops if versions match).

Example wipe of the app schema (superuser, port-forward as usual):

```sql
DROP SCHEMA IF EXISTS _heroku CASCADE;
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
GRANT ALL ON SCHEMA public TO destino_docente;
```

Then `pg_restore` again from your `.dump` file. If `_heroku` is absent, the first line is a no-op.

### Common `pg_restore` messages (often harmless with `--no-owner --no-acl`)

| Message | Meaning |
|--------|---------|
| `role "u…" does not exist` | Expected if Heroku used app roles you did not create locally; data may still load. |
| `must be owner of …` | Usually ACL/owner; try superuser `postgres` and `--no-owner --no-acl`. |
| `already exists` | Target DB was not empty; objects skipped or partially applied — **prefer a fresh DB** and one restore. |
| `extension "…" does not exist` | Heroku may ship extensions (e.g. `pg_stat_statements`); install in cluster or ignore if optional. |
| `ERROR` on one table | That table (or constraint) may be incomplete — compare row counts below. |

List what is inside the dump (table of contents):

```bash
pg_restore -l destino-docente.dump | less
```

### If you already restored with errors — see what you have

Run on **both** Heroku and the cluster (same SQL). On Heroku:

```bash
heroku pg:psql -a destino-docente
```

On the cluster (with port-forward as in §3):

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d destino_docente
```

**1) Tables present in `public`**

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Compare the two sides: any table **missing** on the cluster was not created or was dropped.

**2) Approximate row counts** (fast; run `ANALYZE;` first if numbers look stale)

```sql
SELECT relname AS table_name, n_live_tup::bigint AS approx_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;
```

**3) Exact counts on important Django tables** (adjust names if you renamed models; these match this project’s `db_table` / defaults)

```sql
SELECT
  (SELECT COUNT(*) FROM auth_user)                         AS auth_user,
  (SELECT COUNT(*) FROM schools)                           AS schools,
  (SELECT COUNT(*) FROM school_studies)                    AS school_studies,
  (SELECT COUNT(*) FROM imparted_studies)                  AS imparted_studies,
  (SELECT COUNT(*) FROM school_suggestions)                AS school_suggestions,
  (SELECT COUNT(*) FROM school_edit_suggestions)           AS school_edit_suggestions,
  (SELECT COUNT(*) FROM search_history)                    AS search_history,
  (SELECT COUNT(*) FROM schools_apicall)                   AS schools_apicall,
  (SELECT COUNT(*) FROM django_migrations)                 AS django_migrations,
  (SELECT COUNT(*) FROM users_usersubscription)            AS users_usersubscription;
```

If a `SELECT` errors with “relation does not exist”, drop that line — table names must match your DB (`\dt` in `psql`). `APICall` uses Django’s default table **`schools_apicall`**, not `apicall`.

Mismatch vs Heroku → that table’s data or constraints failed during restore; consider a **clean DB + single full restore** after fixing extension/role issues, or restore only missing tables from a custom-format dump (`pg_restore -t tablename …`).

**4) Django check**

```bash
python manage.py showmigrations --plan
```

Run against each environment (Heroku vs cluster) with the right `DATABASE_URL`. No pending migrations on either is ideal after restore.

## 5. Reassign ownership to the app user

Django connects as **`destino_docente`**. After restore, objects are often owned by **`postgres`**.

PostgreSQL allows **one owner per object** — there is no “co-owner.” You either **change owner** or **grant** privileges.

### Try this first

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d destino_docente -c "REASSIGN OWNED BY postgres TO destino_docente;"
```

Same `PGPASSWORD` (postgres superuser) as above.

### If you get: `cannot reassign ownership of objects owned by role postgres because they are required by the database system`

Bulk `REASSIGN` refuses to move some objects (e.g. database-level or extension-related). Do this instead:

**1) Database owner** (run connected to **`postgres`**, not `destino_docente`):

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -c "ALTER DATABASE destino_docente OWNER TO destino_docente;"
```

**2) Everything else in `public` still owned by `postgres`** — from `psql` on `destino_docente`, paste and run (uses `\gexec` to run generated `ALTER` statements):

```sql
SELECT format('ALTER TABLE %s OWNER TO destino_docente', c.oid::regclass)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'S', 'v', 'p')
  AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = 'postgres');
\gexec

SELECT format('ALTER FUNCTION %s OWNER TO destino_docente', p.oid::regprocedure)
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proowner = (SELECT oid FROM pg_roles WHERE rolname = 'postgres');
\gexec
```

If you have materialized views or foreign tables in `public`, use `ALTER MATERIALIZED VIEW` / `ALTER FOREIGN TABLE` for those instead of `ALTER TABLE`.

If you use composite types in `public` owned by `postgres`, add a similar loop for `pg_type` / `ALTER TYPE` (rare for stock Django).

**3) Optional:** `ALTER SCHEMA public OWNER TO destino_docente;` if you want the app user to own the schema (not always required if tables are owned and grants are correct).

### If Django reports `permission denied for table …`

That means **`destino_docente` has no privileges** on objects still owned by **`postgres`** (typical after `pg_restore --no-owner --no-acl` if ownership was not fully transferred). As **`postgres`** on **`destino_docente`**:

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d destino_docente -v ON_ERROR_STOP=1 <<'SQL'
GRANT USAGE ON SCHEMA public TO destino_docente;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO destino_docente;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO destino_docente;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO destino_docente;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL PRIVILEGES ON TABLES TO destino_docente;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL PRIVILEGES ON SEQUENCES TO destino_docente;
SQL
```

Prefer fixing **ownership** (steps above) when you can; **`GRANT ALL`** is a reliable fallback so the app can read/write immediately.

## 6. Migrations

- Heroku should already be migrated before the dump.
- After restore, the web container runs `migrate --noinput` on start; expect **no pending migrations** if versions match.

## 7. Verify

- Run the **SQL comparisons** in §4 after a noisy restore.
- Django admin: user count, a few schools, search history if you use it.
- Compare critical screens with Heroku **while Heroku still serves prod** if you can.

## 8. SSL / `DATABASE_URL`

- **Heroku**: URL uses TLS to managed Postgres.
- **In-cluster Django**: uses the Terraform-built `DATABASE_URL` (Secret `destino-docente-app-env`) pointing at the **Kubernetes service** — typically **`sslmode=disable`**. Do **not** point Django at the Heroku URL after cutover.

## 9. Decommission Heroku (after cutover)

Do this only when **DNS / Cloudflare** already send real users to the cluster, you have a **recent cluster backup** (see `docs/DEPLOYMENT.md`), and you are satisfied with smoke tests on the new site.

1. **Stop new deploys to Heroku** — remove or disable GitHub → Heroku auto-deploy, `git push heroku`, Review Apps, and any CI job that deploys there so you do not overwrite prod by mistake.
2. **Optional last export** — if you want a final archive: `pg_dump` from Heroku one more time (§2) and store the file somewhere safe (not in git).
3. **Heroku add-ons** — in the Heroku dashboard or CLI, remove **Postgres**, **Redis** (if any), **scheduler**, etc., or destroy the app (below) which tears down add-ons with it.
4. **Destroy the app** — dashboard **Settings → Delete app**, or:
   ```bash
   heroku apps:destroy destino-docente --confirm destino-docente
   ```
   Replace `destino-docente` with your real app name if it differs.
5. **Clean up local remotes** — `git remote remove heroku` (and drop Heroku-specific env files from your machine if you still have them).
6. **Secrets** — cluster `DJANGO_SECRET_KEY` and DB passwords are already separate from Heroku; rotate anything you ever pasted into Heroku **and** still use elsewhere (email SMTP, API keys) if you want zero reuse.

Heroku billing stops for that app once it is destroyed; confirm in the Heroku account **Billing** view.

## Optional: sync job instead of laptop

If you upload the dump to object storage, you can run a one-off `pg_restore` Job in the cluster; the port-forward + laptop flow above is enough for most one-time migrations.
