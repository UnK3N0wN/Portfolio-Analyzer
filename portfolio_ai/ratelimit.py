"""
portfolio_ai/ratelimit.py

Lightweight cache-based rate limiter.

Uses whatever CACHES['default'] backend is configured — LocMemCache today,
Redis once Phase 1 (django-redis) lands, with no code changes required here.
This is intentionally dependency-free; if the project later adopts
django-ratelimit or DRF throttling classes wholesale, this can be retired.

NOTE: LocMemCache is per-process. Behind multiple gunicorn workers or
multiple app servers, each process enforces its own limit independently,
so the *effective* combined limit is (limit * worker_count) until the
cache backend is switched to Redis in Phase 1. Treat this as a stop-gap,
not a hard guarantee, until then.
"""
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse


def _client_ip(request):
    """Best-effort client IP, respecting a trusted reverse proxy header."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(key_prefix, limit=10, window=60, key_func=None):
    """
    Decorator: allow at most `limit` requests per `window` seconds per
    client, identified by `key_func(request)` (defaults to client IP).

    Usage:
        @rate_limit('login', limit=10, window=300)
        def login_view(request): ...

        @rate_limit('ai_chat', limit=20, window=60,
                    key_func=lambda r: r.user.id if r.user.is_authenticated else _client_ip(r))
        def ai_chat(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            identity  = key_func(request) if key_func else _client_ip(request)
            cache_key = f'ratelimit:{key_prefix}:{identity}'

            count = cache.get(cache_key, 0)
            if count >= limit:
                return HttpResponse(
                    'Too many requests. Please wait a bit and try again.',
                    status=429,
                    content_type='text/plain',
                )

            try:
                # incr() is atomic where the backend supports it (avoids a
                # race between concurrent requests reading the same count).
                cache.incr(cache_key)
            except ValueError:
                # Key doesn't exist yet.
                cache.set(cache_key, 1, window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator