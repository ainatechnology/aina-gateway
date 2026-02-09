"""
aina-gateway authentication & IP filtering middleware.

Phase 2a: BearerTokenMiddleware - API key auth for LAN/VM access
Phase 2c: IPWhitelistMiddleware - IP-based filtering for tunnel access

Security layers (applied in order):
1. IP Whitelist - blocks requests from unknown IPs (outermost)
2. Bearer Token - validates API key for LAN access (innermost)
   → Anthropic IPs are exempt from Bearer auth (tunnel = authless)

Auth matrix:
    | Source          | IP Whitelist | Bearer Token |
    |-----------------|-------------|--------------|
    | Anthropic (tunnel) | ✅ checked  | ⏭️ skipped   |
    | LAN (direct)       | ✅ checked  | ✅ checked   |
    | localhost          | ✅ checked  | ⏭️ skipped   |
"""

import ipaddress
import logging
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("aina-gateway.auth")

# ---------------------------------------------------------------------------
# Anthropic's official outbound IPs for MCP tool calls
# Source: https://platform.claude.com/docs/en/api/ip-addresses
# ---------------------------------------------------------------------------
ANTHROPIC_CIDRS = [
    "160.79.104.0/21",
    # Legacy IPs (phasing out since 2026-01-15, kept for safety)
    "34.162.46.92/32",
    "34.162.102.82/32",
    "34.162.136.91/32",
    "34.162.142.92/32",
    "34.162.183.95/32",
]

# Loopback CIDRs (always trusted, exempt from Bearer auth)
LOOPBACK_CIDRS = [
    "127.0.0.0/8",       # IPv4 loopback
    "::1/128",           # IPv6 loopback
]

# Default private/local CIDRs (LAN - require Bearer auth)
LAN_CIDRS = [
    "10.0.0.0/8",        # RFC1918 Class A
    "172.16.0.0/12",     # RFC1918 Class B
    "192.168.0.0/16",    # RFC1918 Class C
]


def _parse_networks(cidrs: list[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse CIDR strings into network objects."""
    nets = []
    for cidr in cidrs:
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError as e:
            logger.warning(f"Invalid CIDR '{cidr}': {e}")
    return nets


# Pre-parsed network lists for reuse
ANTHROPIC_NETWORKS = _parse_networks(ANTHROPIC_CIDRS)
LOOPBACK_NETWORKS = _parse_networks(LOOPBACK_CIDRS)


def _build_whitelist() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    Build the IP whitelist from defaults + optional env var.

    Set ALLOWED_IPS in .env to add custom CIDRs (comma-separated):
        ALLOWED_IPS=203.0.113.0/24,198.51.100.42/32
    """
    cidrs = ANTHROPIC_CIDRS + LOOPBACK_CIDRS + LAN_CIDRS

    extra = os.getenv("ALLOWED_IPS", "").strip()
    if extra:
        cidrs += [c.strip() for c in extra.split(",") if c.strip()]

    return _parse_networks(cidrs)


def _get_client_ip(request: Request) -> str:
    """
    Extract the real client IP.

    Cloudflare sets CF-Connecting-IP (most reliable) and
    X-Forwarded-For. We trust these because traffic comes
    through our own Cloudflare Tunnel.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    return request.client.host if request.client else "0.0.0.0"


def _ip_in_networks(ip_str: str, networks: list) -> bool:
    """Check if an IP address is in any of the given networks."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in network for network in networks)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Blocks requests from IPs not in the whitelist.

    Checks CF-Connecting-IP / X-Forwarded-For first,
    falls back to the direct client IP.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.whitelist = _build_whitelist() if enabled else []
        if enabled:
            logger.info(
                f"IP Whitelist active: {len(self.whitelist)} network(s) allowed"
            )

    def _is_allowed(self, ip_str: str) -> bool:
        """Check if an IP address is in any whitelisted network."""
        return _ip_in_networks(ip_str, self.whitelist)

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client_ip = _get_client_ip(request)

        if not self._is_allowed(client_ip):
            logger.warning(f"Blocked request from {client_ip}")
            return JSONResponse(
                {"error": "Access denied"},
                status_code=403,
            )

        return await call_next(request)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """
    Validates Bearer token in Authorization header.

    Exempt from auth:
    - When API_KEY is empty (authless mode)
    - Requests from Anthropic IPs (tunnel access, protected by IP whitelist)
    - Requests from localhost (loopback)

    Requires auth:
    - LAN requests (Claude Desktop, scripts, etc.)
    """

    def __init__(self, app, api_key: str = ""):
        super().__init__(app)
        self.api_key = api_key
        self.auth_enabled = bool(api_key)

    def _is_auth_exempt(self, request: Request) -> bool:
        """Check if request comes from a trusted source that doesn't need Bearer auth."""
        client_ip = _get_client_ip(request)
        # Anthropic IPs (via Cloudflare Tunnel) → already protected by IP whitelist
        if _ip_in_networks(client_ip, ANTHROPIC_NETWORKS):
            return True
        # Localhost → trusted
        if _ip_in_networks(client_ip, LOOPBACK_NETWORKS):
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        if not self.auth_enabled:
            return await call_next(request)

        # Skip Bearer auth for trusted sources
        if self._is_auth_exempt(request):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ")

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(token, self.api_key):
            return JSONResponse({"error": "Invalid API key"}, status_code=403)

        return await call_next(request)
