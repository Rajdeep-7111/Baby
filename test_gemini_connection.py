from app.services.providers.gemini import GeminiProvider


provider = GeminiProvider()

response = provider.generate(
    "Explain Docker in two simple sentences."
)

print(response)