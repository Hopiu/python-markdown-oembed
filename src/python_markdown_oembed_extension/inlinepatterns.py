import logging
from markdown.inlinepatterns import Pattern
import oembed


LOG = logging.getLogger(__name__)


OEMBED_LINK_RE = r'\!\[([^\]]*)\]\(((?:https?:)?//[^\)]*)' \
                 r'(?<!png)(?<!jpg)(?<!jpeg)(?<!gif)(?<!avif)(?<!webp)\)'

class OEmbedLinkPattern(Pattern):

    def __init__(self, pattern, md=None, oembed_consumer=None):
        Pattern.__init__(self, pattern, md=md)
        self.consumer = oembed_consumer

    def handleMatch(self, match):
        html = self.get_oembed_html_for_match(match)
        if html is None:
            return None
        else:
            html = f'<figure class="oembed ratio ratio-16x9">{ html }</figure>'
            placeholder = self.md.htmlStash.store(html)
            return placeholder

    def get_oembed_html_for_match(self, match):
        url = match.group(3).strip()
        try:
            response = self.consumer.embed(url)
        except oembed.OEmbedNoEndpoint:
            LOG.error("No OEmbed Endpoint")
            return None
        except Exception as e:
            LOG.error(e)
            return None
        else:
            return response['html']
