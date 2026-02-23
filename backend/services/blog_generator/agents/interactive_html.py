"""
Interactive HTML Agent -- converts content into a self-contained interactive HTML page.

Uses the standard vibe-blog Agent pattern: __init__(self, llm_client) with self.llm.chat().
"""

import re
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert HTML developer. Convert the given content into a self-contained interactive HTML page.
Requirements:
- Single HTML file with embedded CSS and JS
- Clean, modern design with responsive layout
- Include KaTeX CDN for math formula rendering if needed
- Use semantic HTML5 elements
- Add subtle animations and hover effects
- Dark/light theme support via prefers-color-scheme
Return ONLY the HTML code wrapped in ```html ... ``` markers."""


class InteractiveHTMLAgent:
    """Converts content into an interactive HTML page via LLM."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate(self, content: str, topic: str = "") -> dict:
        """Generate interactive HTML from content.

        Returns dict with keys: success, html, fallback.
        Always succeeds -- falls back to a simple CSS-only page on error.
        """
        user_prompt = f"Topic: {topic}\n\nContent:\n{content}" if topic else content
        try:
            response = self.llm.chat(SYSTEM_PROMPT, user_prompt)
            html = self._extract_html(response)
            if html and self._validate_html(html):
                return {"success": True, "html": html, "fallback": False}
            fallback = self._generate_fallback(content, topic)
            return {"success": True, "html": fallback, "fallback": True}
        except Exception as e:
            logger.warning("Interactive HTML generation failed: %s", e)
            fallback = self._generate_fallback(content, topic)
            return {"success": True, "html": fallback, "fallback": True}

    @staticmethod
    def _extract_html(response: str) -> str:
        """Extract HTML from LLM response (code block or raw)."""
        match = re.search(r'```html\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        if '<html' in response.lower() and '</html>' in response.lower():
            start = response.lower().index('<html')
            end = response.lower().index('</html>') + len('</html>')
            return response[start:end]
        return ""

    @staticmethod
    def _validate_html(html: str) -> bool:
        """Basic structural validation -- checks for required tags."""
        required = ['<html', '<head', '<body', '</html>', '</body>']
        html_lower = html.lower()
        return all(tag in html_lower for tag in required)

    @staticmethod
    def _generate_fallback(content: str, topic: str = "") -> str:
        """Generate a simple fallback HTML page (pure CSS, no JS)."""
        title = topic or "Content"
        escaped = (content
                   .replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
@media (prefers-color-scheme: dark) {{ body {{ background: #1a1a2e; color: #e0e0e0; }} }}
pre {{ background: #f5f5f5; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
@media (prefers-color-scheme: dark) {{ pre {{ background: #2d2d44; }} }}
</style>
</head>
<body>
<h1>{title}</h1>
<pre>{escaped}</pre>
</body>
</html>"""
