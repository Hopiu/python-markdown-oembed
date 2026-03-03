from __future__ import annotations

from mdx_oembed.oembed import OEmbedEndpoint

# URL patterns use shell-style globs with an "https?://" shorthand
# that matches both http and https schemes.

YOUTUBE = OEmbedEndpoint('https://www.youtube.com/oembed', [
    'https?://*.youtube.com/*',
    'https?://youtu.be/*',
])

SLIDESHARE = OEmbedEndpoint('https://www.slideshare.net/api/oembed/2', [
    'https?://www.slideshare.net/*/*',
    'https?://fr.slideshare.net/*/*',
    'https?://de.slideshare.net/*/*',
    'https?://es.slideshare.net/*/*',
    'https?://pt.slideshare.net/*/*',
])

FLICKR = OEmbedEndpoint('https://www.flickr.com/services/oembed/', [
    'https?://*.flickr.com/*',
])

VIMEO = OEmbedEndpoint('https://vimeo.com/api/oembed.json', [
    'https?://vimeo.com/*',
])

DEFAULT_ENDPOINTS = [
    YOUTUBE,
    FLICKR,
    VIMEO,
    SLIDESHARE,
]
