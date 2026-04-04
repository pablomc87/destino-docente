#!/usr/bin/env bash
# Dump the `schools` app from the in-cluster Django DB (PostgreSQL) into a JSON fixture.
# Requires: kubectl configured, namespace destino-docente, deployment destino-docente-web running.
#
# Usage:
#   ./scripts/dump_schools_from_cluster.sh [output.json]
#   KUBECTL_NAMESPACE=my-ns ./scripts/dump_schools_from_cluster.sh
#
# Then locally (SQLite, ENVIRONMENT=development, no DATABASE_URL):
#   python manage.py migrate
#   python manage.py loaddata path/to/output.json

set -euo pipefail

NS="${KUBECTL_NAMESPACE:-destino-docente}"
DEPLOY="${KUBECTL_DEPLOY:-destino-docente-web}"
OUT="${1:-fixtures/cluster_schools.json}"

mkdir -p "$(dirname "$OUT")"

echo "Dumping from namespace=$NS deployment/$DEPLOY into $OUT ..." >&2

kubectl exec -n "$NS" "deploy/$DEPLOY" -- \
  python manage.py dumpdata schools \
  --exclude schools.searchhistory \
  --exclude schools.apicall \
  --indent 2 >"$OUT"

echo "Wrote $OUT ($(wc -c <"$OUT") bytes)" >&2
echo "Local load: ENVIRONMENT=development python manage.py loaddata $OUT" >&2
