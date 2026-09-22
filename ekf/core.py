"""Files are authoritative. All indexes and reports are rebuilt from the repository."""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone

import yaml

CORE_TYPES = ["intent", "requirement", "constraint", "interface", "architecture", "component",
              "decision", "assumption", "hazard", "risk", "verification", "evidence"]
RELATIONS = ["derives-from", "refines", "depends-on", "allocated-to", "implemented-by",
             "verified-by", "validated-by", "mitigates", "interfaces-with", "supersedes", "produces"]
IGNORED = {".git", ".ekf", ".venv", "node_modules", "__pycache__"}
MAX_FILE = 2 * 1024 * 1024


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class StrictLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    explicit = set()
    for key_node, _ in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("Metadata keys must be strings")
        if key in explicit:
            raise ValueError(f"Duplicate YAML key: {key}")
        explicit.add(key)
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("Metadata keys must be strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_yaml(text):
    if len(text.encode()) > MAX_FILE:
        raise ValueError("Metadata exceeds the 2 MB limit")
    value = yaml.load(text, Loader=StrictLoader)
    # Accept ordinary YAML aliases while bounding expansion and rejecting cycles.
    budget = [100000]
    def inspect(item, ancestors=(), depth=0):
        budget[0] -= 1
        if budget[0] < 0 or depth > 40:
            raise ValueError("Metadata exceeds the supported complexity limit")
        if isinstance(item, (dict, list)):
            if id(item) in ancestors:
                raise ValueError("Recursive YAML aliases are not supported")
            for child in (item.values() if isinstance(item, dict) else item):
                inspect(child, (*ancestors, id(item)), depth + 1)
    inspect(value)
    return value


def parse_artifact(text, path=""):
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("An EKF artifact must start with YAML frontmatter (---)")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if end is None:
        raise ValueError("YAML frontmatter has no closing ---")
    meta = load_yaml("".join(lines[1:end]))
    if not isinstance(meta, dict):
        raise ValueError("YAML frontmatter must be a mapping")
    for key in ("ekf", "id", "type", "title"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"Required metadata '{key}' must be a non-empty string")
    if meta["ekf"] != "0.1":
        raise ValueError('This version supports ekf: "0.1"')
    relations = meta.get("relations", [])
    if not isinstance(relations, list):
        raise ValueError("relations must be a list")
    for relation in relations:
        if not isinstance(relation, dict) or not isinstance(relation.get("type"), str) or not relation["type"].strip():
            raise ValueError("Each relation needs a non-empty type")
        refs = [k for k in ("target", "resource") if k in relation]
        if len(refs) != 1 or not isinstance(relation[refs[0]], str) or not relation[refs[0]].strip():
            raise ValueError("Each relation needs exactly one non-empty target or resource")
    return {"id": meta["id"], "type": meta["type"], "title": meta["title"], "meta": meta,
            "body": "".join(lines[end + 1:]).lstrip("\n"), "path": path, "raw": text, "hash": digest(text)}


def serialize(meta, body):
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100) + "---\n\n" + body.rstrip() + "\n"


