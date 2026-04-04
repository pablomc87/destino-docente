# Security audit report — Destino Docente

**Date:** 2026-04-04  
**Scope:** Application ([`destino-docente`](../)), deployment references ([`kubernetes-homelab`](https://github.com/pablomc87/kubernetes-homelab) Terraform), and **live checks** against `https://destino-docente.org`.

---

## Executive summary

This pass implemented the agreed **hardening and cleanup** in code: removed dead Heroku configuration, reduced information disclosure (logs, API errors, HTML errors), fixed password-reset user enumeration, scoped API usage metrics per user or client IP, added **REST_FRAMEWORK** defaults with throttling, and applied **targeted rate limits** to suggestion POSTs and Google tracking POSTs. **Server-side SSRF** was reviewed: outbound calls use the **Google Maps client** with coordinates only—no user-controlled URLs.

Production was probed with **non-destructive** `curl` requests. **Full benefit requires deploying** the new image to the cluster; live responses below reflect **pre-deploy** behavior where noted.

---

## Threat summary

| Area | Risk (before) | Mitigation applied |
|------|----------------|-------------------|
| Unauthenticated DB writes | `track_google_api` and suggestion APIs accepted abuse | Throttles (`google_track`, `suggestions`) + global anon/user DRF throttles |
| Information disclosure | `str(e)` in JSON/HTML, `print()` to stdout, DEBUG loggers | Generic client messages; server-side `logger.exception`; log levels tied to `DEBUG` |
| User enumeration | Password reset revealed unknown emails | Removed pre-check; Django’s flow + same success path |
| Operational metrics leak | `check_api_limits` summed **all** `APICall` rows | Scoped to **authenticated user** or **anonymous IP** |
| Session probe | `check_session` logged secrets; errors returned 200 | Removed sensitive logs; errors → **503** |
| Host / legacy platform | Heroku `ALLOWED_HOSTS = ['*']` if `DYNO` set | Heroku branches **removed** |
| Transport / headers | Incomplete hardening on prod profile | `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`; HSTS when `SECURE_SSL_REDIRECT` is true |
| Contact PII in defaults | Hardcoded default `CONTACT_EMAIL` | Default `''`; Terraform optional `destino_docente_contact_email` |
| Mass assignment | `SchoolSuggestionSerializer` used `fields = '__all__'` | Explicit `fields` list |

**Cloudflare Tunnel / LAN:** The public site is behind **Cloudflare** → **tunnel** → origin. Tests did not find a parameter that makes Django fetch an arbitrary URL; **LAN scanning via the browser app alone** is therefore not supported by current code paths. Residual risk is unchanged for any future feature that adds **user-controlled URL fetch**.

---

## Dynamic tests (`https://destino-docente.org`)

| Test | Result |
|------|--------|
| `GET /health/` | **200** JSON; headers: `server: cloudflare`, `x-frame-options: DENY`, `x-content-type-options: nosniff`, `referrer-policy: same-origin` |
| `HEAD /admin/` | **302** to login (expected) |
| `GET /api/check-limits/` | **200** JSON (pre-deploy: still **global** usage counts; per-IP/user after deploy) |
| `POST /api/track-google-api/` | **200** `{"status":"success"}` with minimal JSON body (pre-deploy: **no** app throttle yet; throttled after deploy) |

No SSRF-style probes returned internal banners in responses from tested parameters (nearest/search use structured fields, not raw URLs).

---

## Security score (0–100)

**Score: 78 / 100** (post-code-change, assuming deployment and `CONTACT_EMAIL` / TLS settings aligned with ops).

| Criterion | Max | Score | Notes |
|-----------|-----|-------|-------|
| Identity & session | 20 | 15 | CSRF middleware on; secure cookies env-driven; session check no longer leaks to logs |
| Data exposure | 20 | 16 | API/HTML errors generic; limits scoped in code |
| Input validation & authz | 20 | 14 | Public read APIs by design; writes throttled; admin still needs strong passwords + optional IP lock |
| Transport & headers | 15 | 11 | Django `SECURE_*` improved; edge headers seen on live site; cluster `SECURE_SSL_REDIRECT` may differ from Cloudflare—verify cookie/CSRF flags |
| Logging & errors | 15 | 14 | Production log levels no longer forced DEBUG for noisy loggers |
| Supply chain & deploy | 10 | 8 | Image via GHCR; Terraform secrets pattern sound; rotate keys if ever leaked |

---

## Django `manage.py check --deploy`

With `ENVIRONMENT=development`, deploy checks are **silenced** for local HTTP/`DEBUG` noise; use **`./scripts/check_deploy.sh`** for a production-style run (Cloudflare-terminated TLS, secure cookies, HSTS) with **no issues** (plus documented silences for **W008** / **W021**). See [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Residual recommendations

1. **Deploy** the new container and confirm `429` under heavy `POST` to `/api/track-google-api/` and suggestion endpoints.
2. Set **`CONTACT_EMAIL`** in Kubernetes (Terraform variable `destino_docente_contact_email`) so contact mail works.
3. **Google Maps API key:** HTTP referrer restrictions and quota alerts in Google Cloud.
4. **Dependency scanning:** e.g. `pip-audit` or GitHub Dependabot.
5. **Admin:** strong passwords, 2FA on provider accounts, optional IP allowlist at Cloudflare or Traefik.
6. **Rate limits at edge:** Cloudflare WAF / rate rules for `/api/` if abuse continues.

---

## Files touched (reference)

- [`config/settings.py`](../config/settings.py) — Heroku removed, `REST_FRAMEWORK`, logging, security headers, `CONTACT_EMAIL` default.
- [`schools/views/background_operations.py`](../schools/views/background_operations.py) — errors, limits scope, throttle on track.
- [`schools/views/school_views.py`](../schools/views/school_views.py) — prints removed, throttles, `get_object_or_404`.
- [`schools/serializers.py`](../schools/serializers.py) — explicit fields, prints removed.
- [`schools/throttles.py`](../schools/throttles.py) — new throttle classes.
- [`schools/views/render_templates.py`](../schools/views/render_templates.py) — generic HTML errors, contact logging.
- [`users/views.py`](../users/views.py) — password reset, `check_session`, login log line.
- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md), [`docs/migration-from-heroku.md`](migration-from-heroku.md) — Heroku de-emphasized.
- [`kubernetes-homelab/terraform/destino-docente.tf`](../../kubernetes-homelab/terraform/destino-docente.tf) — optional `CONTACT_EMAIL` in Secret.
- **Removed:** [`Procfile`](../Procfile) (legacy Heroku).
