"""Tool calling: load tenant tool definitions, expose them as ToolSpecs, and
execute tool calls (HTTP webhooks or built-ins) with structured outputs."""
from __future__ import annotations

import json
import uuid

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.llm.base import ToolCall, ToolSpec
from app.models.tool import ToolDefinition
from app.repositories.repos import ToolRepo

log = get_logger("services.tools")


class ToolService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.repo = ToolRepo(session, tenant_id)

    async def list_specs(self) -> tuple[list[ToolSpec], dict[str, ToolDefinition]]:
        defs = await self.repo.active()
        specs = [
            ToolSpec(name=d.name, description=d.description, input_schema=d.input_schema or {"type": "object", "properties": {}})
            for d in defs
        ]
        registry = {d.name: d for d in defs}
        return specs, registry

    async def execute(self, call: ToolCall, registry: dict[str, ToolDefinition]) -> str:
        tool = registry.get(call.name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {call.name}"})

        if tool.handler_type == "http":
            return await self._http_handler(tool, call.arguments)
        if tool.handler_type == "builtin":
            return self._builtin(tool, call.arguments)
        return json.dumps({"error": f"Unsupported handler: {tool.handler_type}"})

    async def _http_handler(self, tool: ToolDefinition, args: dict) -> str:
        cfg = tool.handler_config or {}
        url = cfg.get("url")
        if not url:
            return json.dumps({"error": "Tool has no webhook URL configured"})
        method = cfg.get("method", "POST").upper()
        headers = dict(cfg.get("headers", {}))
        # Inject tenant context so the downstream system can scope its response.
        headers.setdefault("X-Tenant-Id", str(self.tenant_id))
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.request(
                    method, url, json=args if method != "GET" else None,
                    params=args if method == "GET" else None, headers=headers,
                )
                resp.raise_for_status()
                return resp.text[:8000]
        except Exception as e:
            log.warning("tool_http_error", tool=tool.name, error=str(e))
            return json.dumps({"error": f"Tool call failed: {e}"})

    def _builtin(self, tool: ToolDefinition, args: dict) -> str:
        # Place for platform-provided tools (e.g. current time, math). Stubbed.
        return json.dumps({"result": "builtin tool executed", "args": args})