def safe_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise Problem("Invalid repository path")
    relative = Path(name)
    if relative.is_absolute() or any(p in ("..", ".git", ".ekf") or p.startswith(".") for p in relative.parts):
        raise Problem("Use a relative repository path without hidden directories")
    root = Path(root).resolve()
    result = root / relative
    for parent in [result, *result.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise Problem("Symbolic links are not accessible")
    if not result.resolve().is_relative_to(root):
        raise Problem("Path escapes the repository")
    return result


def files(root):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED and not d.startswith(".") and not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            p = Path(directory) / name
            if not name.startswith(".") and not p.is_symlink():
                yield p


def scan(root):
    sources = [(path.relative_to(root).as_posix(), path.stat().st_size,
                lambda path=path: path.read_text(encoding="utf-8")) for path in files(root)]
    def resource_exists(name):
        try:
            return safe_path(root, name).is_file()
        except Problem:
            return False
    return scan_sources(sources, resource_exists)


def scan_sources(sources, resource_exists):
    """Apply identical format and graph checks to working files and Git blobs."""
    artifacts, findings, identities = [], [], {}
    for rel, size, read in sources:
        if Path(rel).suffix.lower() != ".md":
            continue
        try:
            if size > MAX_FILE:
                findings.append({"severity": "error", "rule": "size", "path": rel, "message": "Markdown file exceeds 2 MB"})
                continue
            text = read()
            if not text.lstrip("\ufeff").startswith("---"):
                continue  # Ordinary Markdown documentation is not an artifact.
            artifact = parse_artifact(text, rel)
            artifacts.append(artifact)
            if artifact["id"] in identities:
                findings.append({"severity": "error", "rule": "duplicate-id", "id": artifact["id"], "path": rel,
                                 "message": f"Duplicate ID also used in {identities[artifact['id']]}"})
            identities[artifact["id"]] = rel
        except (ValueError, yaml.YAMLError, UnicodeError, RecursionError) as exc:
            findings.append({"severity": "error", "rule": "syntax", "path": rel, "message": str(exc)[:600]})
    edges = []
    for artifact in artifacts:
        for relation in artifact["meta"].get("relations", []):
            edges.append({"source": artifact["id"], **relation})
            if "target" in relation and relation["target"] not in identities:
                findings.append({"severity": "error", "rule": "unresolved-target", "id": artifact["id"],
                                 "path": artifact["path"], "message": f"Unknown target: {relation['target']}"})
            if "resource" in relation:
                if not resource_exists(relation["resource"]):
                    findings.append({"severity": "warning", "rule": "resource", "id": artifact["id"],
                                     "message": f"Resource unavailable: {relation['resource']}"})
    return {"artifacts": artifacts, "edges": edges, "findings": findings}


def analyze(graph, head=""):
    result = copy.deepcopy(graph["findings"])
    lookup = {a["id"]: a for a in graph["artifacts"]}
    coverage = []
    for a in graph["artifacts"]:
        relations = a["meta"].get("relations", [])
        if a["type"] == "requirement" and a["meta"].get("status") != "deprecated":
            ver = [lookup[r["target"]] for r in relations if r["type"] == "verified-by" and r.get("target") in lookup
                   and lookup[r["target"]]["type"] == "verification"]
            evid = [lookup[r["target"]] for v in ver for r in v["meta"].get("relations", [])
                    if r["type"] == "produces" and r.get("target") in lookup and lookup[r["target"]]["type"] == "evidence"]
            current = [e for e in evid if e["meta"].get("baseline") == head]
            state = "unplanned" if not ver else "planned" if not evid else "current" if current else "needs-review"
            coverage.append({"id": a["id"], "title": a["title"], "verification": [v["id"] for v in ver],
                             "evidence": [e["id"] for e in evid], "state": state,
                             "results": [{"id": e["id"], "result": e["meta"].get("result", "unspecified"),
                                          "baseline": e["meta"].get("baseline")} for e in evid]})
            if not ver:
                result.append({"severity": "warning", "rule": "verification-coverage", "id": a["id"], "message": "No verification definition linked"})
        if a["type"] == "assumption" and a["meta"].get("status", "draft") == "draft":
            result.append({"severity": "warning", "rule": "assumption", "id": a["id"], "message": "Unresolved assumption — confirm before relying on it"})
        if a["type"] == "hazard" and not any(e.get("target") == a["id"] and e["type"] == "mitigates" for e in graph["edges"]):
            result.append({"severity": "warning", "rule": "hazard", "id": a["id"], "message": "No mitigation relationship found"})
        if a["type"] == "verification" and not re.search(r"(?im)^#+\s+(acceptance criteria|pass criteria|expected result)", a["body"]):
            result.append({"severity": "warning", "rule": "pass-criteria", "id": a["id"], "message": "Consider documenting explicit pass criteria"})
        if a["type"] == "evidence" and a["meta"].get("baseline") != head:
            result.append({"severity": "warning", "rule": "evidence-baseline", "id": a["id"], "message": "Evidence baseline differs from HEAD or is unspecified; applicability needs review"})
    errors = [f for f in result if f["severity"] == "error"]
    return {"findings": result, "coverage": coverage,
            "syntactic": not any(f["rule"] in ("syntax", "size", "duplicate-id") for f in errors),
            "graph": not errors, "errors": len(errors), "warnings": len(result) - len(errors)}


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.state = self.root / ".ekf"
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self._revision_cache = {}
        self.git("rev-parse", "--show-toplevel")
        if Path(self.git("rev-parse", "--show-toplevel").strip()).resolve() != self.root:
            raise Problem("The EKF workspace must be its own Git repository")
        # Runtime state never enters source control, including in existing repos.
        exclude = Path(self.git("rev-parse", "--git-path", "info/exclude").strip())
        if not exclude.is_absolute():
            exclude = self.root / exclude
        exclude.parent.mkdir(parents=True, exist_ok=True)
        previous = exclude.read_text() if exclude.exists() else ""
        if "/.ekf/" not in previous.splitlines():
            exclude.write_text(previous + "\n/.ekf/\n")

    def git(self, *args, cwd=None, check=True):
        proc = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                               "-c", "user.name=EKF Studio", "-c", "user.email=studio@localhost", *args],
                              cwd=cwd or self.root, capture_output=True, text=True, encoding="utf-8", timeout=30)
        if proc.returncode and check:
            raise Problem(proc.stderr.strip() or "Git operation failed", 409)
        return proc.stdout

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def clean(self):
        return not self.git("status", "--porcelain", "--untracked-files=all").strip()

    def resolve_revision(self, ref):
        if not isinstance(ref, str) or not ref or len(ref) > 200:
            raise Problem("Choose a baseline or a full commit ID")
        if re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", ref):
            target = ref
        elif ref in self.git("tag", "--list").splitlines():
            target = "refs/tags/" + ref
        else:
            raise Problem("Baseline or commit not found", 404)
        return self.git("rev-parse", "--verify", target + "^{commit}").strip()

    def revision_tree(self, commit):
        entries = {}
        for record in self.git("ls-tree", "-r", "-z", "-l", commit).split("\0"):
            if not record:
                continue
            info, path = record.split("\t", 1)
            mode, kind, oid, size = info.split()
            parts = path.split("/")
            if (kind != "blob" or mode not in ("100644", "100755") or "\\" in path
                    or any(p.startswith(".") or p in IGNORED for p in parts)):
                continue
            entries[path] = {"oid": oid, "size": int(size)}
        return entries

    def revision_resource(self, path, ref):
        # Validate the historical path independently of today's working files.
        if (not isinstance(path, str) or not path or "\\" in path or "\0" in path
                or path.startswith("/") or any(p.startswith(".") or p in IGNORED or not p for p in path.split("/"))):
            raise Problem("Use a relative repository path without hidden directories")
        commit = self.resolve_revision(ref)
        entry = self.revision_tree(commit).get(path)
        if not entry:
            raise Problem("Resource not found in this revision", 404)
        if entry["size"] > MAX_FILE:
            raise Problem("Resource exceeds the 2 MB text viewer limit")
        try:
            content = self.git("cat-file", "blob", entry["oid"])
        except UnicodeError:
            raise Problem("This is a binary resource. Open it in its engineering tool.")
        if "\0" in content:
            raise Problem("This is a binary resource. Open it in its engineering tool.")
        return {"path": path, "content": content, "commit": commit}

    def resource(self, path, ref=""):
        if ref:
            return self.revision_resource(path, ref)
        target = safe_path(self.root, path)
        if not target.is_file():
            raise Problem("Resource not found", 404)
        if target.stat().st_size > MAX_FILE:
            raise Problem("Resource exceeds the 2 MB text viewer limit")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeError:
            raise Problem("This is a binary resource. Open it in its engineering tool.")
        if "\0" in content:
            raise Problem("This is a binary resource. Open it in its engineering tool.")
        return {"path": path, "content": content}

    def file_index(self, ref=""):
        if ref:
            return self.revision_tree(self.resolve_revision(ref))
        result = {}
        hash_type = hashlib.sha1 if len(self.head()) == 40 else hashlib.sha256
        for path in files(self.root):
            size = path.stat().st_size
            digest = hash_type(f"blob {size}\0".encode())
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            result[path.relative_to(self.root).as_posix()] = {"oid": digest.hexdigest(), "size": size}
        return result

    def compare_resource(self, before, after, path):
        with self.lock:
            versions, contents, notices = [], [], []
            for ref in (before, after):
                entry = self.file_index(ref).get(path)
                versions.append(entry)
                if entry is None:
                    contents.append("")
                    continue
                try:
                    content = self.resource(path, ref)["content"]
                    if "\0" in content:
                        raise Problem("Binary content has no text preview")
                    contents.append(content)
                except Problem as exc:
                    notices.append(str(exc))
                    contents.append("")
            if not any(versions):
                raise Problem("Resource not found in either version", 404)
            diff = [] if notices else list(difflib.unified_diff(contents[0].splitlines(), contents[1].splitlines(),
                        fromfile=path if versions[0] else "/dev/null", tofile=path if versions[1] else "/dev/null", lineterm=""))
            return {"path": path, "before": versions[0], "after": versions[1], "diff": "\n".join(diff[:4000]),
                    "truncated": len(diff) > 4000, "notice": " ".join(dict.fromkeys(notices))}

    def snapshot(self, ref=""):
        with self.lock:
            if ref:
                commit = self.resolve_revision(ref)
                if commit in self._revision_cache:
                    return copy.deepcopy(self._revision_cache[commit])
                entries = self.revision_tree(commit)
                sources = [(path, entry["size"], lambda oid=entry["oid"]: self.git("cat-file", "blob", oid))
                           for path, entry in entries.items()]
                graph = scan_sources(sources, lambda path: path in entries)
                try:
                    manifest = load_yaml(self.revision_resource("ekf.yaml", commit)["content"]) if "ekf.yaml" in entries else {}
                    if not isinstance(manifest, dict):
                        raise ValueError("Manifest must be a mapping")
                except (Problem, ValueError, yaml.YAMLError) as exc:
                    manifest = {}
                    graph["findings"].append({"severity": "warning", "rule": "manifest", "message": str(exc)})
                result = self.make_snapshot(graph, manifest, commit, "", False, True)
                if len(self._revision_cache) >= 3:
                    self._revision_cache.pop(next(iter(self._revision_cache)))
                self._revision_cache[commit] = result
                return copy.deepcopy(result)
            graph = scan(self.root)
            head = self.head()
            dirty = not self.clean()
            manifest_path = self.root / "ekf.yaml"
            try:
                manifest = load_yaml(manifest_path.read_text()) if manifest_path.exists() else {}
                if not isinstance(manifest, dict):
                    raise ValueError("Manifest must be a mapping")
            except (ValueError, yaml.YAMLError) as exc:
                manifest = {}
                graph["findings"].append({"severity": "warning", "rule": "manifest", "message": str(exc)})
            return self.make_snapshot(graph, manifest, head, self.git("branch", "--show-current").strip(), dirty)

    def make_snapshot(self, graph, manifest, head, branch, dirty, readonly=False):
        return {**graph, "validation": analyze(graph, head if not dirty else "uncommitted-working-tree"), "manifest": manifest,
                "head": head, "branch": branch, "dirty": dirty, "readonly": readonly,
                "types": list(dict.fromkeys(CORE_TYPES + [a["type"] for a in graph["artifacts"]])),
                "relation_types": list(dict.fromkeys(RELATIONS + [e["type"] for e in graph["edges"]])), "root": str(self.root)}

    def artifact(self, identity, ref=""):
        graph = self.snapshot(ref) if ref else scan(self.root)
        matches = [a for a in graph["artifacts"] if a["id"] == identity]
        if len(matches) != 1:
            raise Problem("Artifact not found or ID is ambiguous", 404)
        return matches[0]

    def impact(self, identity, depth=3, ref=""):
        graph = self.snapshot(ref) if ref else scan(self.root)
        if identity not in {a["id"] for a in graph["artifacts"]}:
            raise Problem("Artifact not found", 404)
        depth = max(1, min(int(depth), 10))
        seen, frontier = {identity}, {identity}
        distances = {identity: 0}
        for level in range(depth):
            adjacent = {e.get("target") for e in graph["edges"] if e["source"] in frontier and e.get("target")}
            adjacent |= {e["source"] for e in graph["edges"] if e.get("target") in frontier}
            frontier = adjacent - seen
            seen |= frontier
            distances.update({x: level + 1 for x in frontier})
        return {"root": identity, "depth": depth, "artifacts": [a for a in graph["artifacts"] if a["id"] in seen],
                "edges": [e for e in graph["edges"] if e["source"] in seen and (e.get("target") in seen or e.get("resource"))],
                "distances": distances, "note": "Potential impact through incoming and outgoing relationships; not a semantic conclusion."}

    def save(self, path, raw, expected_hash=None, actor="human:local"):
        return self.save_many([{"path": path, "raw": raw, "expected_hash": expected_hash}], actor)[0]

    def save_many(self, changes, actor="human:local"):
        """Validate the complete change before writing; commit or restore every file together."""
        with self.lock:
            if not self.clean():
                raise Problem("Repository has external changes. Commit or discard them with Git before saving in Studio.", 409)
            existing = scan(self.root)
            prepared, paths, identities = [], set(), {}
            for a in existing["artifacts"]:
                if a["id"] in identities:
                    raise Problem("Resolve duplicate artifact IDs before saving", 409)
                identities[a["id"]] = a["path"]
            for change in changes:
                target = safe_path(self.root, change["path"])
                path = target.relative_to(self.root).as_posix()
                if path in paths:
                    raise Problem("Each artifact can only be saved once per change")
                paths.add(path)
                if target.suffix.lower() != ".md":
                    raise Problem("Artifacts must be Markdown files")
                proposed = parse_artifact(change["raw"], path)
                if target.exists():
                    previous = parse_artifact(target.read_text(encoding="utf-8"), path)
                    if change.get("expected_hash") != previous["hash"]:
                        raise Problem(f"{previous['id']} changed. Reopen the editor before saving; no changes were saved.", 409)
                    if proposed["id"] != previous["id"]:
                        raise Problem("Preserve the artifact ID when editing an existing concept")
                elif change.get("expected_hash") is not None:
                    raise Problem("This artifact was moved or deleted. Reopen it before saving.", 409)
                if proposed["id"] in identities and identities[proposed["id"]] != path:
                    raise Problem("This ID is already used by another artifact", 409)
                identities[proposed["id"]] = path
                prepared.append((target, proposed, target.read_bytes() if target.exists() else None))
            for _, proposed, _ in prepared:
                if any(r.get("target") and r["target"] not in identities for r in proposed["meta"].get("relations", [])):
                    raise Problem("A relationship points to an unknown artifact")
            try:
                for target, proposed, _ in prepared:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(proposed["raw"], encoding="utf-8")
                if paths:
                    self.git("add", "--", *sorted(paths))
                    if self.git("diff", "--cached", "--name-only").strip():
                        label = prepared[0][1]["id"] if len(prepared) == 1 else f"links across {len(prepared)} artifacts"
                        self.git("commit", "-m", f"{actor}: update {label}")
            except Exception:
                for target, _, old in prepared:
                    if old is None:
                        target.unlink(missing_ok=True)
                    else:
                        target.write_bytes(old)
                if paths:
                    self.git("reset", "--", *sorted(paths), check=False)
                raise
            return [a for _, a, _ in prepared]

    def save_links(self, updates, artifact=None):
        """Relationship lists belong to their source, including links shown as incoming."""
        if not isinstance(updates, list) or (artifact is not None and not isinstance(artifact, dict)):
            raise Problem("Supply relationship updates and an optional artifact draft")
        with self.lock:
            changes, seen = [], set()
            sources = {}
            for source in scan(self.root)["artifacts"]:
                if source["id"] in sources:
                    raise Problem("Resolve duplicate artifact IDs before editing links", 409)
                sources[source["id"]] = source
            draft = parse_artifact(artifact["raw"], artifact["path"]) if artifact is not None else None
            if artifact is not None:
                changes.append(artifact)
            for update in updates:
                if not isinstance(update, dict) or not isinstance(update.get("relations"), list):
                    raise Problem("Each link update needs an ID, expected hash and relations list")
                identity = update["id"]
                if identity in seen or (draft and identity == draft["id"]):
                    raise Problem("Supply each source artifact once")
                seen.add(identity)
                a = sources.get(identity)
                if a is None:
                    raise Problem("A source artifact was moved or deleted. Reopen the editor before saving.", 409)
                meta = copy.deepcopy(a["meta"])
                meta["relations"] = update["relations"]
                # Keep engineering meaning byte-for-byte when only the frontmatter changes.
                lines = a["raw"].lstrip("\ufeff").splitlines(keepends=True)
                end = next(i for i in range(1, len(lines)) if lines[i].strip() in ("---", "..."))
                raw = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100) + "---\n" + "".join(lines[end + 1:])
                changes.append({"path": a["path"], "raw": raw, "expected_hash": update.get("expected_hash")})
            saved = self.save_many(changes)
            return {"id": draft["id"] if draft else None, "updated": [a["id"] for a in saved], "commit": self.head()}

    def review(self, identity, expected_hash):
        with self.lock:
            a = self.artifact(identity)
            meta = copy.deepcopy(a["meta"])
            reviews = meta.setdefault("verified", [])
            if not isinstance(reviews, list):
                raise Problem("verified metadata must be a list to append a review")
            reviews.append({"by": "human:local", "at": now()})
            return self.save(a["path"], serialize(meta, a["body"]), expected_hash)

    def history(self):
        raw = self.git("log", "-40", "--format=%H%x1f%aI%x1f%s")
        return [{"commit": p[0], "at": p[1], "message": p[2]} for line in raw.splitlines() if len(p := line.split("\x1f", 2)) == 3]

    def baselines(self):
        return [{"name": t, "commit": self.resolve_revision(t)} for t in self.git("tag", "--list").splitlines()]

    def compare(self, before, after="", identity=None):
        with self.lock:
            left, right = self.snapshot(before), self.snapshot(after)
            indexes = []
            for snapshot in (left, right):
                index = {a["id"]: a for a in snapshot["artifacts"]}
                if len(index) != len(snapshot["artifacts"]):
                    raise Problem("Resolve duplicate artifact IDs before comparing versions", 409)
                indexes.append(index)
            old, new = indexes
            describe = lambda s, label: {"label": label or "Current workspace", "commit": s["head"], "dirty": s["dirty"]}
            result = {"before": describe(left, before), "after": describe(right, after)}
            if identity is not None:
                a, b = old.get(identity), new.get(identity)
                if a is None and b is None:
                    raise Problem("Artifact not found in either version", 404)
                diff = list(difflib.unified_diff((a["raw"] if a else "").splitlines(), (b["raw"] if b else "").splitlines(),
                            fromfile=(a["path"] if a else "/dev/null"), tofile=(b["path"] if b else "/dev/null"), lineterm=""))
                return {**result, "artifact_before": a, "artifact_after": b, "diff": "\n".join(diff[:4000]), "truncated": len(diff) > 4000}
            summarize = lambda a: {k: a[k] for k in ("id", "title", "type", "path", "hash")} if a else None
            changes = []
            for aid in sorted(old.keys() | new.keys()):
                a, b = old.get(aid), new.get(aid)
                if a and b and a["raw"] == b["raw"] and a["path"] == b["path"]:
                    continue
                fields = [k for k in sorted(a["meta"].keys() | b["meta"].keys())
                          if k not in a["meta"] or k not in b["meta"] or a["meta"][k] != b["meta"][k]] if a and b else []
                changes.append({"id": aid, "status": "added" if not a else "removed" if not b else "modified",
                                "before": summarize(a), "after": summarize(b), "fields": fields,
                                "content_changed": bool(a and b and a["body"] != b["body"]),
                                "moved": bool(a and b and a["path"] != b["path"])})
            edge_key = lambda e: json.dumps(e, sort_keys=True, default=str)
            old_edges, new_edges = ({edge_key(e): e for e in s["edges"]} for s in (left, right))
            old_coverage, new_coverage = ({r["id"]: r for r in s["validation"]["coverage"]} for s in (left, right))
            coverage = [{"id": aid, "before": old_coverage.get(aid), "after": new_coverage.get(aid)}
                        for aid in sorted(old_coverage.keys() | new_coverage.keys()) if old_coverage.get(aid) != new_coverage.get(aid)]
            old_findings, new_findings = ({edge_key(f): f for f in s["validation"]["findings"]} for s in (left, right))
            old_files, new_files = self.file_index(left["head"] if before else ""), self.file_index(right["head"] if after else "")
            artifact_paths = {a["path"] for s in (left, right) for a in s["artifacts"]}
            resources = [{"path": path, "status": "added" if path not in old_files else "removed" if path not in new_files else "modified",
                          "before": old_files.get(path), "after": new_files.get(path)}
                         for path in sorted(old_files.keys() | new_files.keys())
                         if path not in artifact_paths and old_files.get(path) != new_files.get(path)]
            return {**result, "artifacts": changes,
                    "resources": resources,
                    "relations_added": [new_edges[k] for k in sorted(new_edges.keys() - old_edges.keys())],
                    "relations_removed": [old_edges[k] for k in sorted(old_edges.keys() - new_edges.keys())],
                    "coverage": coverage,
                    "findings_added": [new_findings[k] for k in sorted(new_findings.keys() - old_findings.keys())],
                    "findings_removed": [old_findings[k] for k in sorted(old_findings.keys() - new_findings.keys())],
                    "manifest_changed": left["manifest"] != right["manifest"]}

    def baseline(self, name):
        with self.lock:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,79}", name) or ".." in name:
                raise Problem("Use a Git tag name with letters, numbers, dots, slashes or dashes")
            if not self.clean():
                raise Problem("Commit external changes before creating a baseline", 409)
            report = analyze(scan(self.root), self.head())
            if not report["graph"]:
                raise Problem("Resolve conformance errors before creating a baseline")
            self.git("tag", "-a", name, "-m", f"Engineering baseline {name}")
            return {"name": name, "commit": self.head()}

    def proposals(self):
        folder = self.state / "proposals"
        folder.mkdir(exist_ok=True)
        return sorted([json.loads(p.read_text()) for p in folder.glob("*.json")], key=lambda p: p["created"], reverse=True)

    def propose(self, title, changes, actor="agent:external"):
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise Problem("A change proposal needs a title (up to 200 characters)")
        if not isinstance(changes, list) or not 1 <= len(changes) <= 50:
            raise Problem("Provide between 1 and 50 file changes")
        with self.lock:
            if not self.clean():
                raise Problem("Commit external repository changes before proposing a branch", 409)
            base = self.head()
            identity = uuid.uuid4().hex[:12]
            branch = "change/" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:45] + "-" + identity[:6]
            worktree = self.state / "worktrees" / identity
            worktree.parent.mkdir(exist_ok=True)
            original = scan(self.root)
            touched, touched_ids = [], []
            self.git("worktree", "add", "-b", branch, str(worktree), base)
            try:
                for change in changes:
                    if not isinstance(change, dict):
                        raise Problem("Each change must be an object")
                    path, content = change.get("path"), change.get("content")
                    dest = safe_path(worktree, path)
                    if path in touched:
                        raise Problem("A file can only occur once in a proposal")
                    if content is not None and (not isinstance(content, str) or len(content.encode()) > MAX_FILE):
                        raise Problem("File content must be text under 2 MB, or null for deletion")
                    old = next((a for a in original["artifacts"] if a["path"] == path), None)
                    if content is None:
                        if not dest.is_file():
                            raise Problem("Cannot delete a missing file")
                        dest.unlink()
                    else:
                        if path == "ekf.yaml":
                            manifest = load_yaml(content)
                            if not isinstance(manifest, dict) or manifest.get("ekf") != "0.1":
                                raise Problem('The manifest must be a YAML mapping with ekf: "0.1"')
                        if dest.suffix.lower() == ".md" and content.startswith("---"):
                            a = parse_artifact(content, path)
                            if old and old["id"] != a["id"]:
                                raise Problem("Preserve existing artifact IDs")
                            meta = a["meta"]
                            meta["generated"] = {"by": actor, "at": now()}
                            content = serialize(meta, a["body"])
                            touched_ids.append(a["id"])
                        elif old:
                            raise Problem("An existing EKF artifact must keep its metadata")
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(content, encoding="utf-8")
                    if old:
                        touched_ids.append(old["id"])
                    touched.append(path)
                report = analyze(scan(worktree), base)
                if not report["graph"]:
                    raise Problem("Proposal fails EKF validation: " + "; ".join(f["message"] for f in report["findings"] if f["severity"] == "error"))
                self.git("add", "--", *touched, cwd=worktree)
                if not self.git("diff", "--cached", "--name-only", cwd=worktree).strip():
                    raise Problem("Proposal has no changes")
                self.git("commit", "-m", f"{actor}: {title}", cwd=worktree)
                commit = self.git("rev-parse", "HEAD", cwd=worktree).strip()
                diff = self.git("diff", "--no-ext-diff", "--no-textconv", base, commit, "--")
                old_edges = {json.dumps(e, sort_keys=True, default=str) for e in original["edges"]}
                new_edges = {json.dumps(e, sort_keys=True, default=str) for e in scan(worktree)["edges"]}
                affected = set()
                for aid in set(touched_ids):
                    if any(a["id"] == aid for a in original["artifacts"]):
                        affected.update(a["id"] for a in self.impact(aid)["artifacts"])
                proposal = {"id": identity, "title": title, "created": now(), "actor": actor, "status": "pending",
                            "base": base, "commit": commit, "branch": branch, "files": touched, "diff": diff,
                            "affected": sorted(affected), "findings": report["findings"],
                            "relations_added": [json.loads(e) for e in sorted(new_edges - old_edges)],
                            "relations_removed": [json.loads(e) for e in sorted(old_edges - new_edges)]}
                folder = self.state / "proposals"
                folder.mkdir(exist_ok=True)
                (folder / f"{identity}.json").write_text(json.dumps(proposal, default=str, indent=2))
                return proposal
            finally:
                self.git("worktree", "remove", "--force", str(worktree), check=False)

    def decide(self, identity, decision):
        if decision not in ("approve", "reject"):
            raise Problem("Choose approve or reject")
        with self.lock:
            proposal = next((p for p in self.proposals() if p["id"] == identity), None)
            if not proposal or proposal["status"] != "pending":
                raise Problem("Pending proposal not found", 404)
            if decision == "approve":
                if not self.clean() or self.head() != proposal["base"]:
                    raise Problem("Repository changed since this proposal. Create an updated proposal against the current HEAD.", 409)
                if self.git("rev-parse", proposal["branch"]).strip() != proposal["commit"]:
                    raise Problem("Proposal branch changed after review", 409)
                self.git("merge", "--no-ff", "-m", f"human:local: approve {proposal['title']}\n\nReviewed-commit: {proposal['commit']}\nProposal-branch: {proposal['branch']}", proposal["commit"])
                proposal["merged_commit"] = self.head()
            proposal.update(status="approved" if decision == "approve" else "rejected", reviewed_by="human:local", reviewed_at=now())
            (self.state / "proposals" / f"{identity}.json").write_text(json.dumps(proposal, indent=2))
            return proposal

    def report(self, kind="traceability", ref=""):
        snap = self.snapshot(ref)
        title = {"traceability": "Traceability matrix", "verification": "Verification report", "requirements": "Requirements specification",
                 "architecture": "Architecture and interfaces", "safety": "Safety traceability", "review": "Design review package"}.get(kind)
        if not title:
            raise Problem("Unknown report type")
        rows = [f"# {title}", "", f"Generated: {now()}", f"Baseline: `{snap['head']}`", "",
                "Generated from EKF source files. Advisory findings are not certification evidence.", ""]
        if snap["dirty"]:
            rows += ["**Uncommitted working tree:** this report includes changes beyond the baseline commit above.", ""]
        if kind in ("traceability", "verification", "review"):
            rows += ["| Requirement | Verification | Evidence | Applicability |", "|---|---|---|---|"]
            for row in snap["validation"]["coverage"]:
                vals = [row["id"], ", ".join(row["verification"]) or "—", ", ".join(row["evidence"]) or "—", row["state"]]
                rows.append("| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in vals) + " |")
        selections = {"requirements": {"intent", "requirement", "constraint"}, "architecture": {"architecture", "component", "interface", "decision"},
                      "safety": {"hazard", "risk", "assumption"}, "review": set(snap["types"])}
        for a in snap["artifacts"]:
            if a["type"] in selections.get(kind, set()):
                rows += ["", f"## {a['id']} · {a['title']}", "", f"Source: `{a['path']}`", "", a["body"], "",
                         *[f"- {r['type']}: {r.get('target', r.get('resource'))}" for r in a["meta"].get("relations", [])]]
                if kind == "safety":
                    rows += [f"- Incoming: {e['source']} → {e['type']} → {a['id']}" for e in snap["edges"] if e.get("target") == a["id"]]
        rows += ["", "## Engineering findings", "", *[f"- {f['severity']}: {f.get('id', f.get('path', 'repository'))}: {f['message']}" for f in snap["validation"]["findings"]]]
        return "\n".join(rows) + "\n"
