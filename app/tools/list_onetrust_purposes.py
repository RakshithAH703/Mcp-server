from app.mcp.schemas import ToolDefinition
from app.services.consent_service import get_consent_service

ENABLED = True


def register(registry):
    registry.register(
        ToolDefinition(
            name="list_onetrust_purposes",
            description="List OneTrust consent purposes so an agent can choose which purpose to use for consent lookup.",
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        "description": "Optional text filter applied to purpose name or description.",
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                    },
                    "size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            handler=_list_onetrust_purposes,
        )
    )


def _list_onetrust_purposes(arguments: dict) -> dict:
    return get_consent_service().list_purposes(**arguments)
