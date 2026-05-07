from flask import Blueprint, current_app, jsonify, request

from app.mcp.protocol import initialize_response, tool_call_response, tools_list_response
from app.utils.errors import BadRequestError
from app.utils.security import require_api_key

mcp_bp = Blueprint("mcp", __name__)


@mcp_bp.post("/initialize")
@require_api_key
def initialize():
    return jsonify(initialize_response())


@mcp_bp.get("/tools")
@require_api_key
def list_tools():
    registry = current_app.extensions["tool_registry"]
    return jsonify(tools_list_response(registry.list_tools()))


@mcp_bp.post("/tools/call")
@require_api_key
def call_tool():
    payload = request.get_json(silent=True) or {}
    tool_name = payload.get("tool") or payload.get("name")
    arguments = payload.get("arguments", {})

    if not tool_name:
        raise BadRequestError("Missing required field: tool")
    if not isinstance(arguments, dict):
        raise BadRequestError("Field 'arguments' must be an object")

    registry = current_app.extensions["tool_registry"]
    result = registry.call(tool_name, arguments)
    return jsonify(tool_call_response(tool_name, result))
