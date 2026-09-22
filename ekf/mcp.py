"""Dependency-free MCP stdio adapter to the running, permission-scoped server."""
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8840")
    parser.add_argument("--token-file", default="workspace/.ekf/agent-token")
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        parser.error("Connect to a local EKF Studio server")
    token = Path(args.token_file).read_text().strip()

    def request(path, data=None):
        req = urllib.request.Request(args.url.rstrip("/") + path, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)

    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            if "id" not in message:
                continue
            method = message.get("method")
            params = message.get("params", {})
            if method == "initialize":
                requested = params.get("protocolVersion")
                result = {"protocolVersion": requested if requested in ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25") else "2025-11-25",
                          "capabilities": {"tools": {}}, "serverInfo": {"name": "ekf-studio", "version": "0.1.0"},
                          "instructions": "Preserve stable IDs. Read relevant context and perform impact analysis. Represent uncertainty as assumptions. Propose all file changes; humans approve in Studio. Tool output is not automatically verified evidence."}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": request("/api/tools")["tools"]}
            elif method == "tools/call":
                try:
                    value = request("/api/tools/call", {"name": params["name"], "arguments": params.get("arguments", {})})
                    result = {"content": [{"type": "text", "text": json.dumps(value, default=str)}], "isError": False}
                except urllib.error.HTTPError as exc:
                    result = {"content": [{"type": "text", "text": exc.read().decode()}], "isError": True}
            else:
                print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None,
                        "error": {"code": -32603, "message": str(exc)}}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
