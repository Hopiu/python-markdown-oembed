# -*- coding: utf-8 -*-
from python_markdown_oembed_extension.extension import OEmbedExtension


VERSION = '0.2.2'


def makeExtension(**kwargs):
    return OEmbedExtension(**kwargs)
