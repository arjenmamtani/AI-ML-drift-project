"""
Rate limiting using slowapi (Starlette-compatible wrapper around limits).

Limits:
  - Ingestion endpoints  : 1000 requests/minute (high volume expected)
  - Drift compute        : 60/minute (expensive operation)
  - Training trigger     : 10/minute (very expensive)
  - Auth endpoints       : 20/minute (brute-force protection)
  - General default      : 200/minute

All limits are per IP address. In production behind a load balancer,
configure X-Forwarded-For parsing so you get the real client IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
