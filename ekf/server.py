import argparse
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, urlparse, quote

import yaml

from .core import Repository, Problem, safe_path, serialize, now, MAX_FILE
from .runner import Runner
from .projects import Projects, Jobs
from .github import GitHub

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
    def __init__(self, repo=None, projects_folder=None):
        self.lock = threading.RLock()
        self.projects = Projects(projects_folder or (repo.project_root.parent if repo else Path.cwd()/'projects'), repo.project_root if repo else None)
        self.jobs = Jobs()
        self.github = GitHub(self.projects.state)
        self.repo = None
        self.runner = None
        self.agent_token = ''
        self.cache = {}
        self.session = secrets.token_urlsafe(32)
        if repo:
            self.activate(repo)
        elif self.projects.data['selected']:
            try: self.open_project(self.projects.data['selected'])
            except (Problem,OSError,ValueError): self.projects.select(None)
        human_path = (repo.state if repo else self.projects.state) / 'human-token'
        self.launch_key = self.token(human_path)

    @staticmethod
    def token(path):
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd,'w') as stream: stream.write(secrets.token_urlsafe(32))
        return path.read_text().strip()

    def activate(self, repo):
        identity = self.projects.register(repo.project_root)
        if self.runner and self.runner.active.locked():
            raise Problem('Wait for the current tool run to finish before switching projects.',409)
        self.repo = repo
        self.runner = self.cache[identity][1] if identity in self.cache else Runner(repo)
        token_path = repo.state / "agent-token"
        self.agent_token = self.token(token_path)
        self.cache[identity] = (repo,self.runner)
        self.projects.select(identity)
        return {'project':identity}

    def open_project(self, identity):
        if self.jobs.active: raise Problem('Wait for project setup to finish before switching projects.',409)
        repo = self.cache[identity][0] if identity in self.cache else Repository(self.projects.root(identity))
        return self.activate(repo)

    def require_project(self):
        if not self.repo: raise Problem('Create or open a project first.',409)

    def project_context(self, identity):
        current = self.projects.identity(self.repo.project_root) if self.repo else None
        if identity is not None and identity != current:
            raise Problem('The project changed in another tab. Refresh before continuing; no changes were saved.',409)

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
        if actor == "human:local":
            return self.repo.workflow.save_files(changes, title)
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

        def send(self, payload, status=200, content_type="application/json; charset=utf-8", cookie=False, download=None, attachment=False):
            if not isinstance(payload, bytes):
                payload = (json.dumps(payload, default=str) if content_type.startswith("application/json") else payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'" if attachment else "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https: http:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if cookie:
                self.send_header("Set-Cookie", f"ekf_session={app.session}; Path=/; HttpOnly; SameSite=Strict")
            if download:
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(download, safe=""))
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
            with app.lock:
                self.handle_get()

        def handle_get(self):
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
                if path in ("/app.js", "/links.js", "/changes.js", "/projects.js", "/style.css", "/favicon.svg", "/dist/markdown.js", "/dist/markdown.css"):
                    mime = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}[Path(path).suffix]
                    return self.send((STATIC / path[1:]).read_bytes(), content_type=mime)
                human_only=path.startswith(('/api/projects','/api/github','/api/setup-jobs'))
                self.auth(human=human_only)
                if path == "/api/help/workflow":
                    return self.send({"markdown": (STATIC.parent / "docs" / "workflow-help.md").read_text(encoding="utf-8")})
                if path == '/api/projects':
                    return self.send({'projects':app.projects.list(),'folder':str(app.projects.folder),'selected':app.projects.data['selected'],'setup_job':app.jobs.active})
                if path == '/api/setup-jobs': return self.send(app.jobs.get(get('id')))
                if path == '/api/github/status': return self.send(app.github.status())
                if path == '/api/github/repositories': return self.send(app.github.repositories(get('page',1)))
                if path == '/api/github/owners': return self.send(app.github.owners())
                if path == '/api/github/inspect': return self.send(app.github.inspect(get('repository')))
                app.require_project()
                app.project_context(self.headers.get('X-EKF-Project'))
                if path == '/api/github/connection':
                    name=app.github.remote(app.repo)
                    return self.send({'repository':name,'url':'https://github.com/'+name if name else None,'main':app.repo.workflow.main,'commit':app.repo.workflow.main_head()})
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
                if path == "/api/proposals/conflict":
                    return self.send(app.repo.workflow.conflict(get("id"), get("path")))
                if path == "/api/runs":
                    return self.send(app.runner.get(get("id")) if get("id") else app.runner.list())
                if path == "/api/resource":
                    return self.send(app.read_resource(get("path"), get("ref")))
                if path == "/api/asset":
                    data, mime = app.repo.asset(get("path"), get("ref"))
                    return self.send(data, content_type=mime, attachment=True,
                                     download=Path(get("path")).name if get("download") or not mime.startswith("image/") else None)
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
            with app.lock:
                self.handle_post()

        def handle_post(self):
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
                limit = 16 * MAX_FILE if path in ("/api/artifact", "/api/links") else 4 * MAX_FILE
                if not 0 < size <= limit:
                    raise Problem(f"Request body must be between 1 byte and {limit // (1024 * 1024)} MB", 413)
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise Problem("Request body must be an object")
                if path.startswith('/api/projects/') and app.jobs.active:
                    raise Problem('Wait for project or GitHub setup to finish before changing projects.',409)
                if path == '/api/projects/create':
                    identity=app.projects.create(body['title'],body['folder'])
                    return self.send(app.open_project(identity),201)
                if path == '/api/projects/open':
                    identity=body.get('id')
                    if not identity:
                        root=Path(body['path']).expanduser().resolve()
                        if not (root/'ekf.yaml').is_file() or not (root/'.git').exists():
                            raise Problem('Choose an existing EKF project folder containing ekf.yaml and its own Git repository.')
                        repo=Repository(root)
                        identity=app.projects.register(repo.project_root)
                        return self.send(app.activate(repo))
                    return self.send(app.open_project(identity))
                if path == '/api/projects/forget':
                    app.projects.forget(body['id']); return self.send({'removed':True})
                if path == '/api/github/login': return self.send(app.jobs.start('Preparing GitHub sign-in…',app.github.sign_in),202)
                if path == '/api/github/login/cancel': app.github.cancel_login(); return self.send({'cancelled':True})
                if path == '/api/github/clone':
                    return self.send(app.jobs.start('Downloading your GitHub project…',lambda progress:app.github.clone(app.projects,body['repository'],body['folder'])),202)
                app.require_project()
                app.project_context(body.get('project'))
                app.repo.workflow.assert_context(body.get("workspace"))
                if path in ('/api/github/publish','/api/github/connect'):
                    repo=app.repo
                    if body.get('expected_main')!=repo.workflow.main_head():
                        raise Problem('The approved project changed. Reopen GitHub setup before uploading.',409)
                    def transfer(progress):
                        with repo.lock:
                            if body.get('expected_main')!=repo.workflow.main_head(): raise Problem('The approved project changed. Reopen GitHub setup.',409)
                            if path.endswith('/publish'):
                                return app.github.publish(repo,body['owner'],body['name'],body['visibility'],body.get('description',''))
                            return app.github.connect(repo,body['repository'],body.get('upload') is True)
                    return self.send(app.jobs.start('Connecting your project to GitHub…',transfer),202)
                if path == "/api/files":
                    return self.send(app.repo.workflow.save_files(body["changes"], body.get("title", "Edit project files")))
                if path == "/api/changes/start":
                    return self.send(app.repo.workflow.start(body["title"]))
                if path == "/api/changes/switch":
                    return self.send(app.repo.workflow.switch(body.get("id")))
                if path == "/api/proposals/rename":
                    return self.send(app.repo.workflow.rename(body["id"], body["title"]))
                if path == "/api/proposals/update":
                    return self.send(app.repo.workflow.update(body["id"], body.get("run_checks", True)))
                if path == "/api/proposals/check":
                    return self.send(app.repo.workflow.check_proposal(body["id"]))
                if path == "/api/proposals/resolve":
                    return self.send(app.repo.workflow.resolve(body["id"], body["path"], body["choice"], body.get("content"), body.get("expected_commit"), body.get("expected_main")))
                if path == "/api/artifact":
                    return self.send(app.repo.save(body["path"], body["raw"], body.get("expected_hash"), assets=body.get("assets", [])))
                if path == "/api/links":
                    return self.send(app.repo.save_links(body["updates"], body.get("artifact")))
                if path == "/api/review":
                    return self.send(app.repo.review(body["id"], body["expected_hash"]))
                if path == "/api/baselines":
                    return self.send(app.repo.baseline(body["name"]))
                if path == "/api/proposals":
                    p = app.repo.propose(body["title"], body["changes"], actor)
                    if actor == "human:local":
                        app.repo.workflow.switch(p["id"])
                    return self.send(p, 201)
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


def serve(repo=None, port=8840, projects_folder=None):
    app = Application(repo, projects_folder)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    print(f"EKF Studio: http://localhost:{server.server_port}/?access={app.launch_key}\nProjects: {app.projects.folder}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
