import time
from typing import Any

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.settings import Settings
from app.utils.errors import AuthenticationError, CrmApiError, CrmUnavailableError
from app.utils.logging import get_logger
from app.services.oauth import OAuthTokenProvider

logger = get_logger(__name__)


class OceClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = self._build_session()
        self.oauth_provider = OAuthTokenProvider(settings, self.session)

    def get(self, path: str, *, params: dict | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, *, json: dict | None = None) -> dict[str, Any]:
        return self._request("POST", path, json=json)

    def _build_session(self) -> Session:
        retry = Retry(
            total=self.settings.oce_retry_total,
            connect=self.settings.oce_retry_total,
            read=self.settings.oce_retry_total,
            status=self.settings.oce_retry_total,
            backoff_factor=self.settings.oce_retry_backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = self._url(path)
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        headers.setdefault("Accept", "application/json")
        headers.setdefault("Content-Type", "application/json")

        started = time.perf_counter()
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.settings.oce_timeout_seconds,
                **kwargs,
            )
        except requests.Timeout as exc:
            raise CrmUnavailableError("OCE CRM request timed out") from exc
        except requests.RequestException as exc:
            raise CrmUnavailableError("OCE CRM is unavailable") from exc

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "oce_request_completed",
            method=method,
            path=path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code == 401 and self.settings.oce_auth_type == "oauth2_client_credentials":
            self.oauth_provider.clear()
            headers.update(self._auth_headers(force_refresh=True))
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.settings.oce_timeout_seconds,
                **kwargs,
            )

        return self._parse_response(response)

    def _parse_response(self, response: Response) -> dict[str, Any]:
        if response.status_code >= 500:
            raise CrmUnavailableError("OCE CRM returned a server error", details=_safe_json(response))
        if response.status_code >= 400:
            raise CrmApiError("OCE CRM rejected the request", details=_safe_json(response))
        if response.status_code == 204:
            return {}

        try:
            data = response.json()
        except ValueError as exc:
            raise CrmApiError("OCE CRM returned a non-JSON response") from exc

        if isinstance(data, dict):
            return data
        return {"items": data}

    def _auth_headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        if self.settings.oce_auth_type == "api_token":
            if not self.settings.oce_api_token:
                raise AuthenticationError("OCE_API_TOKEN is required for api_token auth")
            return {"Authorization": f"Bearer {self.settings.oce_api_token}"}

        if self.settings.oce_auth_type == "oauth2_client_credentials":
            return {"Authorization": f"Bearer {self.oauth_provider.get_token(force_refresh=force_refresh)}"}

        raise AuthenticationError(f"Unsupported OCE_AUTH_TYPE: {self.settings.oce_auth_type}")

    def _url(self, path: str) -> str:
        if not self.settings.oce_base_url:
            raise CrmUnavailableError("OCE_BASE_URL is required")
        clean_path = path.strip("/")
        return f"{self.settings.oce_base_url}/api/{self.settings.oce_api_version}/{clean_path}"


def _safe_json(response: Response):
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "body": response.text[:500]}
