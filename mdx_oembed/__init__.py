from mdx_oembed.extension import OEmbedExtension
from mdx_oembed.version import __version__

VERSION = __version__


def makeExtension(**kwargs):
    return OEmbedExtension(**kwargs)
