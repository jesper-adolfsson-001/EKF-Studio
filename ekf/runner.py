"""A fail-closed Linux tool runner. No host shell fallback."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
import uuid

from .core import Problem, files, now, safe_path

LIMITER = '''import os, resource, sys
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
resource.setrlimit(resource.RLIMIT_FSIZE, (16*1024*1024, 16*1024*1024))
resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.execv(sys.argv[1], sys.argv[1:])
'''


class Runner:
    def __init__(self, repo):
        self.repo = repo
        self.folder = repo.state / "runs"
        self.folder.mkdir(exist_ok=True)
        self.active = threading.Lock()
        self.available = False
        self.reason = "Checking sandbox"
        self.probe()
        for p in self.folder.glob("*/run.json"):
            run = json.loads(p.read_text())
            if run["status"] in ("queued", "running"):
                run.update(status="interrupted", finished=now(), stderr="The server stopped before this execution completed.")
                p.write_text(json.dumps(run, indent=2))

    def base_command(self):
        bwrap = shutil.which("bwrap")
        if not bwrap:
            raise Problem("Bubblewrap is not installed. Install bubblewrap to enable sandbox execution.", 503)
        command = [bwrap, "--unshare-all", "--unshare-user", "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
        for path in ("/usr", "/lib", "/lib64", "/bin"):
            if Path(path).exists():
                command += ["--ro-bind", path, path]
        command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--clearenv",
                    "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp", "--setenv", "LANG", "C.UTF-8"]
        return command

    def probe(self):
        try:
            result = subprocess.run(self.base_command() + ["--", "/usr/bin/python3", "-I", "-c", "print('ready')"],
                                    capture_output=True, text=True, timeout=5)
            self.available = result.returncode == 0 and result.stdout.strip() == "ready"
            self.reason = "Isolated Linux execution is ready" if self.available else result.stderr.strip()[:500]
        except (Problem, OSError, subprocess.TimeoutExpired) as exc:
            self.available, self.reason = False, str(exc)
        return {"available": self.available, "reason": self.reason, "network": False, "timeout_seconds": 15,
                "memory_mb": 512, "repository": "read-only snapshot", "concurrency": 1}

    def list(self):
        return sorted([json.loads(p.read_text()) for p in self.folder.glob("*/run.json")], key=lambda r: r["created"], reverse=True)

    def get(self, identity):
        if not isinstance(identity, str) or not identity.isalnum():
            raise Problem("Invalid run ID")
        path = self.folder / identity / "run.json"
        if not path.is_file():
            raise Problem("Tool run not found", 404)
        return json.loads(path.read_text())

    def save(self, run):
        target = self.folder / run["id"] / "run.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(run, indent=2))
        tmp.replace(target)

    def start(self, command, actor="human:local"):
        if not isinstance(command, str) or not command.strip() or len(command) > 16000:
            raise Problem("Provide a shell command or script under 16,000 characters")
        if not self.available:
            raise Problem("Sandbox unavailable: " + self.reason, 503)
        if not self.active.acquire(blocking=False):
            raise Problem("A tool is already running. Wait for it to finish.", 409)
        identity = uuid.uuid4().hex[:12]
        folder = self.folder / identity
        try:
            folder.mkdir()
            snapshot = folder / "snapshot"
            output = folder / "output"
            snapshot.mkdir()
            output.mkdir()
            hashes, total = {}, 0
            with self.repo.lock:
                if not self.repo.clean():
                    raise Problem("Commit repository changes before running tools so results have a reproducible revision.", 409)
                revision = self.repo.head()
                for source in files(self.repo.root):
                    size = source.stat().st_size
                    total += size
                    if total > 100 * 1024 * 1024 or len(hashes) >= 10000:
                        raise Problem("Execution snapshot exceeds 100 MB or 10,000 files")
                    relative = source.relative_to(self.repo.root)
                    dest = snapshot / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
                    hashes[relative.as_posix()] = hashlib.sha256(dest.read_bytes()).hexdigest()
            (folder / "limit.py").write_text(LIMITER)
            run = {"id": identity, "command": command, "actor": actor, "created": now(), "status": "queued",
                   "revision": revision, "input_hashes": hashes, "stdout": "", "stderr": "", "outputs": []}
            self.save(run)
            threading.Thread(target=self.execute, args=(run,), daemon=True).start()
            return run
        except Exception:
            self.active.release()
            raise

    def execute(self, run):
        folder = self.folder / run["id"]
        start = time.monotonic()
        proc = None
        try:
            run.update(status="running", started=now())
            self.save(run)
            command = self.base_command() + ["--ro-bind", str(folder / "snapshot"), "/workspace",
                       "--bind", str(folder / "output"), "/output", "--ro-bind", str(folder / "limit.py"), "/limit.py",
                       "--chdir", "/workspace", "--", "/usr/bin/python3", "-I", "/limit.py",
                       "/bin/bash", "--noprofile", "--norc", "-c", run["command"]]
            # Regular files bound output growth without accumulating unbounded pipe buffers.
            with (folder / "stdout").open("wb") as out, (folder / "stderr").open("wb") as err:
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
                while proc.poll() is None:
                    output_size, output_count = 0, 0
                    for generated in files(folder / "output"):
                        output_count += 1
                        output_size += generated.stat().st_size
                        if output_size > 32 * 1024 * 1024 or output_count > 100:
                            break
                    if time.monotonic() - start > 15 or out.tell() + err.tell() > 2 * 1024 * 1024 or output_size > 32 * 1024 * 1024 or output_count > 100:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=3)
                        run["status"] = "limited"
                        break
                    time.sleep(0.05)
                else:
                    run["status"] = "succeeded" if proc.returncode == 0 else "failed"
            run["exit_code"] = proc.returncode
            for key in ("stdout", "stderr"):
                with (folder / key).open("rb") as stream:
                    run[key] = stream.read(128 * 1024).decode("utf-8", errors="replace")
                if (folder / key).stat().st_size > 128 * 1024:
                    run[key] += "\n[output truncated]"
            run["outputs"] = []
            for p in files(folder / "output"):
                if len(run["outputs"]) >= 100:
                    break
                if p.is_file() and p.stat().st_size <= 16 * 1024 * 1024:
                    run["outputs"].append({"path": p.relative_to(folder / "output").as_posix(), "bytes": p.stat().st_size,
                                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        except Exception as exc:
            if proc and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            run.update(status="failed", stderr=str(exc))
        finally:
            run.update(finished=now(), duration_ms=round((time.monotonic() - start) * 1000))
            self.save(run)
            self.active.release()

    def output(self, identity, path):
        self.get(identity)
        target = safe_path(self.folder / identity / "output", path)
        if not target.is_file() or target.stat().st_size > 2 * 1024 * 1024:
            raise Problem("Output is unavailable or exceeds the 2 MB text viewer limit")
        return target.read_text(encoding="utf-8")
