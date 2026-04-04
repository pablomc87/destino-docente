"""
Rewrite Host when clients target the pod by cluster IP (e.g. 10.42.x.x:8000).
Prevents DisallowedHost from kube-proxy, Traefik backends, or probes without a custom Host header.
"""

import ipaddress
import os


class RewriteInternalKubernetesHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        raw = os.environ.get("K8S_INTERNAL_HOST_FALLBACK", "127.0.0.1")
        self.fallback_host = raw.split(":")[0]

    def __call__(self, request):
        if os.environ.get("ALLOW_K8S_INTERNAL_HOST_REWRITE", "true").lower() not in (
            "1",
            "true",
            "yes",
        ):
            return self.get_response(request)

        raw = request.META.get("HTTP_HOST", "")
        if not raw:
            return self.get_response(request)

        host_part = raw.split(":")[0]
        parsed_ip = None
        try:
            parsed_ip = ipaddress.ip_address(host_part)
        except ValueError:
            pass  # Normal hostname (e.g. destino-docente.org) — no rewrite

        if parsed_ip is not None and (
            parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local
        ):
            request.META["HTTP_HOST"] = self.fallback_host

        return self.get_response(request)
