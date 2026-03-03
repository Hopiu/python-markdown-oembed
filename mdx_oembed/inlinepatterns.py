from __future__ import annotations

import html as _html
import logging
from os.path import splitext
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

import markdown
import nh3
from markdown.inlinepatterns import InlineProcessor

from mdx_oembed.oembed import OEmbedConsumer, OEmbedNoEndpoint

LOG = logging.getLogger(__name__)

# Image extensions to exclude from oEmbed processing
_IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".avif", ".webp",
    ".svg", ".bmp", ".tiff", ".ico",
})

# Matches Markdown image syntax with an absolute URL: ![alt](https://...)
OEMBED_LINK_RE = r"!\[([^\]]*)\]\(((?:https?:)?//[^\)]+)\)"

# Allowed HTML tags and attributes for sanitizing oEmbed responses
_SANITIZE_TAGS = {
    "iframe", "video", "audio", "source", "img",
    "blockquote", "div", "p", "a", "span", "figure",
}
_SANITIZE_ATTRS = {
    "*": {"class", "style", "title"},
    "iframe": {
        "src", "width", "height", "frameborder",
        "allowfullscreen", "allow", "referrerpolicy", "sandbox",
    },
    "video": {
        "src", "width", "height", "controls",
        "autoplay", "loop", "muted", "poster", "preload",
    },
    "audio": {
        "src", "controls", "autoplay", "loop", "muted", "preload",
    },
    "source": {"src", "type"},
    "img": {"src", "alt", "width", "height", "loading"},
    "a": {"href", "target"},
}


def _is_image_url(url: str) -> bool:
    """Check if a URL points to an image based on its path extension."""
    try:
        path = urlparse(url).path
        _, ext = splitext(path)
        return ext.lower() in _IMAGE_EXTENSIONS
    except Exception:
        return False


def _sanitize_html(html: str) -> str:
    """Sanitize oEmbed HTML to prevent XSS."""
    return nh3.clean(html, tags=_SANITIZE_TAGS, attributes=_SANITIZE_ATTRS)


class OEmbedLinkPattern(InlineProcessor):
    """Inline processor that replaces Markdown image links with oEmbed content."""

    def __init__(
        self,
        pattern: str,
        md: markdown.Markdown | None = None,
        oembed_consumer: OEmbedConsumer | None = None,
        wrapper_class: str = "oembed",
    ) -> None:
        super().__init__(pattern, md)
        self.consumer = oembed_consumer
        self.wrapper_class = wrapper_class

    def handleMatch(self, m, data):  # noqa: N802
        url = m.group(2).strip()
        alt = m.group(1)

        # Skip image URLs — let Markdown's default image handler process them
        if _is_image_url(url):
            return None, None, None

        html = self._get_oembed_html(url, alt)
        if html is None:
            return None, None, None

        html = _sanitize_html(html)
        if self.wrapper_class:
            html = f'<figure class="{self.wrapper_class}">{html}</figure>'

        # Stash raw HTML so it survives Markdown's escaping; place the
        # placeholder inside an inline element that the tree-processor will
        # later replace with the real HTML.
        placeholder = self.md.htmlStash.store(html)
        el = Element("span")
        el.text = placeholder
        return el, m.start(0), m.end(0)

    def _get_oembed_html(self, url: str, alt: str = "") -> str | None:
        """Fetch oEmbed HTML for a URL, handling different response types."""
        if self.consumer is None:
            LOG.warning("No oEmbed consumer configured")
            return None
        try:
            response = self.consumer.embed(url)
        except OEmbedNoEndpoint:
            LOG.warning("No oEmbed endpoint for URL: %s", url)
            return None
        except Exception:
            LOG.exception("Error fetching oEmbed for URL: %s", url)
            return None

        # oEmbed 'video' and 'rich' types include an 'html' field
        html = response.get("html")
        if html:
            return html

        # oEmbed 'photo' type — construct an <img> tag
        photo_url = response.get("url")
        if photo_url:
            width = response.get("width", "")
            height = response.get("height", "")
            return (
                f'<img src="{_html.escape(str(photo_url), quote=True)}"'
                f' alt="{_html.escape(alt, quote=True)}"'
                f' width="{_html.escape(str(width), quote=True)}"'
                f' height="{_html.escape(str(height), quote=True)}" />'
            )

        LOG.warning("oEmbed response for %s has no 'html' or 'url' field", url)
        return None
