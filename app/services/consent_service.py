from flask import current_app

from app.config.settings import Settings
from app.services.onetrust_client import OneTrustClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConsentService:
    def __init__(self, client: OneTrustClient, settings: Settings):
        self.client = client
        self.settings = settings

    def list_consents(
        self,
        purpose_guid: str | None = None,
        include_effective_status: bool = True,
        page: int = 0,
        size: int = 20,
    ) -> dict:
        effective_purpose_guid = purpose_guid or self.settings.onetrust_default_purpose_id
        logger.info(
            "onetrust_consent_list_requested",
            purpose_id_present=bool(effective_purpose_guid),
            used_default_purpose_id=purpose_guid is None and bool(self.settings.onetrust_default_purpose_id),
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
        return self.client.get(
            "api/consentmanager/v1/datasubjects/profiles",
            params={key: value for key, value in params.items() if value is not None},
        )


def get_consent_service() -> ConsentService:
    if "consent_service" not in current_app.extensions:
        settings = current_app.extensions["settings"]
        current_app.extensions["consent_service"] = ConsentService(OneTrustClient(settings), settings)
    return current_app.extensions["consent_service"]
