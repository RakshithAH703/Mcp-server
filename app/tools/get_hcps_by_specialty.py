from app.tools.base import build_tool

ENABLED = False


def register(registry):
    registry.register(
        build_tool(
            name="get_hcps_by_specialty",
            description="Fetch healthcare professionals under a specific specialty from OCE CRM.",
            input_schema={
                "type": "object",
                "properties": {
                    "specialty": {"type": "string", "minLength": 2, "maxLength": 100},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
                "required": ["specialty"],
                "additionalProperties": False,
            },
            handler_name="get_hcps_by_specialty",
        )
    )
