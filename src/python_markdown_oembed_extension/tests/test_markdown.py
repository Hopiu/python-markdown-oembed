import markdown, yaml, requests_mock
from python_markdown_oembed_extension.oembedextension import OEmbedExtension
from python_markdown_oembed_extension.endpoints import VIMEO


def test_full():
    with ( requests_mock.Mocker() as m
         , open('./src/python_markdown_oembed_extension/tests/vimeoMock.yaml', 'r') as vm
         , open('./src/python_markdown_oembed_extension/tests/test_markdown.md', 'r') as md
         , open('./src/python_markdown_oembed_extension/tests/test_expectedHtml.html', 'r') as expectedHtml
         ):

        yml = yaml.safe_load(vm)
        m.get(yml['request'], json=yml['response'])

        mdString = md.read()
        htmlString = markdown.markdown(mdString, extensions=[OEmbedExtension()])
        print(htmlString)

        assert htmlString == expectedHtml.read().rstrip()

