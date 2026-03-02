import re
import unittest
from unittest.mock import MagicMock, patch

import markdown
from mdx_oembed import endpoints
from mdx_oembed.inlinepatterns import OEMBED_LINK_RE, _is_image_url, _sanitize_html

# ---------------------------------------------------------------------------
# Regex tests
# ---------------------------------------------------------------------------

class TestOEmbedRegex(unittest.TestCase):
    """Tests for the raw OEMBED_LINK_RE pattern."""

    def setUp(self):
        self.re = re.compile(OEMBED_LINK_RE)

    # --- should NOT match (relative URLs) ---

    def test_ignore_relative_image_link(self):
        assert self.re.search("![image](/image.png)") is None

    # --- should match (absolute URLs — image filtering is in Python now) ---

    def test_match_absolute_url(self):
        m = self.re.search("![img](http://example.com/photo.png)")
        assert m is not None

    def test_match_youtube_link(self):
        m = self.re.search("![video](http://www.youtube.com/watch?v=ABC)")
        assert m is not None
        assert m.group(2) == "http://www.youtube.com/watch?v=ABC"

    def test_match_youtube_short_link(self):
        m = self.re.search("![video](http://youtu.be/ABC)")
        assert m is not None

    def test_match_https(self):
        m = self.re.search("![video](https://youtu.be/ABC)")
        assert m is not None

    def test_match_protocol_relative(self):
        m = self.re.search("![video](//youtu.be/ABC)")
        assert m is not None

    def test_alt_text_captured(self):
        m = self.re.search("![my alt text](https://example.com/embed)")
        assert m is not None
        assert m.group(1) == "my alt text"


# ---------------------------------------------------------------------------
# Image URL detection
# ---------------------------------------------------------------------------

