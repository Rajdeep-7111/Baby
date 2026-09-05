"""AI provider implementations and their common contract."""

from app.services.providers.base import AIProvider
from app.services.providers.mock import MockAIProvider

__all__ = ["AIProvider", "MockAIProvider"]
