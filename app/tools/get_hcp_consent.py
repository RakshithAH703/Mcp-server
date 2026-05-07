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
                    "purpose_guid": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 80,
                        "description": "Optional OneTrust purpose GUID to filter consent for a specific purpose.",
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
