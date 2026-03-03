"""Minimal oEmbed consumer — replaces the python-oembed dependency.

Implements just the subset used by this extension:
  - OEmbedEndpoint: pairs an API URL with URL-glob patterns
  - OEmbedConsumer: resolves a URL against registered endpoints and
    fetches the oEmbed JSON response
  - OEmbedError / OEmbedNoEndpoint: exception hierarchy
"""

from __future__ import annotations

import fnmatch
import json
import logging
import re
import warnings
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mdx_oembed.version import __version__

__all__ = [
    "OEmbedEndpoint",
    "OEmbedConsumer",
    "OEmbedError",
    "OEmbedNoEndpoint",
    "REQUEST_TIMEOUT",
]

LOG = logging.getLogger(__name__)

# Default timeout (seconds) for outbound oEmbed HTTP requests.
REQUEST_TIMEOUT = 10

_USER_AGENT = f"python-markdown-oembed/{__version__}"

# Pre-compiled regex for the ``https?://`` scheme shorthand used in oEmbed
# URL patterns.  Kept at module level to avoid re-creation on every call.
_SCHEME_RE = re.compile(r"https\?://")
_SCHEME_PLACEHOLDER = "__SCHEME__"


# -- Exceptions -------------------------------------------------------------

class OEmbedError(Exception):
    """Base exception for oEmbed errors."""


class OEmbedNoEndpoint(OEmbedError):  # noqa: N818
    """Raised when no registered endpoint matches the requested URL."""


# -- Endpoint ---------------------------------------------------------------

class OEmbedEndpoint:
    """An oEmbed provider endpoint.

    Parameters
    ----------
    api_url:
        The provider's oEmbed API URL (e.g. ``https://www.youtube.com/oembed``).
    url_patterns:
        Shell-style glob patterns (with ``https?://`` shorthand) that describe
        which content URLs this endpoint handles.  The ``?`` in ``https?``
        is treated specially: it makes the preceding ``s`` optional so a single
        pattern can match both ``http`` and ``https``.
    """

    def __init__(self, api_url: str, url_patterns: list[str]) -> None:
        self.api_url = api_url
        self.url_patterns = url_patterns
        self._regexes: list[re.Pattern[str]] = [
            self._compile(p) for p in url_patterns
        ]

    def __repr__(self) -> str:
        return f"OEmbedEndpoint({self.api_url!r}, {self.url_patterns!r})"

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    def _compile(pattern: str) -> re.Pattern[str]:
        """Convert a URL-glob pattern to a compiled regex.

        Handles the ``https?://`` convention used by oEmbed providers:
        the ``s`` before ``?`` is made optional *before* the rest of the
        pattern is translated via `fnmatch`.
        """
        converted = _SCHEME_RE.sub(_SCHEME_PLACEHOLDER, pattern)
        # fnmatch.translate anchors with \\A … \\Z and handles */?/[] globs.
        regex = fnmatch.translate(converted)
        # Put the scheme alternation back.
        regex = regex.replace(_SCHEME_PLACEHOLDER, r"https?://")
        return re.compile(regex, re.IGNORECASE)

    def matches(self, url: str) -> bool:
        """Return True if *url* matches any of this endpoint's patterns."""
        return any(r.match(url) for r in self._regexes)


# -- Consumer ---------------------------------------------------------------

class OEmbedConsumer:
    """Registry of `OEmbedEndpoint` objects that can resolve arbitrary URLs.

    Parameters
    ----------
    timeout:
        HTTP request timeout in seconds.  Defaults to :data:`REQUEST_TIMEOUT`.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT) -> None:
        self._endpoints: list[OEmbedEndpoint] = []
        self.timeout = timeout

    def __repr__(self) -> str:
        names = [ep.api_url for ep in self._endpoints]
        return f"OEmbedConsumer(endpoints={names!r})"

    def add_endpoint(self, endpoint: OEmbedEndpoint) -> None:
        """Register an oEmbed endpoint."""
        self._endpoints.append(endpoint)

    def addEndpoint(self, endpoint: OEmbedEndpoint) -> None:  # noqa: N802
        """Deprecated alias for :meth:`add_endpoint`."""
        warnings.warn(
            "addEndpoint() is deprecated, use add_endpoint() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.add_endpoint(endpoint)

    def embed(self, url: str) -> dict[str, Any]:
        """Fetch the oEmbed response for *url*.

        Returns the parsed JSON as a ``dict``.

        Raises
        ------
        OEmbedNoEndpoint
            If none of the registered endpoints match *url*.
        OEmbedError
            On HTTP or JSON-parsing failures.
        """
        endpoint = self._find_endpoint(url)
        if endpoint is None:
            raise OEmbedNoEndpoint(f"No oEmbed endpoint registered for {url}")
        return self._fetch(endpoint, url)

    # -- internal helpers ----------------------------------------------------

    def _find_endpoint(self, url: str) -> OEmbedEndpoint | None:
        for ep in self._endpoints:
            if ep.matches(url):
                return ep
        return None

    def _fetch(self, endpoint: OEmbedEndpoint, content_url: str) -> dict[str, Any]:
        params = urlencode({"url": content_url, "format": "json"})
        api_url = f"{endpoint.api_url}?{params}"
        request = Request(api_url, headers={  # noqa: S310
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        })
        LOG.debug("Fetching oEmbed: %s", api_url)
        try:
            with urlopen(request, timeout=self.timeout) as resp:  # noqa: S310
                if resp.status is not None and not (200 <= resp.status < 300):
                    raise OEmbedError(
                        f"oEmbed request for {content_url} returned HTTP {resp.status}"
                    )
                charset = resp.headers.get_content_charset() or "utf-8"
                data: dict[str, Any] = json.loads(resp.read().decode(charset))
        except OEmbedError:
            raise
        except Exception as exc:
            raise OEmbedError(
                f"Failed to fetch oEmbed for {content_url}: {exc}"
            ) from exc
        return data
