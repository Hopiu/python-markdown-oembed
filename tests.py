"""Tests for python-markdown-oembed extension."""

from __future__ import annotations

import json
import re
import warnings
from unittest.mock import MagicMock, patch

import markdown
import pytest

from mdx_oembed import endpoints
from mdx_oembed.inlinepatterns import OEMBED_LINK_RE, _is_image_url, _sanitize_html
from mdx_oembed.oembed import (
    OEmbedConsumer,
    OEmbedEndpoint,
    OEmbedError,
    OEmbedNoEndpoint,
)

# ---------------------------------------------------------------------------
# Regex tests
# ---------------------------------------------------------------------------

_OEMBED_RE = re.compile(OEMBED_LINK_RE)


def test_ignore_relative_image_link():
    assert _OEMBED_RE.search("![image](/image.png)") is None


def test_match_absolute_url():
    m = _OEMBED_RE.search("![img](http://example.com/photo.png)")
    assert m is not None


def test_match_youtube_link():
    m = _OEMBED_RE.search("![video](http://www.youtube.com/watch?v=ABC)")
    assert m is not None
    assert m.group(2) == "http://www.youtube.com/watch?v=ABC"


def test_match_youtube_short_link():
    m = _OEMBED_RE.search("![video](http://youtu.be/ABC)")
    assert m is not None


def test_match_https():
    m = _OEMBED_RE.search("![video](https://youtu.be/ABC)")
    assert m is not None


def test_match_protocol_relative():
    m = _OEMBED_RE.search("![video](//youtu.be/ABC)")
    assert m is not None


def test_alt_text_captured():
    m = _OEMBED_RE.search("![my alt text](https://example.com/embed)")
    assert m is not None
    assert m.group(1) == "my alt text"


# ---------------------------------------------------------------------------
# Image URL detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ext",
    ["png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "bmp", "tiff", "ico"],
)
def test_common_image_extensions(ext: str):
    assert _is_image_url(f"http://example.com/photo.{ext}") is True


def test_image_url_case_insensitive():
    assert _is_image_url("http://example.com/Photo.PNG") is True
    assert _is_image_url("http://example.com/photo.JpEg") is True


def test_image_url_query_string_ignored():
    assert _is_image_url("http://example.com/photo.jpg?size=large") is True


def test_non_image_url():
    assert _is_image_url("http://www.youtube.com/watch?v=ABC") is False


def test_no_extension_url():
    assert _is_image_url("http://example.com/embed") is False


# ---------------------------------------------------------------------------
# HTML sanitization
# ---------------------------------------------------------------------------


def test_sanitize_allows_iframe():
    html = (
        '<iframe src="https://youtube.com/embed/x"'
        ' width="560" height="315" allowfullscreen></iframe>'
    )
    result = _sanitize_html(html)
    assert "<iframe" in result
    assert 'src="https://youtube.com/embed/x"' in result


def test_sanitize_strips_script():
    html = '<script>alert("xss")</script><iframe src="https://safe.com"></iframe>'
    result = _sanitize_html(html)
    assert "<script" not in result
    assert "<iframe" in result


def test_sanitize_strips_onerror():
    html = '<img src="x" onerror="alert(1)" />'
    result = _sanitize_html(html)
    assert "onerror" not in result


# ---------------------------------------------------------------------------
# OEmbedConsumer / OEmbedEndpoint unit tests
# ---------------------------------------------------------------------------


def test_endpoint_matches_http_and_https():
    ep = OEmbedEndpoint("https://example.com/oembed", ["https?://example.com/*"])
    assert ep.matches("http://example.com/video/1")
    assert ep.matches("https://example.com/video/1")
    assert not ep.matches("http://other.com/video/1")


def test_consumer_add_endpoint():
    consumer = OEmbedConsumer()
    ep = OEmbedEndpoint("https://example.com/oembed", ["https?://example.com/*"])
    consumer.add_endpoint(ep)
    assert ep in consumer._endpoints  # noqa: SLF001


