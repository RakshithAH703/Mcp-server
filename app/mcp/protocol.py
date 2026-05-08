MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "onetrust-consent-mcp-server"
SERVER_VERSION = "1.0.0"


def initialize_response() -> dict:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
        "capabilities": {
            "tools": {
                "listChanged": False,
            }
        },
    }


def tools_list_response(tools: list[dict]) -> dict:
    return {
        "tools": tools,
    }


def tool_call_response(tool_name: str, result: dict) -> dict:
    return {
        "tool": tool_name,
        "content": [
            {
                "type": "json",
                "json": result,
            }
        ],
        "isError": False,
    }
