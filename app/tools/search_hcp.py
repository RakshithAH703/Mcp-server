from app.tools.base import build_tool

ENABLED = False


def register(registry):
    registry.register(
        build_tool(
            name="search_hcp_by_name",
            description="Search healthcare professionals in OCE CRM using a name filter.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 2, "maxLength": 150},
                    "specialty": {"type": "string", "minLength": 2, "maxLength": 100},
                    "territory_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            handler_name="search_hcps",
        )
    )