def test_consumer_add_endpoint_deprecated_alias():
    consumer = OEmbedConsumer()
    ep = OEmbedEndpoint("https://example.com/oembed", ["https?://example.com/*"])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        consumer.addEndpoint(ep)
    assert len(w) == 1
    assert issubclass(w[0].category, DeprecationWarning)
    assert "addEndpoint" in str(w[0].message)
    assert ep in consumer._endpoints  # noqa: SLF001


def test_consumer_embed_no_endpoint():
    consumer = OEmbedConsumer()
    with pytest.raises(OEmbedNoEndpoint):
        consumer.embed("http://unknown.example.com/video")


def test_consumer_http_status_error():
    """Non-2xx HTTP responses should raise OEmbedError."""
    ep = OEmbedEndpoint("https://example.com/oembed", ["https?://example.com/*"])
    consumer = OEmbedConsumer()
    consumer.add_endpoint(ep)

    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("mdx_oembed.oembed.urlopen", return_value=mock_resp):
        with pytest.raises(OEmbedError, match="HTTP 404"):
            consumer.embed("http://example.com/video/1")


def test_consumer_successful_fetch():
    """Successful 200 response should return parsed JSON."""
    ep = OEmbedEndpoint("https://example.com/oembed", ["https?://example.com/*"])
    consumer = OEmbedConsumer()
    consumer.add_endpoint(ep)

    body = json.dumps({"html": "<iframe></iframe>", "type": "video"}).encode()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = body
    mock_resp.headers.get_content_charset.return_value = "utf-8"
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("mdx_oembed.oembed.urlopen", return_value=mock_resp):
        data = consumer.embed("http://example.com/video/1")
    assert data["html"] == "<iframe></iframe>"


# ---------------------------------------------------------------------------
# Extension integration tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _make_mock_consumer(
    html_response: str = "<iframe src='https://embed.example.com'></iframe>",
) -> MagicMock:
    """Create a mock OEmbedConsumer that returns the given HTML."""
    consumer = MagicMock()
    data = {"html": html_response, "type": "video"}
    response = MagicMock()
    response.get = lambda key, default=None: data.get(key, default)
    response.__getitem__ = lambda self_inner, key: data[key]
    consumer.embed.return_value = response
    return consumer


def _make_photo_consumer(
    photo_url: str = "https://example.com/photo.jpg",
    width: int = 640,
    height: int = 480,
) -> MagicMock:
    consumer = MagicMock()
    data = {"type": "photo", "url": photo_url, "width": width, "height": height}
    response = MagicMock()
    response.get = lambda key, default=None: data.get(key, default)
    response.__getitem__ = lambda self_inner, key: data[key]
    consumer.embed.return_value = response
    return consumer


def _make_failing_consumer(
    exc_class: type[Exception] = Exception, msg: str = "fail"
) -> MagicMock:
    consumer = MagicMock()
    consumer.embed.side_effect = exc_class(msg)
    return consumer


def _convert(
    text: str,
    consumer: MagicMock | None = None,
    **ext_config: object,
) -> str:
    """Helper: convert markdown with a mocked consumer."""
    if consumer is None:
        consumer = _make_mock_consumer()

    with patch("mdx_oembed.extension.OEmbedConsumer", return_value=consumer):
        md = markdown.Markdown(
            extensions=["oembed"],
            extension_configs={"oembed": ext_config} if ext_config else {},
        )
        return md.convert(text)


# --- basic embedding ---


def test_youtube_embed():
    output = _convert("![video](http://www.youtube.com/watch?v=ABC)")
    assert "<iframe" in output
    assert "oembed" in output  # wrapper class


def test_vimeo_embed():
    output = _convert("![vid](https://vimeo.com/12345)")
    assert "<iframe" in output


# --- images pass through ---


def test_image_png_passthrough():
    output = _convert("![alt](http://example.com/img.png)")
    assert "<img" in output


def test_image_jpg_passthrough():
    output = _convert("![alt](http://example.com/img.jpg)")
    assert "<img" in output