class TestIsImageUrl(unittest.TestCase):

    def test_common_extensions(self):
        for ext in ("png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "bmp", "tiff", "ico"):
            assert _is_image_url(f"http://example.com/photo.{ext}") is True, ext

    def test_case_insensitive(self):
        assert _is_image_url("http://example.com/Photo.PNG") is True
        assert _is_image_url("http://example.com/photo.JpEg") is True

    def test_query_string_ignored(self):
        assert _is_image_url("http://example.com/photo.jpg?size=large") is True

    def test_non_image(self):
        assert _is_image_url("http://www.youtube.com/watch?v=ABC") is False

    def test_no_extension(self):
        assert _is_image_url("http://example.com/embed") is False


# ---------------------------------------------------------------------------
# HTML sanitization
# ---------------------------------------------------------------------------

class TestSanitizeHtml(unittest.TestCase):

    def test_allows_iframe(self):
        html = '<iframe src="https://youtube.com/embed/x" width="560" height="315" allowfullscreen></iframe>'
        result = _sanitize_html(html)
        assert "<iframe" in result
        assert 'src="https://youtube.com/embed/x"' in result

    def test_strips_script(self):
        html = '<script>alert("xss")</script><iframe src="https://safe.com"></iframe>'
        result = _sanitize_html(html)
        assert "<script" not in result
        assert "<iframe" in result

    def test_strips_onerror(self):
        html = '<img src="x" onerror="alert(1)" />'
        result = _sanitize_html(html)
        assert "onerror" not in result


# ---------------------------------------------------------------------------
# Extension integration tests (mocked HTTP)
# ---------------------------------------------------------------------------

def _make_mock_consumer(html_response="<iframe src='https://embed.example.com'></iframe>"):
    """Create a mock OEmbedConsumer that returns the given HTML."""
    consumer = MagicMock()
    response = MagicMock()
    response.get = lambda key, default=None: {"html": html_response, "type": "video"}.get(key, default)
    response.__getitem__ = lambda self_inner, key: {"html": html_response, "type": "video"}[key]
    consumer.embed.return_value = response
    return consumer


def _make_photo_consumer(photo_url="https://example.com/photo.jpg", width=640, height=480):
    consumer = MagicMock()
    data = {"type": "photo", "url": photo_url, "width": width, "height": height}
    response = MagicMock()
    response.get = lambda key, default=None: data.get(key, default)
    response.__getitem__ = lambda self_inner, key: data[key]
    consumer.embed.return_value = response
    return consumer


def _make_failing_consumer(exc_class=Exception, msg="fail"):
    consumer = MagicMock()
    consumer.embed.side_effect = exc_class(msg)
    return consumer


class TestOEmbedExtension(unittest.TestCase):
    """Integration tests with mocked oEmbed consumer."""

    def _convert(self, text, consumer=None, **ext_config):
        """Helper: convert markdown with a mocked consumer."""
        if consumer is None:
            consumer = _make_mock_consumer()

        with patch("mdx_oembed.extension.oembed.OEmbedConsumer", return_value=consumer):
            md = markdown.Markdown(
                extensions=["oembed"],
                extension_configs={"oembed": ext_config} if ext_config else {},
            )
            return md.convert(text)

    # --- basic embedding ---

    def test_youtube_embed(self):
        output = self._convert("![video](http://www.youtube.com/watch?v=ABC)")
        assert "<iframe" in output
        assert "oembed" in output  # wrapper class

    def test_vimeo_embed(self):
        output = self._convert("![vid](https://vimeo.com/12345)")
        assert "<iframe" in output

    # --- images pass through ---

    def test_image_png_passthrough(self):
        output = self._convert("![alt](http://example.com/img.png)")
        assert "<img" in output

    def test_image_jpg_passthrough(self):
        output = self._convert("![alt](http://example.com/img.jpg)")
        assert "<img" in output

    def test_image_with_query_passthrough(self):
        output = self._convert("![alt](http://example.com/img.jpg?v=1)")
        assert "<img" in output

    def test_image_uppercase_passthrough(self):
        output = self._convert("![alt](http://example.com/img.PNG)")
        assert "<img" in output

    # --- relative images are unaffected ---

    def test_relative_image(self):
        output = self._convert("![alt](image.png)")
        assert '<img alt="alt" src="image.png"' in output

    def test_slash_relative_image(self):
        output = self._convert("![alt](/image.png)")
        assert '<img alt="alt" src="/image.png"' in output

    # --- photo type response ---

    def test_photo_type_response(self):
        consumer = _make_photo_consumer()
        output = self._convert("![photo](https://flickr.com/photos/1234)", consumer)
        assert "<img" in output
        assert "https://example.com/photo.jpg" in output

    # --- error handling ---

    def test_no_endpoint_falls_through(self):
        import oembed as _oembed
        consumer = _make_failing_consumer(_oembed.OEmbedNoEndpoint)
        output = self._convert("![video](http://unknown.example.com/abc)", consumer)
        assert "<iframe" not in output

    def test_network_error_falls_through(self):
        consumer = _make_failing_consumer(Exception, "timeout")
        output = self._convert("![video](http://www.youtube.com/watch?v=ABC)", consumer)
        assert "<iframe" not in output

    # --- configuration ---

    def test_custom_wrapper_class(self):
        output = self._convert(
            "![v](http://www.youtube.com/watch?v=ABC)",
            wrapper_class="embed-responsive",
        )
        assert "embed-responsive" in output

    def test_empty_wrapper_class(self):
        output = self._convert(
            "![v](http://www.youtube.com/watch?v=ABC)",
            wrapper_class="",
        )
        assert "<figure" not in output
        assert "<iframe" in output

    # --- XSS protection ---

    def test_script_stripped_from_response(self):
        evil_consumer = _make_mock_consumer(
            '<script>alert("xss")</script><iframe src="https://ok.com"></iframe>'
        )
        output = self._convert("![v](http://www.youtube.com/watch?v=ABC)", evil_consumer)
        assert "<script" not in output
        assert "<iframe" in output

    # --- multiple links ---

    def test_multiple_embeds(self):
        text = (
            "![a](http://www.youtube.com/watch?v=A)\n\n"
            "![b](http://www.youtube.com/watch?v=B)"
        )
        output = self._convert(text)
        assert output.count("<iframe") == 2


class TestLimitedEndpoints(unittest.TestCase):
    """Test allowed_endpoints configuration."""

    def test_youtube_only(self):
        import oembed as _oembed

        def side_effect(url):
            if "youtube" in url:
                resp = MagicMock()
                data = {"html": "<iframe src='yt'></iframe>", "type": "video"}
                resp.get = lambda key, default=None: data.get(key, default)
                resp.__getitem__ = lambda self_inner, key: data[key]
                return resp
            raise _oembed.OEmbedNoEndpoint("nope")

        consumer = MagicMock()
        consumer.embed.side_effect = side_effect

        with patch("mdx_oembed.extension.oembed.OEmbedConsumer", return_value=consumer):
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


if __name__ == "__main__":
    unittest.main()
