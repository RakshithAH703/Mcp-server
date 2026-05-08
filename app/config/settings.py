import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    flask_env: str
    host: str
    port: int
    log_level: str
    mcp_api_key: str | None
    onetrust_base_url: str | None
    onetrust_token_url: str | None
    onetrust_client_id: str | None
    onetrust_client_secret: str | None
    onetrust_scope: str | None
    onetrust_default_purpose_id: str | None
    onetrust_timeout_seconds: int
    onetrust_retry_total: int
    onetrust_retry_backoff_factor: float
    onetrust_trust_env_proxy: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            flask_env=os.getenv("FLASK_ENV", "production"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            mcp_api_key=os.getenv("MCP_API_KEY") or None,
            onetrust_base_url=_optional_url("ONETRUST_BASE_URL"),
            onetrust_token_url=os.getenv("ONETRUST_TOKEN_URL") or None,
            onetrust_client_id=os.getenv("ONETRUST_CLIENT_ID") or None,
            onetrust_client_secret=os.getenv("ONETRUST_CLIENT_SECRET") or None,
            onetrust_scope=os.getenv("ONETRUST_SCOPE") or None,
            onetrust_default_purpose_id=os.getenv("ONETRUST_DEFAULT_PURPOSE_ID") or None,
            onetrust_timeout_seconds=int(os.getenv("ONETRUST_TIMEOUT_SECONDS", "20")),
            onetrust_retry_total=int(os.getenv("ONETRUST_RETRY_TOTAL", "3")),
            onetrust_retry_backoff_factor=float(os.getenv("ONETRUST_RETRY_BACKOFF_FACTOR", "0.5")),
            onetrust_trust_env_proxy=_bool_env("ONETRUST_TRUST_ENV_PROXY", default=False),
        )

    def to_flask_config(self) -> dict:
        return {
            "ENV": self.flask_env,
            "HOST": self.host,
            "PORT": self.port,
            "JSON_SORT_KEYS": False,
        }


def _optional_url(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    return value.rstrip("/")


def _bool_env(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
