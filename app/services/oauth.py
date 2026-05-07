import threading
import time

import requests
from requests import Session

from app.config.settings import Settings
from app.utils.errors import AuthenticationError


class OAuthTokenProvider:
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

            if not all([self.settings.oce_token_url, self.settings.oce_client_id, self.settings.oce_client_secret]):
                raise AuthenticationError("OCE OAuth2 configuration is incomplete")

            payload = {
                "grant_type": "client_credentials",
                "client_id": self.settings.oce_client_id,
                "client_secret": self.settings.oce_client_secret,
            }
            if self.settings.oce_scope:
                payload["scope"] = self.settings.oce_scope

            try:
                response = self.session.post(
                    self.settings.oce_token_url,
                    data=payload,
                    timeout=self.settings.oce_timeout_seconds,
                )
            except requests.RequestException as exc:
                raise AuthenticationError("Unable to retrieve OCE OAuth token") from exc

            if response.status_code >= 400:
                raise AuthenticationError("OCE OAuth token request failed", details=_safe_json(response))

            token_payload = response.json()
            access_token = token_payload.get("access_token")
            if not access_token:
                raise AuthenticationError("OCE OAuth token response did not include access_token")

            expires_in = int(token_payload.get("expires_in", 3600))
            self._token = access_token
            self._token_expires_at = time.time() + max(expires_in - 60, 60)
            return access_token

    def clear(self) -> None:
        with self._token_lock:
            self._token = None
            self._token_expires_at = 0.0


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "body": response.text[:500]}
