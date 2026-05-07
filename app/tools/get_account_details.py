from app.tools.base import build_tool

ENABLED = False


def register(registry):
    registry.register(
        build_tool(
            name="get_account_details",
            description="Fetch customer or account details from OCE CRM.",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "minLength": 1, "maxLength": 80},
                },
                "required": ["account_id"],
                "additionalProperties": False,
            },
            handler_name="get_account_details",
        )
    )
