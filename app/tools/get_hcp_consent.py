from app.mcp.schemas import ToolDefinition
from app.services.consent_service import get_consent_service

ENABLED = True


def register(registry):
    registry.register(
        ToolDefinition(
            name="list_onetrust_consents",
            description="List OneTrust consent and preference profiles.",
            input_schema={
                "type": "object",
                "properties": {
                    "purpose_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 80,
                        "description": "OneTrust purpose id selected from list_onetrust_purposes.",
                    },
                    "purpose_name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        "description": "Exact OneTrust purpose label/name selected from list_onetrust_purposes.",
                    },
                    "purpose_name_contains": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        "description": "Search text used to resolve a single OneTrust purpose by label/name.",
                    },
                    "include_effective_status": {
                        "type": "boolean",
                        "default": True,
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                    },
                    "size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            handler=_list_onetrust_consents,
        )
    )


def _list_onetrust_consents(arguments: dict) -> dict:
    return get_consent_service().list_consents(**arguments)
