"""Hardened HTTPS client used for every download.

Security properties (see CLAUDE.md, "Security rules"):
  * HTTPS only; plain HTTP is rejected before any connection is made.
  * Exact host allow-list: only hosts explicitly passed by the caller.
  * Certificate + hostname verification always on, TLS >= 1.2.
  * Redirects are never followed (a redirect could leave the allow-list).
  * Hard timeout and hard response size limit (streamed, never trusts
    Content-Length alone).
  * No credentials in URLs; callers pass API keys via headers.

Pure Python (stdlib only, optional ``certifi``); no aqt/anki imports.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .i18n import tr

DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_BYTES = 6 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class DownloadError(Exception):
    """Any failure while downloading. Message is safe to show to the user."""


@dataclass
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def content_type(self) -> str:
        return (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def make_ssl_context(cafile: str | None = None) -> ssl.SSLContext:
    """Verified TLS context. Uses certifi's CA bundle when available."""
    if cafile is None:
        try:
            import certifi  # bundled with Anki

            cafile = certifi.where()
        except Exception:
            cafile = None
    ctx = ssl.create_default_context(cafile=cafile)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        raise DownloadError(tr("net.redirect", code=code))


def check_url(url: str, allowed_hosts: Iterable[str]) -> urllib.parse.SplitResult:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise DownloadError(tr("net.https_only"))
    if parts.username or parts.password:
        raise DownloadError(tr("net.no_credentials"))
    host = (parts.hostname or "").lower()
    if not host or host not in {h.lower() for h in allowed_hosts}:
        raise DownloadError(tr("net.host_not_allowed", host=host))
    return parts


def request(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    method: str = "GET",
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    ssl_context: ssl.SSLContext | None = None,
    accept_error_body: bool = False,
) -> Response:
    """Perform one hardened HTTPS request and return the full response.

    Non-2xx responses raise DownloadError unless ``accept_error_body`` is set
    (used to read JSON error messages from APIs).
    """
    check_url(url, allowed_hosts)
    ctx = ssl_context or make_ssl_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        _NoRedirect(),
    )
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)

    try:
        resp = opener.open(req, timeout=timeout)
    except DownloadError:
        raise
    except urllib.error.HTTPError as e:
        if accept_error_body:
            body = _read_limited(e, max_bytes)
            return Response(e.code, dict(e.headers or {}), body)
        raise DownloadError(tr("net.http_status", code=e.code)) from None
    except ssl.SSLError as e:
        raise DownloadError(tr("net.tls", reason=e.reason or e)) from None
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLError):
            raise DownloadError(tr("net.tls", reason=reason.reason or reason)) from None
        raise DownloadError(tr("net.connect", reason=reason)) from None
    except TimeoutError:
        raise DownloadError(tr("net.timeout")) from None
    except OSError as e:
        raise DownloadError(tr("net.network", reason=e)) from None

    with resp:
        # Defence in depth: make sure we really ended up where we wanted.
        check_url(resp.geturl(), allowed_hosts)
        declared = resp.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise DownloadError(tr("net.too_big"))
        body = _read_limited(resp, max_bytes)
        return Response(resp.status, dict(resp.headers), body)


def _read_limited(fp, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = fp.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise DownloadError(tr("net.too_big"))
            chunks.append(chunk)
    except DownloadError:
        raise
    except TimeoutError:
        raise DownloadError(tr("net.timeout")) from None
    except OSError as e:
        raise DownloadError(tr("net.network", reason=e)) from None
    return b"".join(chunks)
