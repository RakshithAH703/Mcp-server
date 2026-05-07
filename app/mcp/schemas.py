from dataclasses import dataclass
from typing import Callable


ToolHandler = Callable[[dict], dict]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: ToolHandler

    def to_mcp_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