def test_image_with_query_passthrough():
    output = _convert("![alt](http://example.com/img.jpg?v=1)")
    assert "<img" in output


def test_image_uppercase_passthrough():
    output = _convert("![alt](http://example.com/img.PNG)")
    assert "<img" in output


# --- relative images are unaffected ---


def test_relative_image():
    output = _convert("![alt](image.png)")
    assert '<img alt="alt" src="image.png"' in output


def test_slash_relative_image():
    output = _convert("![alt](/image.png)")
    assert '<img alt="alt" src="/image.png"' in output


# --- photo type response ---


def test_photo_type_response():
    consumer = _make_photo_consumer()
    output = _convert("![photo](https://flickr.com/photos/1234)", consumer)
    assert "<img" in output
    assert "https://example.com/photo.jpg" in output


def test_photo_type_escapes_html():
    """Photo URLs with special chars are properly escaped."""
    consumer = _make_photo_consumer(
        photo_url='https://example.com/photo.jpg?a=1&b=2"'
    )
    output = _convert(
        "![alt text](https://flickr.com/photos/1234)", consumer
    )
    # The & in the photo URL must be escaped as &amp; in the src attribute
    assert "&amp;" in output
    # The " in the photo URL must be escaped (nh3 may use &quot; or &#34;)
    assert 'b=2"' not in output


# --- error handling ---


def test_no_endpoint_falls_through():
    consumer = _make_failing_consumer(OEmbedNoEndpoint)
    output = _convert("![video](http://unknown.example.com/abc)", consumer)
    assert "<iframe" not in output


def test_network_error_falls_through():
    consumer = _make_failing_consumer(Exception, "timeout")
    output = _convert("![video](http://www.youtube.com/watch?v=ABC)", consumer)
    assert "<iframe" not in output


# --- configuration ---


def test_custom_wrapper_class():
    output = _convert(
        "![v](http://www.youtube.com/watch?v=ABC)",
        wrapper_class="embed-responsive",
    )
    assert "embed-responsive" in output


def test_empty_wrapper_class():
    output = _convert(
        "![v](http://www.youtube.com/watch?v=ABC)",
        wrapper_class="",
    )
    assert "<figure" not in output
    assert "<iframe" in output


# --- XSS protection ---


def test_script_stripped_from_response():
    evil_consumer = _make_mock_consumer(
        '<script>alert("xss")</script><iframe src="https://ok.com"></iframe>'
    )
    output = _convert("![v](http://www.youtube.com/watch?v=ABC)", evil_consumer)
    assert "<script" not in output
    assert "<iframe" in output


# --- multiple links ---


def test_multiple_embeds():
    text = (
        "![a](http://www.youtube.com/watch?v=A)\n\n"
        "![b](http://www.youtube.com/watch?v=B)"
    )
    output = _convert(text)
    assert output.count("<iframe") == 2


# ---------------------------------------------------------------------------
# Limited endpoints configuration
# ---------------------------------------------------------------------------


def test_youtube_only_endpoint():
    def side_effect(url: str) -> MagicMock:
        if "youtube" in url:
            resp = MagicMock()
            data = {"html": "<iframe src='yt'></iframe>", "type": "video"}
            resp.get = lambda key, default=None: data.get(key, default)
            resp.__getitem__ = lambda self_inner, key: data[key]
            return resp
        raise OEmbedNoEndpoint("nope")

    consumer = MagicMock()
    consumer.embed.side_effect = side_effect

    with patch("mdx_oembed.extension.OEmbedConsumer", return_value=consumer):
        md = markdown.Markdown(
            extensions=["oembed"],
            extension_configs={
                "oembed": {"allowed_endpoints": [endpoints.YOUTUBE]},
            },
        )
        yt_output = md.convert("![v](http://www.youtube.com/watch?v=A)")
        assert "<iframe" in yt_output

        md.reset()
        vim_output = md.convert("![v](http://vimeo.com/12345)")
        assert "<iframe" not in vim_output
