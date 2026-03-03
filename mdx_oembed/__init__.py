from __future__ import annotations

from mdx_oembed.extension import OEmbedExtension
from mdx_oembed.version import __version__

VERSION = __version__

__all__ = ["OEmbedExtension", "VERSION", "__version__", "makeExtension"]


def makeExtension(**kwargs: object) -> OEmbedExtension:  # noqa: N802
    return OEmbedExtension(**kwargs)
