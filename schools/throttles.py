"""DRF throttle scopes for abuse-prone endpoints (rates from REST_FRAMEWORK)."""

from rest_framework.throttling import SimpleRateThrottle


class SuggestionRateThrottle(SimpleRateThrottle):
    scope = "suggestions"


class GoogleTrackRateThrottle(SimpleRateThrottle):
    scope = "google_track"
