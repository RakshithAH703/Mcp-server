from app.tools.base import build_tool

ENABLED = False


def register(registry):
    registry.register(
        build_tool(
            name="get_hcp_profile",
            description="Fetch profile details for a healthcare professional from OCE CRM.",
            input_schema={
                "type": "object",
                "properties": {
                    "hcp_id": {"type": "string", "minLength": 1, "maxLength": 80},
                },
                "required": ["hcp_id"],
                "additionalProperties": False,
            },
            handler_name="get_profile_details",
        )
    )
