# Python Markdown oEmbed

Markdown extension to allow media embedding using the oEmbed standard.

## Requirements

- Python >= 3.9
- Markdown >= 3.2

## Installation

    pip install python-markdown-oembed

Or with [uv](https://docs.astral.sh/uv/):

    uv add python-markdown-oembed

## Usage

```python
import markdown
md = markdown.Markdown(extensions=['oembed'])
md.convert('![video](http://www.youtube.com/watch?v=zqnh_YJBvOI)')
```

Output is wrapped in a `<figure class="oembed">` element by default:

```html
<figure class="oembed"><iframe width="459" height="344" ...></iframe></figure>
```

### Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `allowed_endpoints` | YouTube, Flickr, Vimeo, Slideshare | List of `oembed.OEmbedEndpoint` objects |
| `wrapper_class` | `"oembed"` | CSS class(es) for the `<figure>` wrapper. Set to `""` to disable wrapping |

Example with custom configuration:

```python
from mdx_oembed.endpoints import YOUTUBE, VIMEO

md = markdown.Markdown(
    extensions=['oembed'],
    extension_configs={
        'oembed': {
            'allowed_endpoints': [YOUTUBE, VIMEO],
            'wrapper_class': 'embed-responsive',
        }
    }
)
```

## Security

oEmbed HTML responses are sanitized using [nh3](https://github.com/messense/nh3)
to prevent XSS from compromised oEmbed providers. Only safe tags (`iframe`,
`video`, `audio`, `img`, etc.) and attributes are allowed.

## Links

- [python-markdown-oembed](https://github.com/rennat/python-markdown-oembed)
- [Markdown](http://daringfireball.net/projects/markdown/)
- [oEmbed](http://www.oembed.com/)
- [python-oembed](https://github.com/abarmat/python-oembed)

## License

A Public Domain work. Do as you wish.

## Changelog

### 0.3.0

- **Breaking:** requires Python >= 3.9 and Markdown >= 3.2
- Migrated from deprecated `Pattern` to `InlineProcessor` (Markdown 3.2+ compatible)
- Added HTML sanitization of oEmbed responses (XSS protection via nh3)
- Added support for oEmbed `photo` type responses
- Improved image URL detection (case-insensitive, handles query strings)
- All oEmbed API endpoints now use HTTPS
- Slideshare URL patterns now accept both HTTP and HTTPS
- Configurable `<figure>` wrapper class (previously hardcoded Bootstrap classes)
- Migrated to `pyproject.toml` with hatchling build backend
- Tests modernized: uses pytest + unittest.mock, all HTTP calls mocked
- Centralized version management in `mdx_oembed/version.py`

### 0.2.1

- add Slideshare endpoint (thanks to [anantshri](https://github.com/anantshri))

### 0.2.0

- backwards incompatible changes
    - allows arbitrary endpoints ([commit](https://github.com/Wenzil/python-markdown-oembed/commit/1e89de9db5e63677e071c36503e2499bbe0792da))
    - works with modern Markdown (>=2.6)
    - dropped support for python 2.6
- added support python 3.x
