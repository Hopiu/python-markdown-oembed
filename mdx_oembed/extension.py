from __future__ import annotations

from markdown import Extension

from mdx_oembed.endpoints import DEFAULT_ENDPOINTS
from mdx_oembed.inlinepatterns import OEMBED_LINK_RE, OEmbedLinkPattern
from mdx_oembed.oembed import OEmbedConsumer


class OEmbedExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            'allowed_endpoints': [
                DEFAULT_ENDPOINTS,
                "A list of oEmbed endpoints to allow. "
                "Defaults to endpoints.DEFAULT_ENDPOINTS",
            ],
            'wrapper_class': [
                'oembed',
                "CSS class(es) for the <figure> wrapper element. "
                "Set to empty string to disable wrapping.",
            ],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):  # noqa: N802
        consumer = self._prepare_oembed_consumer()
        wrapper_class = self.getConfig('wrapper_class', 'oembed')
        link_pattern = OEmbedLinkPattern(
            OEMBED_LINK_RE, md, consumer, wrapper_class=wrapper_class,
        )
        # Priority 175 — run before the default image pattern (priority 150)
        md.inlinePatterns.register(link_pattern, 'oembed_link', 175)

    def _prepare_oembed_consumer(self):
        allowed_endpoints = self.getConfig('allowed_endpoints', DEFAULT_ENDPOINTS)
        consumer = OEmbedConsumer()
        for endpoint in (allowed_endpoints or []):
            consumer.add_endpoint(endpoint)
        return consumer
