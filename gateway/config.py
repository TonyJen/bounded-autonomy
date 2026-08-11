import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # project-root .env


@dataclass(frozen=True)
class Settings:
    xai_api_key: str
    xai_base_url: str
    xai_model: str
    device_token: str
    db_path: str
    host: str = "0.0.0.0"
    port: int = 8000


def get_settings() -> Settings:
    return Settings(
        xai_api_key=os.getenv("XAI_API_KEY", ""),
        xai_base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        xai_model=os.getenv("XAI_MODEL", "grok-4.5"),
        device_token=os.getenv("DEVICE_TOKEN", "dev-token"),
        db_path=os.getenv("GUARDIAN_DB", "gateway/guardian.db"),
        host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("GATEWAY_PORT", "8000")),
    )
