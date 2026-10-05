import argparse
import json
from pathlib import Path
import sys
from .core import Repository, Problem, analyze, scan
from .seed import init_repo


def main():
    parser = argparse.ArgumentParser(description="EKF Studio — file-native engineering knowledge")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Initialize a Git-backed EKF repository")
    init.add_argument("path")
    init.add_argument("--demo", action="store_true")
    init.add_argument("--title", default="My engineering workspace")
    for name in ("serve", "validate", "report"):
        p = sub.add_parser(name)
        p.add_argument("--repo", default=None if name=='serve' else 'workspace')
        if name == "serve":
            p.add_argument("--port", type=int, default=8840)
            p.add_argument("--projects", help="Folder for local projects (defaults to projects, or the opened repository's parent)")
        if name == "report":
            p.add_argument("--kind", default="traceability", choices=["traceability", "verification", "requirements", "architecture", "safety", "review"])
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_repo(args.path, args.demo, args.title)
            print(f"Created EKF repository: {Path(args.path).resolve()}")
        elif args.command == "validate":
            root = Path(args.repo).resolve()
            if not root.is_dir():
                raise Problem("Repository directory does not exist")
            # CI validation does not require Git or write any files.
            result = analyze(scan(root))
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["graph"] else 1
        elif args.command == "report":
            print(Repository(args.repo).report(args.kind))
        else:
            from .server import serve
            root = Path(args.repo) if args.repo else None
            if root and not root.exists():
                raise Problem('Project folder not found. Start without --repo to create it from the project manager.')
            serve(Repository(root) if root else None, args.port, args.projects)
    except (Problem, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
