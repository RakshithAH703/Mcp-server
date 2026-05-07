import time
from typing import Any
from urllib.parse import urlparse

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.settings import Settings
from app.services.onetrust_oauth import OneTrustOAuthTokenProvider
from app.utils.errors import CrmApiError, CrmUnavailableError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OneTrustClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = self._build_session()
        self.oauth_provider = OneTrustOAuthTokenProvider(settings, self.session)

    def get(self, path: str, *, params: dict | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def _build_session(self) -> Session:
        retry = Retry(
            total=self.settings.onetrust_retry_total,
            connect=self.settings.onetrust_retry_total,
            read=self.settings.onetrust_retry_total,
            status=self.settings.onetrust_retry_total,
            backoff_factor=self.settings.onetrust_retry_backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.trust_env = self.settings.onetrust_trust_env_proxy
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        logger.info(
            "onetrust_http_session_configured",
            trust_env_proxy=session.trust_env,
        )
        return session

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = self._url(path)
        url_meta = _url_meta(url)
        headers = kwargs.pop("headers", {})
        headers.update({"Authorization": f"Bearer {self.oauth_provider.get_token()}"})
        headers.setdefault("Accept", "application/json")
        headers.setdefault("Content-Type", "application/json")

        started = time.perf_counter()
        logger.info(
            "onetrust_api_request_starting",
            method=method,
            path=path,
            **url_meta,
        )
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.settings.onetrust_timeout_seconds,
                **kwargs,
            )
        except requests.Timeout as exc:
            logger.warning(
                "onetrust_api_request_timeout",
                method=method,
                path=path,
                **url_meta,
                error=str(exc),
            )
            raise CrmUnavailableError("OneTrust request timed out") from exc
        except requests.RequestException as exc:
            logger.warning(
                "onetrust_api_request_failed",
                method=method,
                path=path,
                **url_meta,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise CrmUnavailableError("OneTrust is unavailable") from exc

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "onetrust_request_completed",
            method=method,
            path=path,
            **url_meta,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code == 401:
            self.oauth_provider.clear()
            headers.update({"Authorization": f"Bearer {self.oauth_provider.get_token(force_refresh=True)}"})
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.settings.onetrust_timeout_seconds,
                **kwargs,
            )

        return self._parse_response(response)

    def _parse_response(self, response: Response) -> dict[str, Any]:
        if response.status_code >= 500:
            raise CrmUnavailableError("OneTrust returned a server error", details=_safe_json(response))
        if response.status_code >= 400:
            raise CrmApiError("OneTrust rejected the request", details=_safe_json(response))
        if response.status_code == 204:
            return {}

        try:
            data = response.json()
        except ValueError as exc:
            raise CrmApiError("OneTrust returned a non-JSON response") from exc

        if isinstance(data, dict):
            return data
        return {"items": data}

    def _url(self, path: str) -> str:
        if not self.settings.onetrust_base_url:
            raise CrmUnavailableError("ONETRUST_BASE_URL is required")
        clean_path = path.strip("/")
        return f"{self.settings.onetrust_base_url}/{clean_path}"


def _safe_json(response: Response):
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
