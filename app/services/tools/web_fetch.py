"""Web page fetching and basic content extraction for Baby."""

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class WebFetchTool:
    """Fetch a public webpage and extract readable text."""

    name = "web_fetch"

    description = (
        "Fetches a public webpage and extracts its readable text content."
    )

    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "The public webpage URL to fetch.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum number of extracted characters.",
                "default": 12000,
            },
        },
    }

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        url = tool_input.get("url")

        if not isinstance(url, str) or not url.strip():
            return {
                "success": False,
                "result": None,
                "error": "'url' must be a non-empty string.",
            }

        url = url.strip()

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {
                "success": False,
                "result": None,
                "error": "Only valid HTTP and HTTPS URLs are supported.",
            }

        max_chars = tool_input.get("max_chars", 12000)

        if not isinstance(max_chars, int):
            max_chars = 12000

        max_chars = max(1000, min(max_chars, 50000))

        try:
            result = self._fetch(url, max_chars)
        except Exception as error:
            return {
                "success": False,
                "result": None,
                "error": f"Web page fetch failed: {error}",
            }

        return {
            "success": True,
            "result": result,
            "error": None,
        }

    def _fetch(self, url: str, max_chars: int) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/151.0 Safari/537.36"
                )
            },
        )

        with urlopen(request, timeout=15) as response:
            raw = response.read()

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            final_url = response.geturl()

        if "text/html" not in content_type.lower():
            text = raw.decode(
                "utf-8",
                errors="replace",
            )

            return {
                "url": final_url,
                "content_type": content_type,
                "title": "",
                "text": text[:max_chars],
                "truncated": len(text) > max_chars,
            }

        html = raw.decode(
            "utf-8",
            errors="replace",
        )

        title = self._extract_title(html)
        text = self._extract_text(html)

        return {
            "url": final_url,
            "content_type": content_type,
            "title": title,
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
        }

    @staticmethod
    def _extract_title(html: str) -> str:
        match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match is None:
            return ""

        return WebFetchTool._clean_text(match.group(1))

    @staticmethod
    def _extract_text(html: str) -> str:
        # Remove content that normally isn't useful as page text.
        html = re.sub(
            r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Preserve some separation between HTML elements.
        html = re.sub(
            r"<(br|p|div|li|h[1-6]|tr|section|article)[^>]*>",
            "\n",
            html,
            flags=re.IGNORECASE,
        )

        # Remove remaining tags.
        html = re.sub(
            r"<[^>]+>",
            " ",
            html,
        )

        return WebFetchTool._clean_text(html)

    @staticmethod
    def _clean_text(value: str) -> str:
        value = unescape(value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()