import importlib
import pkgutil

from jsonschema import Draft202012Validator

from app.mcp.schemas import ToolDefinition
from app.utils.errors import BadRequestError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise RuntimeError(f"Duplicate MCP tool registered: {tool.name}")
        Draft202012Validator.check_schema(tool.input_schema)
        self._tools[tool.name] = tool
        logger.info("mcp_tool_registered", tool=tool.name)

    def list_tools(self) -> list[dict]:
        return [tool.to_mcp_schema() for tool in self._tools.values()]

    def call(self, name: str, arguments: dict | None) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise BadRequestError(f"Unknown MCP tool: {name}")

        clean_arguments = normalize_arguments(arguments or {}, tool.input_schema)
        validator = Draft202012Validator(tool.input_schema)
        errors = sorted(validator.iter_errors(clean_arguments), key=lambda error: list(error.path))
        if errors:
            details = [
                {
                    "path": ".".join(str(part) for part in error.path),
                    "message": error.message,
                }
                for error in errors
            ]
            raise BadRequestError("Tool arguments failed schema validation", details=details)

        logger.info("mcp_tool_call_started", tool=name)
        result = tool.handler(clean_arguments)
        logger.info("mcp_tool_call_completed", tool=name)
        return result


def discover_tools(package_name: str = "app.tools") -> ToolRegistry:
    registry = ToolRegistry()
    package = importlib.import_module(package_name)

    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if module_info.name.endswith(".base"):
            continue
        module = importlib.import_module(module_info.name)
        if getattr(module, "ENABLED", True) is False:
            logger.info("mcp_tool_module_disabled", module=module_info.name)
            continue
        register_tool = getattr(module, "register", None)
        if callable(register_tool):
            register_tool(registry)

    return registry


def normalize_arguments(arguments: dict, input_schema: dict) -> dict:
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    normalized = {}

    for key, value in arguments.items():
        schema = properties.get(key, {})
        schema_type = schema.get("type")

        if value == "" and key not in required:
            continue

        if schema_type == "integer" and isinstance(value, str):
            normalized[key] = int(value) if value.strip() else value
            continue

        if schema_type == "number" and isinstance(value, str):
            normalized[key] = float(value) if value.strip() else value
            continue

        if schema_type == "boolean" and isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                normalized[key] = True
                continue
            if lowered in {"false", "0", "no", "off"}:
                normalized[key] = False
                continue

        normalized[key] = value

    return normalized
