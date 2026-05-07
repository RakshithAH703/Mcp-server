from app.mcp.schemas import ToolDefinition
from app.services.crm_service import get_crm_service


def build_tool(name: str, description: str, input_schema: dict, handler_name: str):
    def handler(arguments: dict) -> dict:
        service = get_crm_service()
        service_handler = getattr(service, handler_name)
        return service_handler(**arguments)

    return ToolDefinition(
        name=name,
        description=description,
        input_schema=input_schema,
        handler=handler,
    )
