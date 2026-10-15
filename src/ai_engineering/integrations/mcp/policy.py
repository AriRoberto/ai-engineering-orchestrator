import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class MCPProjectPolicy(BaseModel):
    project_id: str
    mode: str = "read-only"
    allowed_tools: frozenset[str] = Field(default_factory=frozenset)


class MCPPolicyStore:
    def __init__(self, config_dir: str) -> None:
        self.config_dir = Path(config_dir)

    def get(self, project_id: str) -> MCPProjectPolicy | None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", project_id):
            return None
        path = self.config_dir / f"{project_id}.yaml"
        if not path.is_file():
            return None
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        mcp = raw.get("mcp", {})
        return MCPProjectPolicy(
            project_id=raw.get("id", project_id),
            mode=raw.get("mode", "read-only"),
            allowed_tools=frozenset(mcp.get("allowed_tools", [])),
        )
