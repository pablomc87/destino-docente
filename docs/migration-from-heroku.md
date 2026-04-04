# Historical note

This project previously ran on Heroku. Production is now **Kubernetes + Helm** (see [DEPLOYMENT.md](DEPLOYMENT.md)). One-off Postgres migrations from old Heroku dumps used `pg_dump` / `pg_restore`; if you still have a `.dump` file, use standard PostgreSQL restore tooling against your current cluster database—there is no Heroku-specific procedure maintained here.
