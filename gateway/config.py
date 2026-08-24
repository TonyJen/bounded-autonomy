import logging
import os
import secrets
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # project-root .env

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    xai_api_key: str
    xai_base_url: str
    xai_model: str
    device_token: str
    db_path: str
    operator_token: str = ""
    host: str = "0.0.0.0"
    port: int = 8000


def get_settings() -> Settings:
    # No public default credential: the repo is published, so a hardcoded
    # fallback token would be known to anyone who reads it. Unset means an
    # ephemeral random token per boot — devices/simulator must be given it.
    device_token = os.getenv("DEVICE_TOKEN", "")
    if not device_token:
        device_token = secrets.token_urlsafe(24)
        logger.warning(
            "DEVICE_TOKEN not set — generated ephemeral token for this boot: "
            "%s (set DEVICE_TOKEN in .env to persist it)", device_token)
    return Settings(
        xai_api_key=os.getenv("XAI_API_KEY", ""),
        xai_base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        xai_model=os.getenv("XAI_MODEL", "grok-4.5"),
        device_token=device_token,
        # BOUNDED_AUTONOMY_DB is canonical; GUARDIAN_DB kept as a fallback
        # for pre-rename local setups.
        db_path=os.getenv("BOUNDED_AUTONOMY_DB")
                or os.getenv("GUARDIAN_DB", "gateway/bounded_autonomy.db"),
        operator_token=os.getenv("OPERATOR_TOKEN", ""),
        host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("GATEWAY_PORT", "8000")),
    )
