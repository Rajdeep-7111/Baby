from app.services.ai import AIService
from app.services.providers.mock import MockAIProvider


def test_ai_service_delegates_to_mock_provider() -> None:
    service = AIService(provider=MockAIProvider())

    assert service.generate("Hello Baby") == "Baby mock response: I received 'Hello Baby'"
    assert service.interpret("calculate 2 + 2") == "calculator"
