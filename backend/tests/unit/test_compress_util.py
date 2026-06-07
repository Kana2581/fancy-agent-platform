import json

import pytest

from app.utils.compress_util import _extract_text


class TestExtractText:
    def test_plain_string(self):
        assert _extract_text("hello world") == "hello world"

    def test_json_content_list_with_text_blocks(self):
        content = json.dumps([
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
        ])
        assert _extract_text(content) == "hello world"

    def test_json_list_skips_non_text_blocks(self):
        content = json.dumps([
            {"type": "image_url", "url": "http://example.com/img.png"},
            {"type": "text", "text": "caption"},
        ])
        assert _extract_text(content) == "caption"

    def test_json_list_all_non_text_returns_empty(self):
        content = json.dumps([{"type": "image_url", "url": "http://x.com/a.png"}])
        assert _extract_text(content) == ""

    def test_invalid_json_returned_as_is(self):
        assert _extract_text("not { json") == "not { json"

    def test_json_object_not_list_returned_as_is(self):
        content = json.dumps({"key": "value"})
        assert _extract_text(content) == content

    def test_none_returns_empty_string(self):
        assert _extract_text(None) == ""

    def test_integer_converts_to_string(self):
        assert _extract_text(42) == "42"

    def test_empty_string(self):
        assert _extract_text("") == ""

    def test_empty_json_list(self):
        content = json.dumps([])
        assert _extract_text(content) == ""
