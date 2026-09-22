import argparse
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlparse

import yaml

from .core import Repository, Problem, safe_path, serialize, now, MAX_FILE
from .runner import Runner

STATIC = Path(__file__).resolve().parent.parent / "web"


def tool(name, description, properties=None, required=None):
    return {"name": name, "description": description, "inputSchema": {"type": "object", "properties": properties or {},
            "required": required or [], "additionalProperties": False}}


TOOLS = [
    tool("search", "Search EKF artifacts. Read-only. Return a bounded context, not the complete repository.", {"query": {"type": "string"}, "type": {"type": "string"}}),
    tool("read_artifact", "Read an artifact by stable ID, including source, provenance and relationships.", {"id": {"type": "string"}}, ["id"]),
    tool("read_resource", "Read a UTF-8 engineering resource from the repository.", {"path": {"type": "string"}}, ["path"]),
    tool("validate", "Run deterministic EKF conformance and advisory engineering checks."),
    tool("impact", "Get a bounded neighborhood, including assumptions, before changing engineering knowledge.", {"id": {"type": "string"}, "depth": {"type": "integer", "minimum": 1, "maximum": 10}}, ["id"]),
    tool("history", "Read recent Git history and current baselines."),
    tool("propose_change", "Create a reviewable Git branch. Preserve IDs, record uncertainty as assumptions, and distinguish inference from evidence. Cannot merge. File content null means delete.",
         {"title": {"type": "string"}, "changes": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": ["string", "null"]}}, "required": ["path", "content"], "additionalProperties": False}}}, ["title", "changes"]),
    tool("run_tool", "Run Bash/Python or installed tools in Bubblewrap. /workspace is a read-only repository snapshot, /output is writable. No network, host home or credentials. Save reusable tools through propose_change. Returns a run ID; poll run_status.", {"command": {"type": "string"}}, ["command"]),
    tool("run_status", "Read execution status, logs, exact input revision and output hashes.", {"id": {"type": "string"}}, ["id"]),
    tool("read_output", "Read a UTF-8 output from a sandbox run.", {"id": {"type": "string"}, "path": {"type": "string"}}, ["id", "path"]),
    tool("propose_evidence", "Propose evidence for a completed run, link its verification, and preserve execution logs and output files. Does not infer pass/fail from exit status. Human review is required.",
         {"run_id": {"type": "string"}, "verification_id": {"type": "string"}, "title": {"type": "string"}}, ["run_id", "verification_id", "title"]),
]


class Application:
    def __init__(self, repo):
        self.repo = repo
        self.runner = Runner(repo)
        self.session = secrets.token_urlsafe(32)
        token_path = repo.state / "agent-token"
        if not token_path.exists():
            fd = os.open(token_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_urlsafe(32))
        self.agent_token = token_path.read_text().strip()
        human_path = repo.state / "human-token"
        if not human_path.exists():
            fd = os.open(human_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_urlsafe(32))
        self.launch_key = human_path.read_text().strip()

    def read_resource(self, path, ref=""):
        return self.repo.resource(path, ref)

    def evidence(self, run_id, verification_id, title, actor):
        run = self.runner.get(run_id)
        if run["status"] not in ("succeeded", "failed", "limited"):
            raise Problem("Wait for the tool run to complete")
        verification = self.repo.artifact(verification_id)
        if verification["type"] != "verification":
            raise Problem("Select a verification definition")
        aid = "EVID-" + run_id.upper()
        path = "engineering/evidence/" + aid.lower() + ".md"
        log_path = f"test-results/{run_id}/execution.json"
        meta = {"ekf": "0.1", "id": aid, "type": "evidence", "title": title, "status": "draft", "baseline": run["revision"],
                "result": "unassessed", "execution": {"tool": "bubblewrap", "command": run["command"], "tool_revision": run["revision"],
                "run_id": run_id, "exit_code": run.get("exit_code"), "at": run["created"]}, "relations": [{"type": "produces", "resource": log_path}]}
        body = f"# {title}\n\n## Execution\n\nTool status: {run['status']}. An exit code is not an engineering pass/fail assessment.\n\n## Assessment\n\nPending engineering review against the verification pass criteria.\n\n## Output\n\n```text\n{run['stdout']}\n```\n\n## Diagnostics\n\n```text\n{run['stderr']}\n```"
        vmeta = dict(verification["meta"])
        vmeta["relations"] = [*vmeta.get("relations", []), {"type": "produces", "target": aid}]
        changes = [{"path": path, "content": serialize(meta, body)}, {"path": verification["path"], "content": serialize(vmeta, verification["body"])},
                   {"path": log_path, "content": json.dumps(run, indent=2)}]
        for out in run["outputs"]:
            dest = f"test-results/{run_id}/{out['path']}"
            try:
                content = self.runner.output(run_id, out["path"])
            except (Problem, UnicodeError):
                continue  # Binary/large outputs remain available in the local run directory.
            if dest != log_path:
                changes.append({"path": dest, "content": content})
        return self.repo.propose(title, changes, actor)

    def call_tool(self, name, args, actor="agent:external"):
        if not isinstance(args, dict):
            raise Problem("Tool arguments must be an object")
        definition = next((t for t in TOOLS if t["name"] == name), None)
        if not definition:
            raise Problem("Unknown tool", 404)
        schema = definition["inputSchema"]
        if any(k not in args for k in schema["required"]) or any(k not in schema["properties"] for k in args):
            raise Problem("Invalid tool arguments")
        if name == "search":
            query = str(args.get("query", "")).lower()
            artifacts = [a for a in self.repo.snapshot()["artifacts"] if query in (a["id"] + " " + a["title"] + " " + a["body"]).lower()
                         and (not args.get("type") or a["type"] == args["type"])]
            return {"total": len(artifacts), "artifacts": [{k: a[k] for k in ("id", "title", "type", "path", "hash")} for a in artifacts[:50]]}
        if name == "read_artifact":
            return self.repo.artifact(args["id"])
        if name == "read_resource":
            return self.read_resource(args["path"])
        if name == "validate":
            return self.repo.snapshot()["validation"]
        if name == "impact":
            return self.repo.impact(args["id"], args.get("depth", 3))
        if name == "history":
            return {"history": self.repo.history(), "baselines": self.repo.baselines()}
        if name == "propose_change":
            return self.repo.propose(args["title"], args["changes"], actor)
        if name == "run_tool":
            return self.runner.start(args["command"], actor)
        if name == "run_status":
            return self.runner.get(args["id"])
        if name == "read_output":
            return {"content": self.runner.output(args["id"], args["path"])}
        if name == "propose_evidence":
            return self.evidence(args["run_id"], args["verification_id"], args["title"], actor)


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "EKFStudio/0.1"

        def log_message(self, fmt, *args):
            # Do not log request paths, tokens, or engineering content.
            pass

        def send(self, payload, status=200, content_type="application/json; charset=utf-8", cookie=False, download=None):
            if not isinstance(payload, bytes):
                payload = (json.dumps(payload, default=str) if content_type.startswith("application/json") else payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if cookie:
                self.send_header("Set-Cookie", f"ekf_session={app.session}; Path=/; HttpOnly; SameSite=Strict")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(payload)

        def guard(self):
            host = self.headers.get("Host", "")
            valid = {f"localhost:{self.server.server_port}", f"127.0.0.1:{self.server.server_port}"}
            if host not in valid:
                raise Problem("Unrecognized host", 403)
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                raise Problem("Cross-origin requests are not allowed", 403)
            navigation = self.command == "GET" and urlparse(self.path).path == "/" and self.headers.get("Sec-Fetch-Mode") == "navigate"
            if self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site") and not navigation:
                raise Problem("Cross-origin requests are not allowed", 403)

        def auth(self, human=False):
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if token and hmac.compare_digest(token, app.agent_token):
                if human:
                    raise Problem("Agent credentials cannot approve or directly edit engineering state; propose a change.", 403)
                return "agent:external"
            cookies = dict(part.strip().split("=", 1) for part in self.headers.get("Cookie", "").split(";") if "=" in part)
            if not hmac.compare_digest(cookies.get("ekf_session", ""), app.session):
                raise Problem("Open the app in your browser or provide agent credentials", 401)
            return "human:local"

        def do_GET(self):
            try:
                self.guard()
                parsed = urlparse(self.path)
                path, query = parsed.path, parse_qs(parsed.query)
                get = lambda key, default="": query.get(key, [default])[0]
                if path == "/":
                    access = get("access")
                    if access and not hmac.compare_digest(access, app.launch_key):
                        raise Problem("Invalid browser access key", 403)
                    return self.send((STATIC / "index.html").read_bytes(), content_type="text/html; charset=utf-8", cookie=bool(access))
                if path in ("/app.js", "/links.js", "/style.css", "/favicon.svg"):
                    mime = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}[Path(path).suffix]
                    return self.send((STATIC / path[1:]).read_bytes(), content_type=mime)
                self.auth()
                if path == "/api/snapshot":
                    return self.send(app.repo.snapshot(get("ref")))
                if path == "/api/artifact":
                    return self.send(app.repo.artifact(get("id"), get("ref")))
                if path == "/api/impact":
                    return self.send(app.repo.impact(get("id"), get("depth", "3"), get("ref")))
                if path == "/api/compare":
                    return self.send(app.repo.compare(get("before"), get("after")))
                if path == "/api/compare/resource":
                    return self.send(app.repo.compare_resource(get("before"), get("after"), get("path")))
                if path == "/api/compare/artifact":
                    return self.send(app.repo.compare(get("before"), get("after"), get("id")))
                if path == "/api/history":
                    return self.send({"history": app.repo.history(), "baselines": app.repo.baselines()})
                if path == "/api/proposals":
                    return self.send(app.repo.proposals())
                if path == "/api/runs":
                    return self.send(app.runner.get(get("id")) if get("id") else app.runner.list())
                if path == "/api/resource":
                    return self.send(app.read_resource(get("path"), get("ref")))
                if path == "/api/output":
                    return self.send({"content": app.runner.output(get("id"), get("path"))})
                if path == "/api/tools":
                    return self.send({"tools": TOOLS, "sandbox": {"available": app.runner.available, "reason": app.runner.reason},
                                      "token_file": str(app.repo.state / "agent-token")})
                if path == "/api/report":
                    return self.send(app.repo.report(get("kind", "traceability"), get("ref")), content_type="text/markdown; charset=utf-8", download="engineering-report.md")
                raise Problem("Not found", 404)
            except (Problem, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
                self.send({"error": str(exc)}, getattr(exc, "status", 400))
            except Exception:
                self.send({"error": "The server could not complete this request. Check the repository and retry."}, 500)

        def do_POST(self):
            try:
                self.guard()
                path = urlparse(self.path).path
                agent_allowed = path in ("/api/tools/call", "/api/proposals", "/api/runs", "/api/evidence")
                actor = self.auth(human=not agent_allowed)
                if parse_qs(urlparse(self.path).query).get("ref"):
                    raise Problem("Historical versions are read only. Return to the current workspace to make changes.", 409)
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise Problem("Content-Type must be application/json", 415)
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4 * MAX_FILE:
                    raise Problem("Request body must be between 1 byte and 8 MB", 413)
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise Problem("Request body must be an object")
                if path == "/api/artifact":
                    return self.send(app.repo.save(body["path"], body["raw"], body.get("expected_hash")))
                if path == "/api/links":
                    return self.send(app.repo.save_links(body["updates"], body.get("artifact")))
                if path == "/api/review":
                    return self.send(app.repo.review(body["id"], body["expected_hash"]))
                if path == "/api/baselines":
                    return self.send(app.repo.baseline(body["name"]))
                if path == "/api/proposals":
                    return self.send(app.repo.propose(body["title"], body["changes"], actor), 201)
                if path == "/api/proposals/decide":
                    return self.send(app.repo.decide(body["id"], body["decision"]))
                if path == "/api/runs":
                    return self.send(app.runner.start(body["command"], actor), 202)
                if path == "/api/evidence":
                    return self.send(app.evidence(body["run_id"], body["verification_id"], body["title"], actor), 201)
                if path == "/api/sandbox/probe":
                    return self.send(app.runner.probe())
                if path == "/api/tools/call":
                    return self.send(app.call_tool(body["name"], body.get("arguments", {}), actor))
                raise Problem("Not found", 404)
            except (Problem, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
                self.send({"error": str(exc)}, getattr(exc, "status", 400))
            except Exception:
                self.send({"error": "The server could not complete this request. Check the repository and retry."}, 500)
    return Handler


def serve(repo, port=8840):
    app = Application(repo)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    print(f"EKF Studio: http://localhost:{server.server_port}/?access={app.launch_key}\nRepository: {repo.root}\nSandbox: {app.runner.reason}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
