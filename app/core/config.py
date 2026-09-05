from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for Baby."""

    app_name: str = os.getenv(
        "BABY_APP_NAME",
        "Baby",
    )

    ai_provider: str = os.getenv(
        "BABY_AI_PROVIDER",
        "mock",
    )

    gemini_model: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash",
    )


settings = Settings()