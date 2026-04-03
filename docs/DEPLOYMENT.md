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

## PostgreSQL backups

The Helm chart installs a **weekly CronJob** that runs `pg_dump` into a PVC (`destino-docente-pg-backups`). Copy dumps off the node periodically so a disk loss does not take backups with it. To restore from a custom-format dump: use `pg_restore` against the in-cluster service (e.g. via `kubectl port-forward`) with the postgres password from Secret `destino-docente-credentials`.

## PostgreSQL inside the cluster

The **Bitnami PostgreSQL** subchart creates, on first startup:

- Database **`destino_docente`** (`postgresql.auth.database` in the Helm values).
- User **`destino_docente`** with password from Secret key `password`.
- Superuser **`postgres`** with password from Secret key `postgres-password` (backups / restores / admin).

Terraform builds `DATABASE_URL` so Django uses **`destino_docente@…/destino_docente`**. If you rename the database in Helm, set Terraform variable **`destino_docente_database_name`** to the same name.

## Required environment variables (cluster)

Managed via Terraform-generated Secret `destino-docente-app-env` (names may match your chart values):

- `DATABASE_URL` — in-cluster PostgreSQL (app DB and app user above; not the `postgres` superuser)
- `DJANGO_SECRET_KEY`
- `REDIS_URL` — optional; when set, Django uses Valkey for cache
- `ENVIRONMENT=production`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `TRUST_BEHIND_PROXY=true` when TLS terminates at Cloudflare / Traefik
