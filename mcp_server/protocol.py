from __future__ import annotations
import json, sys
from typing import Any

def log(message: str) -> None:
    print(f"[android-mcp] {message}", file=sys.stderr, flush=True)

def result(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}]}

def error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}

def serve(tools: dict, dispatch) -> None:
    for line in sys.stdin:
        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method")
            if method == "initialize":
                response = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "android-agent-harness", "version": "0.2.0"}}
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response = {"tools": [{"name": name, **spec} for name, spec in tools.items()]}
            elif method == "tools/call":
                params = request.get("params", {})
                response = dispatch(params["name"], params.get("arguments", {}))
            else:
                response = {"error": {"code": -32601, "message": f"Method not found: {method}"}}
            if request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": response}), flush=True)
        except Exception as exc:
            log(f"error: {exc}")
            if request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}), flush=True)
