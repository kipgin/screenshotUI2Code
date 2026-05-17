"""Tests for the utils module: code parsing, text utilities, response fixer, image utils."""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.code_parser import extract_code_blocks, reconstruct_html, extract_first_block, extract_json_block
from utils.text_utils import estimate_tokens, truncate_to_token_limit, clean_llm_response, messages_to_text
from utils.response_fixer import ResponseFixer, requires_code_block, requires_json_block, requires_non_empty
from utils.image_utils import encode_image_base64, get_image_media_type, build_data_uri


# ── Code parser ───────────────────────────────────────────────────────────────

def test_extract_html_block():
    text = "Here is the code:\n```html\n<div>Hello</div>\n```\n"
    blocks = extract_code_blocks(text)
    assert "html" in blocks
    assert "<div>Hello</div>" in blocks["html"][0]


def test_extract_multiple_langs():
    text = "```css\nbody{}\n```\n```javascript\nconsole.log(1)\n```"
    blocks = extract_code_blocks(text)
    assert "css" in blocks
    assert "javascript" in blocks


def test_extract_js_alias():
    text = "```js\nconst x = 1;\n```"
    blocks = extract_code_blocks(text)
    assert "javascript" in blocks


def test_extract_no_blocks():
    assert extract_code_blocks("no code here") == {}


def test_reconstruct_html():
    result = reconstruct_html("<p>Hello</p>", "p{color:red}", "alert(1)")
    assert "<!DOCTYPE html>" in result
    assert "<p>Hello</p>" in result
    assert "p{color:red}" in result
    assert "alert(1)" in result


def test_reconstruct_html_empty_returns_none():
    assert reconstruct_html() is None


def test_extract_first_block_by_lang():
    text = "```jsx\nfunction App(){}\n```"
    result = extract_first_block(text, "jsx")
    assert "function App" in result


def test_extract_json_block():
    text = 'Some text\n```json\n{"key": "value"}\n```'
    result = extract_json_block(text)
    assert '"key": "value"' in result


def test_extract_json_bare():
    text = 'Here: [{"id": 1}]'
    result = extract_json_block(text)
    assert result is not None


# ── Text utils ────────────────────────────────────────────────────────────────

def test_estimate_tokens():
    # "hello world" = 11 chars → 2 tokens by heuristic
    assert estimate_tokens("hello world") == 2


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_truncate_to_token_limit():
    long_text = "word " * 2000  # 10000 chars = 2500 tokens
    truncated = truncate_to_token_limit(long_text, 100)
    assert estimate_tokens(truncated) <= 110  # small tolerance


def test_clean_llm_response_strips():
    assert clean_llm_response("  hello  ") == "hello"


def test_messages_to_text():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    text = messages_to_text(messages)
    assert "user: Hello" in text
    assert "assistant: Hi" in text


# ── Response fixer ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fixer_passes_on_valid():
    fixer = ResponseFixer(max_retries=2)
    result = await fixer.fix(
        response="```html\n<div></div>\n```",
        check_fn=requires_code_block("html"),
        correction_prompt="Add an HTML block.",
        llm_client=AsyncMock(),
        messages=[],
    )
    assert "```html" in result


@pytest.mark.asyncio
async def test_fixer_retries_and_corrects():
    fixer = ResponseFixer(max_retries=1)
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value="```html\n<div>fixed</div>\n```")

    result = await fixer.fix(
        response="no code block here",
        check_fn=requires_code_block("html"),
        correction_prompt="Please wrap in ```html.",
        llm_client=mock_client,
        messages=[],
    )
    assert "```html" in result


def test_requires_json_block_valid():
    assert requires_json_block('```json\n{"a": 1}\n```')


def test_requires_json_block_invalid():
    assert not requires_json_block("no JSON here at all")


def test_requires_non_empty():
    assert requires_non_empty("hello")
    assert not requires_non_empty("   ")


# ── Image utils ───────────────────────────────────────────────────────────────

def test_encode_image_base64(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    b64 = encode_image_base64(img)
    assert isinstance(b64, str)
    # Should be valid base64
    base64.b64decode(b64)


def test_get_image_media_type_png(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"")
    assert get_image_media_type(f) == "image/png"


def test_get_image_media_type_jpeg(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_bytes(b"")
    assert get_image_media_type(f) == "image/jpeg"


def test_build_data_uri(tmp_path):
    img = tmp_path / "icon.png"
    img.write_bytes(b"\x89PNG" + b"\x00" * 20)
    uri = build_data_uri(img)
    assert uri.startswith("data:image/png;base64,")
