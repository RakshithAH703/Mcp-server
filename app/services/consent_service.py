from flask import current_app

from app.config.settings import Settings
from app.services.onetrust_client import OneTrustClient
from app.utils.errors import BadRequestError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConsentService:
    def __init__(self, client: OneTrustClient, settings: Settings):
        self.client = client
        self.settings = settings
        self._resolved_purpose: dict | None = None

    def list_consents(
        self,
        include_effective_status: bool = True,
        page: int = 0,
        size: int = 20,
    ) -> dict:
        purpose = self.resolve_mcp_purpose()
        effective_purpose_guid = purpose["id"]
        logger.info(
            "onetrust_consent_list_requested",
            purpose_id_present=bool(effective_purpose_guid),
            resolved_purpose_name=purpose.get("name"),
            resolved_purpose_source=purpose.get("source"),
            include_effective_status=include_effective_status,
            page=page,
            size=size,
        )
        params = {
            "purposeGuid": effective_purpose_guid,
            "includeEffectiveStatus": str(include_effective_status).lower(),
            "properties": "ignoreCount",
            "page": page,
            "size": size,
        }
        response = self.client.get(
            "api/consentmanager/v1/datasubjects/profiles",
            params={key: value for key, value in params.items() if value is not None},
        )
        response["_mcp"] = {
            "resolvedPurpose": {
                "id": purpose["id"],
                "name": purpose.get("name"),
                "source": purpose.get("source"),
            }
        }
        return response

    def resolve_mcp_purpose(self) -> dict:
        if self._resolved_purpose:
            return self._resolved_purpose

        if self.settings.onetrust_purpose_name:
            purpose = self._find_purpose_by_exact_name(self.settings.onetrust_purpose_name)
            if purpose:
                self._resolved_purpose = purpose
                return purpose

        purpose = self._find_purpose_by_name_contains(self.settings.onetrust_purpose_name_contains)
        if purpose:
            self._resolved_purpose = purpose
            return purpose

        if self.settings.onetrust_default_purpose_id:
            logger.warning(
                "onetrust_dynamic_purpose_not_found_using_fallback_id",
                purpose_name=self.settings.onetrust_purpose_name,
                purpose_name_contains=self.settings.onetrust_purpose_name_contains,
            )
            self._resolved_purpose = {
                "id": self.settings.onetrust_default_purpose_id,
                "name": None,
                "source": "ONETRUST_DEFAULT_PURPOSE_ID",
            }
            return self._resolved_purpose

        raise BadRequestError(
            "Unable to resolve OneTrust MCP purpose dynamically",
            details={
                "expected_exact_name": self.settings.onetrust_purpose_name,
                "expected_name_contains": self.settings.onetrust_purpose_name_contains,
            },
        )

    def _find_purpose_by_exact_name(self, purpose_name: str) -> dict | None:
        normalized_name = purpose_name.strip().casefold()
        for purpose in self._iter_purposes():
            name = _field(purpose, "Name", "name", "Label", "label")
            purpose_id = _field(purpose, "Id", "id", "Guid", "guid")
            if name and purpose_id and name.strip().casefold() == normalized_name:
                return {"id": purpose_id, "name": name, "source": "ONETRUST_PURPOSE_NAME"}
        return None

    def _find_purpose_by_name_contains(self, text: str) -> dict | None:
        needle = text.strip().casefold()
        matches = []
        for purpose in self._iter_purposes():
            name = _field(purpose, "Name", "name", "Label", "label")
            purpose_id = _field(purpose, "Id", "id", "Guid", "guid")
            if name and purpose_id and needle in name.casefold():
                matches.append({"id": purpose_id, "name": name, "source": "ONETRUST_PURPOSE_NAME_CONTAINS"})

        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise BadRequestError(
                "Multiple OneTrust purposes matched the dynamic MCP purpose rule",
                details={
                    "purpose_name_contains": text,
                    "matched_purpose_names": [match["name"] for match in matches],
                    "fix": "Set ONETRUST_PURPOSE_NAME to the exact OneTrust purpose label in the MCP server environment.",
                },
            )
        return None

    def _iter_purposes(self):
        page = 0
        size = 100
        max_pages = 10

        while page < max_pages:
            response = self.client.get(
                "api/consentmanager/v1/purposes",
                params={"page": page, "size": size, "sort": "name,asc"},
            )
            purposes = _items(response)
            logger.info(
                "onetrust_purposes_page_loaded",
                page=page,
                size=size,
                count=len(purposes),
            )
            for purpose in purposes:
                yield purpose

            if response.get("last") is True or not purposes:
                break
            page += 1


def get_consent_service() -> ConsentService:
    if "consent_service" not in current_app.extensions:
        settings = current_app.extensions["settings"]
        current_app.extensions["consent_service"] = ConsentService(OneTrustClient(settings), settings)
    return current_app.extensions["consent_service"]


def _items(response: dict) -> list[dict]:
    for key in ("content", "items", "data", "purposes"):
        value = response.get(key)
        if isinstance(value, list):
            return value
    return []


def _field(payload: dict, *names: str):
    for name in names:
        if name in payload:
            return payload[name]
    return None
