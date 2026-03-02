import oembed

# URL patterns use python-oembed's glob-like syntax, not standard regex.

YOUTUBE = oembed.OEmbedEndpoint('https://www.youtube.com/oembed', [
    'https?://(*.)?youtube.com/*',
    'https?://youtu.be/*',
])

SLIDESHARE = oembed.OEmbedEndpoint('https://www.slideshare.net/api/oembed/2', [
    'https?://www.slideshare.net/*/*',
    'https?://fr.slideshare.net/*/*',
    'https?://de.slideshare.net/*/*',
    'https?://es.slideshare.net/*/*',
    'https?://pt.slideshare.net/*/*',
])

FLICKR = oembed.OEmbedEndpoint('https://www.flickr.com/services/oembed/', [
    'https?://*.flickr.com/*',
])

VIMEO = oembed.OEmbedEndpoint('https://vimeo.com/api/oembed.json', [
    'https?://vimeo.com/*',
])

DEFAULT_ENDPOINTS = [
    YOUTUBE,
    FLICKR,
    VIMEO,
    SLIDESHARE,
]
