# Production deployment (Kubernetes / homelab)

Production runs on **Kubernetes** (single-node k3s is fine) using the **Helm chart** under `deploy/helm/destino-docente/` and **Argo CD** in the [kubernetes-homelab](https://github.com/pablomc87/kubernetes-homelab) repository.

## Source of truth

- **`main` on your canonical Git host** (e.g. GitHub): triggers **CI** to build and push the **container image** (see `.github/workflows/docker-publish.yml`).
- **Argo CD** syncs the Helm release from Git; the cluster state is declared there—not via `git push heroku`.

## Leaving Heroku

1. Add a **GitHub (or GitLab) remote** and push `main` there; make that the default `upstream` for day-to-day work.
2. In the **Heroku dashboard**, **disable automatic deploys** from GitHub and stop using `git push heroku` as your normal release path.
3. After DNS and traffic point at the cluster, scale down or remove the Heroku app.

Database copy: see [migration-from-heroku.md](migration-from-heroku.md).

## Apply order (first time)

1. **Cluster bootstrap** (if not already done): from `kubernetes-homelab`, run `ansible-playbook ansible/playbooks/bootstrap-k3s-argocd.yml` (see that playbook’s inventory/README). Point `kubectl` at the cluster (e.g. copy `/etc/rancher/k3s/k3s.yaml` from the node or use your `kubeconfig`).
2. **Push both repos to GitHub** (or your Git host). Argo CD expects public URLs in `argocd/applications/destino-docente.yaml` (`pablomc87/destino-docente` and `pablomc87/kubernetes-homelab`); change those if your forks differ. **Include** `deploy/helm/destino-docente/charts/*.tgz` in commits so Argo can resolve Helm dependencies.
3. **Apply the homelab GitOps root app** (if you have not already): `kubectl apply -f argocd/root-application.yaml` so Argo picks up `argocd/kustomization.yaml` (includes the `destino-docente` Application). If the repos are **private**, add credentials in Argo CD (Settings → Repositories, or a repo Secret) for both Git URLs.
4. **Build the app image**: push `main` on `destino-docente` so GitHub Actions (`.github/workflows/docker-publish.yml`) publishes to **GHCR** `ghcr.io/<owner>/destino-docente`. The cluster must be allowed to pull from GHCR (public image is simplest for a first try).
5. **Terraform** (from your laptop, with kubeconfig): `cd kubernetes-homelab/terraform && terraform init && terraform apply` — creates namespace `destino-docente` and Secrets `destino-docente-credentials`, `destino-docente-app-env`. Do this **before** or right before the first successful Argo sync so the Helm chart finds the secrets.
6. **Argo CD**: open the `destino-docente` Application and **Sync**. Wait until Postgres, Valkey, and the web Deployment are healthy.
7. **Optional data**: load production data with [migration-from-heroku.md](migration-from-heroku.md) when you are ready.
8. **Public access later**: Cloudflare Tunnel or DNS — see `kubernetes-homelab/docs/cloudflare-tunnel-destino-docente.md`. Optional: `ansible/playbooks/optional-cloudflared.yml` on the node.

### Try the site only for you (no public DNS)

- Put the ingress host in `/etc/hosts` on your laptop pointing at the node IP (e.g. `destino-docente.homelab.local`), **or**
- Port-forward and use curl: `kubectl port-forward -n destino-docente svc/destino-docente-web 8080:80` then open `http://127.0.0.1:8080/` (Django may redirect or check hosts; ensure `ALLOWED_HOSTS` in the Terraform secret includes `127.0.0.1` — it already includes `localhost` and `127.0.0.1`).

If the browser sends `Host: 127.0.0.1:8080`, that host must be allowed — already listed. For `Host: destino-docente.homelab.local`, that is also in the default Terraform list.

### Web pod crashes on migrate: `DATABASE_URL` / `dj_database_url`

The app needs a real Postgres URL in the container, e.g. `postgresql://destino_docente:…@destino-docente-postgresql…/destino_docente?sslmode=disable`.

1. Confirm the Secret exists and the key is exactly `DATABASE_URL` (case-sensitive):

   `kubectl get secret destino-docente-app-env -n destino-docente -o jsonpath='{.data.DATABASE_URL}' | base64 -d; echo`

   You should see a string starting with `postgresql://` or `postgres://`.

2. If that is empty or garbage, re-check **Terraform** applied to the same cluster/context as the workload, and that nothing else overwrote the Secret. If the decoded value still looks like base64 text, the Secret was **double-encoded**: `kubernetes_secret` `data` must hold **plain strings** (the provider encodes once); do not wrap values in Terraform `base64encode()`.

3. Confirm the Deployment uses `envFrom.secretRef.name: destino-docente-app-env` (Helm value `web.existingAppSecret`).

### `password authentication failed for user "destino_docente"`

PostgreSQL stores passwords **when the data directory is first created**. Changing Secret `destino-docente-credentials` later (e.g. after fixing Terraform double-encoding or rotating `random_password`) does **not** update existing roles on disk.

**If you have no data to keep:** delete the Postgres PVC and pod so Bitnami re-initializes from the current Secret (this wipes the DB). List PVCs first (`kubectl get pvc -n destino-docente`); the data volume is usually named like `data-destino-docente-postgresql-0`:

```bash
kubectl delete pvc -n destino-docente data-destino-docente-postgresql-0
kubectl delete pod -n destino-docente destino-docente-postgresql-0
# StatefulSet recreates the pod and a fresh PVC; Argo/Helm will keep the release in sync
```

**If you want to keep data:** run the one-shot Job in `kubernetes-homelab` that executes `ALTER USER destino_docente …` using the current Secret `password` (handles special characters safely):

```bash
# From kubernetes-homelab repo
kubectl apply -f gitops/destino-docente/sync-db-password-job.yaml
kubectl wait -n destino-docente --for=condition=complete job/destino-docente-sync-db-password --timeout=120s
kubectl logs -n destino-docente job/destino-docente-sync-db-password
kubectl delete job -n destino-docente destino-docente-sync-db-password
```

Then restart the web Deployment so it retries migrations.

## PostgreSQL backups

The Helm chart does **not** schedule automated database backups. When you need a dump, run `pg_dump` yourself (e.g. `kubectl exec` into the PostgreSQL pod or port-forward to the service) using the `postgres` superuser password from Secret `destino-docente-credentials`.

## PostgreSQL inside the cluster

The **Bitnami PostgreSQL** subchart creates, on first startup:

- Database **`destino_docente`** (`postgresql.auth.database` in the Helm values).
- User **`destino_docente`** with password from Secret key `password`.
- Superuser **`postgres`** with password from Secret key `postgres-password` (restores / admin).

Terraform builds `DATABASE_URL` so Django uses **`destino_docente@…/destino_docente`**. If you rename the database in Helm, set Terraform variable **`destino_docente_database_name`** to the same name.

## Required environment variables (cluster)

Managed via Terraform-generated Secret `destino-docente-app-env` (names may match your chart values):

- `DATABASE_URL` — in-cluster PostgreSQL (app DB and app user above; not the `postgres` superuser)
- `DJANGO_SECRET_KEY`
- `REDIS_URL` — optional; when set, Django uses Valkey for cache
- `ENVIRONMENT=production`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` — include every scheme+host used in the browser (Django 4+ checks `Origin` on POST).
- Optional: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` — Terraform **`destino_docente_cookie_secure`** (default **`true`** for Cloudflare HTTPS; **`false`** for plain-HTTP homelab and extra CSRF origin); see homelab Cloudflare doc.
- `TRUST_BEHIND_PROXY=true` when TLS terminates at Cloudflare / Traefik
- Optional: `ALLOW_K8S_INTERNAL_HOST_REWRITE` (default on) — rewrites `Host` when the request targets the pod/cluster IP so Traefik/backends do not hit `DisallowedHost`. Override `K8S_INTERNAL_HOST_FALLBACK` (default `127.0.0.1`) if that host must not be in `ALLOWED_HOSTS`.

## Next steps after the web pod is healthy

1. **Copy production data from Heroku Postgres** into in-cluster Postgres: [migration-from-heroku.md](migration-from-heroku.md) (dump → port-forward → `pg_restore` → `REASSIGN OWNED`).
2. **Public access via Cloudflare Tunnel**: in `kubernetes-homelab`, follow [docs/cloudflare-tunnel-destino-docente.md](https://github.com/pablomc87/kubernetes-homelab/blob/main/docs/cloudflare-tunnel-destino-docente.md) — install `cloudflared`, create the tunnel, point public hostnames at Traefik on the node (`http://…:80`), then set `ingress.host` / `ingress.extraHosts` in `gitops/destino-docente/helm-values.yaml` to match `destino-docente.org` (and `www`). Re-run **Terraform** if you change `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.
