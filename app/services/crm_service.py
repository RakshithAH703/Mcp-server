from flask import current_app

from app.services.oce_client import OceClient


class CrmService:
    def __init__(self, client: OceClient):
        self.client = client

    def get_profile_details(self, hcp_id: str) -> dict:
        return self.client.get(f"hcps/{hcp_id}/profile")

    def get_hcps_by_specialty(self, specialty: str, limit: int = 25, offset: int = 0) -> dict:
        return self.client.get("hcps", params={"specialty": specialty, "limit": limit, "offset": offset})

    def search_hcps(
        self,
        name: str,
        specialty: str | None = None,
        territory_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        params = {
            "name": name,
            "specialty": specialty,
            "territoryId": territory_id,
            "limit": limit,
            "offset": offset,
        }
        return self.client.get("hcps/search", params={key: value for key, value in params.items() if value is not None})

    def get_account_details(self, account_id: str) -> dict:
        return self.client.get(f"accounts/{account_id}")

    def get_territory_details(self, territory_id: str) -> dict:
        return self.client.get(f"territories/{territory_id}")

    def get_interaction_history(self, hcp_id: str, limit: int = 25, offset: int = 0) -> dict:
        return self.client.get(f"hcps/{hcp_id}/interactions", params={"limit": limit, "offset": offset})

    def create_support_request(self, payload: dict) -> dict:
        return self.client.post("support-requests", json=payload)


def get_crm_service() -> CrmService:
    if "crm_service" not in current_app.extensions:
        settings = current_app.extensions["settings"]
        current_app.extensions["crm_service"] = CrmService(OceClient(settings))
    return current_app.extensions["crm_service"]
