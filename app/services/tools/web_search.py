"""Local web search tool for Baby."""

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


class WebSearchTool:
    """Search the public web and return structured search results."""

    name = "web_search"
    description = "Searches the public web for information and returns relevant results."

    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "The web search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return.",
                "default": 5,
            },
        },
    }

    _SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        query = tool_input.get("query")

        if not isinstance(query, str) or not query.strip():
            return {
                "success": False,
                "result": None,
                "error": "'query' must be a non-empty string.",
            }

        max_results = tool_input.get("max_results", 5)

        if not isinstance(max_results, int):
            max_results = 5

        max_results = max(1, min(max_results, 10))

        try:
            results = self._search(query.strip(), max_results)
        except Exception as error:
            return {
                "success": False,
                "result": None,
                "error": f"Web search failed: {error}",
            }

        return {
            "success": True,
            "result": {
                "query": query.strip(),
                "results": results,
            },
            "error": None,
        }

    def _search(self, query: str, max_results: int) -> list[dict[str, str]]:
        url = self._SEARCH_URL.format(query=quote_plus(query))

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
                )
            },
        )

        with urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")

        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        results: list[dict[str, str]] = []

        for match in pattern.finditer(html):
            url_value = unescape(match.group(1))
            title = self._clean_html(match.group(2))

            if not title:
                continue

            results.append(
                {
                    "title": title,
                    "url": url_value,
                }
            )

            if len(results) >= max_results:
                break

        return results

    @staticmethod
    def _clean_html(value: str) -> str:
        value = re.sub(r"<[^>]+>", "", value)
        value = unescape(value)
        return " ".join(value.split())