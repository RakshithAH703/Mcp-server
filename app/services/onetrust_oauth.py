import threading
import time
from urllib.parse import urlparse

import requests
from requests import Session

from app.config.settings import Settings
from app.utils.errors import AuthenticationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OneTrustOAuthTokenProvider:
    def __init__(self, settings: Settings, session: Session):
        self.settings = settings
        self.session = session
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def get_token(self, *, force_refresh: bool = False) -> str:
        with self._token_lock:
            if not force_refresh and self._token and time.time() < self._token_expires_at:
                return self._token

            token_url = self._token_url()
            token_url_meta = _url_meta(token_url)
            logger.info(
                "onetrust_oauth_token_request_starting",
                **token_url_meta,
                client_id_present=bool(self.settings.onetrust_client_id),
                client_secret_present=bool(self.settings.onetrust_client_secret),
                scope_present=bool(self.settings.onetrust_scope),
            )
            if not all([self.settings.onetrust_client_id, self.settings.onetrust_client_secret]):
                raise AuthenticationError("OneTrust OAuth2 client credentials are incomplete")

            payload = {
                "grant_type": "client_credentials",
                "client_id": self.settings.onetrust_client_id,
                "client_secret": self.settings.onetrust_client_secret,
            }
            if self.settings.onetrust_scope:
                payload["scope"] = self.settings.onetrust_scope

            try:
                response = self.session.post(
                    token_url,
                    data=payload,
                    timeout=self.settings.onetrust_timeout_seconds,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "onetrust_oauth_token_request_failed",
                    **token_url_meta,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise AuthenticationError(
                    "Unable to retrieve OneTrust OAuth token",
                    details={
                        **token_url_meta,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ) from exc

            logger.info(
                "onetrust_oauth_token_response_received",
                **token_url_meta,
                status_code=response.status_code,
            )

            if response.status_code >= 400:
                logger.warning(
                    "onetrust_oauth_token_rejected",
                    **token_url_meta,
                    status_code=response.status_code,
                    response=_safe_json(response),
                )
                raise AuthenticationError("OneTrust OAuth token request failed", details=_safe_json(response))

            token_payload = response.json()
            access_token = token_payload.get("access_token")
            if not access_token:
                raise AuthenticationError("OneTrust OAuth token response did not include access_token")

            expires_in = int(token_payload.get("expires_in", 3600))
            self._token = access_token
            self._token_expires_at = time.time() + max(expires_in - 60, 60)
            logger.info(
                "onetrust_oauth_token_cached",
                **token_url_meta,
                expires_in=expires_in,
            )
            return access_token

    def clear(self) -> None:
        with self._token_lock:
            self._token = None
            self._token_expires_at = 0.0

    def _token_url(self) -> str:
        if self.settings.onetrust_token_url:
            return self.settings.onetrust_token_url
        if not self.settings.onetrust_base_url:
            raise AuthenticationError("ONETRUST_BASE_URL is required")
        return f"{self.settings.onetrust_base_url}/api/access/v1/oauth/token"


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "body": response.text[:500]}


def _url_meta(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "url_scheme": parsed.scheme,
        "url_host": parsed.hostname,
        "url_port": parsed.port,
        "url_path": parsed.path,
    }
