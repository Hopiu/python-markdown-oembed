from markdown import Extension
import oembed
from python_markdown_oembed_extension.endpoints import DEFAULT_ENDPOINTS
from python_markdown_oembed_extension.inlinepatterns import OEmbedLinkPattern, OEMBED_LINK_RE


class OEmbedExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            'allowed_endpoints': [
                DEFAULT_ENDPOINTS,
                "A list of oEmbed endpoints to allow. Defaults to "
                "endpoints.DEFAULT_ENDPOINTS"
            ],
        }
        super(OEmbedExtension, self).__init__(**kwargs)

    def extendMarkdown(self, md):
        self.oembed_consumer = self.prepare_oembed_consumer()
        link_pattern = OEmbedLinkPattern(OEMBED_LINK_RE, md,
                                         self.oembed_consumer)
        md.inlinePatterns.register(link_pattern, 'oembed_link', 175)

    def prepare_oembed_consumer(self):
        allowed_endpoints = self.getConfig('allowed_endpoints', DEFAULT_ENDPOINTS)
        consumer = oembed.OEmbedConsumer()

        if allowed_endpoints:
           for endpoint in allowed_endpoints:
                consumer.addEndpoint(endpoint)

        return consumer

