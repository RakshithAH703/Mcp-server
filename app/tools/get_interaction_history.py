from app.tools.base import build_tool

ENABLED = False


def register(registry):
    registry.register(
        build_tool(
            name="get_interaction_history",
            description="Fetch recent appointment or interaction history for an HCP from OCE CRM.",
            input_schema={
                "type": "object",
                "properties": {
                    "hcp_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
                "required": ["hcp_id"],
                "additionalProperties": False,
            },
            handler_name="get_interaction_history",
        )
    )
