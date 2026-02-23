"""Tests for InteractiveHTMLAgent — TDD Red phase."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.agents.interactive_html import InteractiveHTMLAgent


# ---------------------------------------------------------------------------
# FakeLLM helpers
# ---------------------------------------------------------------------------

class FakeLLM:
    """Fake LLM client that returns a preset response."""

    def __init__(self, response=""):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append({"system": system_prompt, "user": user_prompt})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


# ---------------------------------------------------------------------------
# Valid HTML fixture
# ---------------------------------------------------------------------------

VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""

VALID_HTML_BLOCK = f"```html\n{VALID_HTML}\n```"


# ---------------------------------------------------------------------------
# 1. test_generate_success
# ---------------------------------------------------------------------------

def test_generate_success():
    """LLM returns valid HTML block, extracted correctly."""
    llm = FakeLLM(response=VALID_HTML_BLOCK)
    agent = InteractiveHTMLAgent(llm)
    result = agent.generate("Some content", topic="Test Topic")

    assert result["success"] is True
    assert result["fallback"] is False
    assert "<html" in result["html"].lower()
    assert "<body>" in result["html"].lower()
    assert len(llm.calls) == 1
    assert "Test Topic" in llm.calls[0]["user"]


# ---------------------------------------------------------------------------
# 2. test_generate_fallback_on_invalid
# ---------------------------------------------------------------------------

def test_generate_fallback_on_invalid():
    """LLM returns invalid HTML (missing tags), falls back."""
    llm = FakeLLM(response="```html\n<div>not valid html</div>\n```")
    agent = InteractiveHTMLAgent(llm)
    result = agent.generate("Some content", topic="Fallback Test")

    assert result["success"] is True
    assert result["fallback"] is True
    assert "<html" in result["html"].lower()


# ---------------------------------------------------------------------------
# 3. test_generate_fallback_on_exception
# ---------------------------------------------------------------------------

def test_generate_fallback_on_exception():
    """LLM raises exception, falls back gracefully."""
    llm = FakeLLM(response=RuntimeError("LLM down"))
    agent = InteractiveHTMLAgent(llm)
    result = agent.generate("Some content", topic="Error Test")

    assert result["success"] is True
    assert result["fallback"] is True
    assert "<html" in result["html"].lower()


# ---------------------------------------------------------------------------
# 4. test_extract_html_code_block
# ---------------------------------------------------------------------------

def test_extract_html_code_block():
    """Extract HTML from ```html``` markers."""
    raw = '```html\n<html><head></head><body>Hi</body></html>\n```'
    result = InteractiveHTMLAgent._extract_html(raw)
    assert result.startswith("<html>")
    assert result.endswith("</html>")


# ---------------------------------------------------------------------------
# 5. test_extract_html_raw
# ---------------------------------------------------------------------------

def test_extract_html_raw():
    """Extract from raw <html>...</html> without code block markers."""
    raw = 'Here is the page:\n<html lang="en"><head></head><body>Hi</body></html>\nDone.'
    result = InteractiveHTMLAgent._extract_html(raw)
    assert result.startswith('<html')
    assert result.endswith('</html>')


# ---------------------------------------------------------------------------
# 6. test_extract_html_empty
# ---------------------------------------------------------------------------

def test_extract_html_empty():
    """No HTML found returns empty string."""
    result = InteractiveHTMLAgent._extract_html("Just some random text.")
    assert result == ""


# ---------------------------------------------------------------------------
# 7. test_validate_html_valid
# ---------------------------------------------------------------------------

def test_validate_html_valid():
    """Valid HTML passes validation."""
    assert InteractiveHTMLAgent._validate_html(VALID_HTML) is True


# ---------------------------------------------------------------------------
# 8. test_validate_html_invalid
# ---------------------------------------------------------------------------

def test_validate_html_invalid():
    """Missing required tags fails validation."""
    assert InteractiveHTMLAgent._validate_html("<div>no structure</div>") is False
    assert InteractiveHTMLAgent._validate_html("<html><body></body></html>") is False  # missing <head


# ---------------------------------------------------------------------------
# 9. test_fallback_contains_content
# ---------------------------------------------------------------------------

def test_fallback_contains_content():
    """Fallback HTML includes the original content."""
    content = "Hello World paragraph"
    html = InteractiveHTMLAgent._generate_fallback(content, "My Topic")
    assert "Hello World paragraph" in html
    assert "<title>My Topic</title>" in html
    assert "<h1>My Topic</h1>" in html


# ---------------------------------------------------------------------------
# 10. test_fallback_xss_safe
# ---------------------------------------------------------------------------

def test_fallback_xss_safe():
    """Special chars are escaped in fallback to prevent XSS."""
    content = '<script>alert("xss")</script> & "quotes"'
    html = InteractiveHTMLAgent._generate_fallback(content)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html
