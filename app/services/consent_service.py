from app.config.settings import Settings
from app.services.onetrust_client import OneTrustClient
from app.utils.errors import BadRequestError
from app.utils.logging import get_logger

logger = get_logger(__name__)

_consent_service: "ConsentService | None" = None


class ConsentService:
    def __init__(self, client: OneTrustClient, settings: Settings):
        self.client = client
        self.settings = settings

    def list_consents(
        self,
        purpose_id: str | None = None,
        purpose_name: str | None = None,
        purpose_name_contains: str | None = None,
        include_effective_status: bool = True,
        page: int = 0,
        size: int = 20,
    ) -> dict:
        purpose = self.resolve_purpose(
            purpose_id=purpose_id,
            purpose_name=purpose_name,
            purpose_name_contains=purpose_name_contains,
        )
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

    def list_purposes(self, search: str | None = None, page: int = 0, size: int = 50) -> dict:
        page = max(page, 0)
        size = _bounded_page_size(size)

        response = self.client.get(
            "api/consentmanager/v1/purposes",
            params={"page": page, "size": size, "sort": "name,asc"},
        )
        purposes = [_purpose_summary(purpose) for purpose in _items(response)]

        if search:
            needle = search.strip().casefold()
            purposes = [
                purpose
                for purpose in purposes
                if needle in (purpose.get("name") or "").casefold()
                or needle in (purpose.get("description") or "").casefold()
            ]

        return {
            "purposes": purposes,
            "page": response.get("number", page),
            "size": response.get("size", size),
            "numberOfElements": len(purposes),
            "sourceNumberOfElements": response.get("numberOfElements"),
            "totalElements": response.get("totalElements"),
            "totalPages": response.get("totalPages"),
            "empty": len(purposes) == 0,
            "first": response.get("first"),
            "last": response.get("last"),
            "nextPage": None if response.get("last") is True else response.get("number", page) + 1,
            "search": search,
            "searchScope": "current_page" if search else None,
        }

    def resolve_purpose(
        self,
        purpose_id: str | None = None,
        purpose_name: str | None = None,
        purpose_name_contains: str | None = None,
    ) -> dict:
        if purpose_id:
            return {"id": purpose_id, "name": None, "source": "tool_argument:purpose_id"}

        if purpose_name:
            purpose = self._find_purpose_by_exact_name(purpose_name)
            if purpose:
                return purpose
            raise BadRequestError(
                "No OneTrust purpose matched the provided purpose_name",
                details={"purpose_name": purpose_name},
            )

        if purpose_name_contains:
            purpose = self._find_purpose_by_name_contains(purpose_name_contains)
            if purpose:
                return purpose
            raise BadRequestError(
                "No OneTrust purpose matched the provided purpose_name_contains",
                details={"purpose_name_contains": purpose_name_contains},
            )

        if self.settings.onetrust_purpose_name:
            purpose = self._find_purpose_by_exact_name(self.settings.onetrust_purpose_name)
            if purpose:
                return purpose

        if self.settings.onetrust_default_purpose_id:
            logger.warning(
                "onetrust_purpose_not_provided_using_fallback_id",
                purpose_name=self.settings.onetrust_purpose_name,
            )
            return {
                "id": self.settings.onetrust_default_purpose_id,
                "name": None,
                "source": "ONETRUST_DEFAULT_PURPOSE_ID",
            }

        raise BadRequestError(
            "A OneTrust purpose must be specified",
            details={
                "accepted_arguments": ["purpose_id", "purpose_name", "purpose_name_contains"],
                "hint": "Call list_onetrust_purposes first, then call list_onetrust_consents with the selected purpose name or id.",
            },
        )

    def _find_purpose_by_exact_name(self, purpose_name: str) -> dict | None:
        normalized_name = purpose_name.strip().casefold()
        for purpose in self._iter_purposes():
            name = _field(purpose, "Name", "name", "Label", "label")
            purpose_id = _field(purpose, "Id", "id", "Guid", "guid")
            if name and purpose_id and name.strip().casefold() == normalized_name:
                return {"id": purpose_id, "name": name, "source": "tool_argument:purpose_name"}
        return None

    def _find_purpose_by_name_contains(self, text: str) -> dict | None:
        needle = text.strip().casefold()
        matches = []
        for purpose in self._iter_purposes():
            name = _field(purpose, "Name", "name", "Label", "label")
            purpose_id = _field(purpose, "Id", "id", "Guid", "guid")
            if name and purpose_id and needle in name.casefold():
                matches.append({"id": purpose_id, "name": name, "source": "tool_argument:purpose_name_contains"})

        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise BadRequestError(
                "Multiple OneTrust purposes matched the dynamic MCP purpose rule",
                details={
                    "purpose_name_contains": text,
                    "matched_purpose_names": [match["name"] for match in matches],
                    "fix": "Call list_onetrust_consents again with purpose_name set to one exact purpose label, or purpose_id set to the selected purpose id.",
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


def create_consent_service(settings: Settings | None = None) -> ConsentService:
    resolved_settings = settings or Settings.from_env()
    return ConsentService(OneTrustClient(resolved_settings), resolved_settings)


def get_consent_service(settings: Settings | None = None) -> ConsentService:
    global _consent_service
    if _consent_service is None:
        _consent_service = create_consent_service(settings)
    return _consent_service


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


def _purpose_summary(purpose: dict) -> dict:
    return {
        "id": _field(purpose, "Id", "id", "Guid", "guid"),
        "name": _field(purpose, "Name", "name", "Label", "label"),
        "description": _field(purpose, "Description", "description"),
        "status": _field(purpose, "Status", "status"),
        "version": _field(purpose, "Version", "version"),
        "externalReference": _field(purpose, "ExternalReference", "externalReference"),
        "purposeType": _field(purpose, "PurposeType", "purposeType"),
    }


def _bounded_page_size(size: int) -> int:
    if size < 1:
        return 50
    return min(size, 100)
