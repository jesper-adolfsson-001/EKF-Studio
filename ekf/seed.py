"""A clearly labelled, cross-discipline example repository."""
from pathlib import Path
import subprocess
import yaml
from .core import serialize, now, Problem


ANALYZER = '''import csv, json, sys
from pathlib import Path
path = Path(sys.argv[1] if len(sys.argv) > 1 else "test-results/shutdown-042.csv")
rows = list(csv.DictReader(path.open()))
assert rows, "No measurement samples"
start = next(float(r["time_s"]) for r in rows if int(r["shutdown"]) == 1)
end = next(float(r["time_s"]) for r in rows if float(r["time_s"]) >= start and float(r["current_a"]) < 1)
elapsed = round((end - start) * 1000, 3)
result = {"result": "PASS" if elapsed <= 250 else "FAIL", "elapsed_ms": elapsed,
          "limit_ms": 250, "margin_ms": round(250 - elapsed, 3), "data": str(path),
          "note": "Synthetic demonstration data; not physical test evidence."}
print(json.dumps(result, indent=2))
if Path("/output").is_dir():
    Path("/output/shutdown-result.json").write_text(json.dumps(result, indent=2))
'''


def init_repo(root, demo=True, title="My engineering workspace"):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise Problem("Initialize into an empty directory to preserve existing files")
    (root / ".gitignore").write_text(".ekf/\n__pycache__/\n*.pyc\n")
    manifest = {"ekf": "0.1", "system": {"id": "ASTER" if demo else "SYSTEM", "title": "Aster energy platform" if demo else title},
                "defaults": {"artifact_format": "markdown", "relation_model": "ekf"},
                "studio": {"demo": demo, "description": "A connected engineering workspace for a modular energy storage system." if demo else "Engineering intent, design, verification and evidence."}}
    (root / "ekf.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    (root / "index.md").write_text("# Engineering workspace\n\n" + ("This repository contains synthetic example engineering content. Do not use it as real system evidence.\n" if demo else "Engineering knowledge is stored in Markdown with YAML frontmatter.\n"))
    if demo:
        artifacts = [
            ("INT-SYS-001", "intent", "Safe energy, wherever it is needed", "Systems", "stable", [],
             "## Intent\n\nProvide modular, dependable energy storage for remote infrastructure. The platform must be maintainable and fail safely.\n\n## Success measures\n\n- Safe isolation on request\n- Predictable thermal performance\n- Traceable verification across all disciplines"),
            ("REQ-SAFE-001", "requirement", "Emergency energy isolation", "Systems", "stable", [("derives-from", "INT-SYS-001"), ("allocated-to", "CMP-HW-001"), ("verified-by", "VER-SAFE-001"), ("mitigates", "HAZ-001"), ("depends-on", "ASM-001")],
             "## Statement\n\nThe system shall disconnect its DC output when the emergency shutdown input is asserted.\n\n## Acceptance criteria\n\nOutput current shall fall below **1 A within 250 ms** of input assertion.\n\n## Rationale\n\nPrevent continued energy delivery following an external emergency shutdown request."),
            ("REQ-THERM-002", "requirement", "Operating temperature envelope", "Mechanical", "stable", [("derives-from", "INT-SYS-001"), ("allocated-to", "CMP-MECH-001"), ("verified-by", "VER-THERM-002")],
             "## Statement\n\nThe thermal assembly shall maintain cell temperatures between 5 °C and 45 °C under the defined continuous load.\n\n## Acceptance criteria\n\nNo monitored cell may exceed 45 °C during a two-hour, 80 A discharge at 30 °C ambient."),
            ("REQ-COM-003", "requirement", "Health telemetry freshness", "Software", "draft", [("derives-from", "INT-SYS-001"), ("allocated-to", "CMP-SW-001"), ("verified-by", "VER-COM-003"), ("interfaces-with", "IF-CAN-001")],
             "## Statement\n\nThe controller shall publish state of charge, temperature and fault status every 100 ms.\n\n## Acceptance criteria\n\nThe interval between health frames shall not exceed 120 ms under maximum specified bus load."),
            ("REQ-MECH-004", "requirement", "Serviceable module enclosure", "Mechanical", "draft", [("derives-from", "INT-SYS-001"), ("allocated-to", "CMP-MECH-001")],
             "## Statement\n\nA trained technician shall be able to replace an isolated module using standard service tools.\n\n## Acceptance criteria\n\nModule removal and replacement within 20 minutes, excluding electrical isolation.\n\n## Open questions\n\nThe final maintenance procedure and representative technician population need agreement."),
            ("REQ-HW-005", "requirement", "Isolation path fault detection", "Hardware", "draft", [("derives-from", "REQ-SAFE-001"), ("allocated-to", "CMP-HW-001"), ("verified-by", "VER-HW-005")],
             "## Statement\n\nThe contactor assembly shall detect a welded contactor before enabling the next operating cycle.\n\n## Acceptance criteria\n\nFault injection shall demonstrate that a welded contactor prevents energization and raises a diagnostic."),
            ("ARCH-SYS-001", "architecture", "Modular energy architecture", "Systems", "stable", [("refines", "INT-SYS-001"), ("allocated-to", "CMP-HW-001"), ("allocated-to", "CMP-SW-001"), ("allocated-to", "CMP-MECH-001")],
             "## Structure\n\nThe platform combines a control unit, an isolation assembly and a replaceable thermal enclosure.\n\n## Boundaries\n\nThe external energy supervisor communicates over CAN. The emergency shutdown input is electrically independent of the software control path."),
            ("CMP-HW-001", "component", "Power isolation assembly", "Hardware", "stable", [("interfaces-with", "IF-CAN-001")],
             "## Responsibility\n\nTwo series contactors provide independent interruption paths. Auxiliary feedback supports weld detection.\n\n## Interfaces\n\nShutdown input, coil supply, contactor feedback and DC power terminals."),
            ("CMP-SW-001", "component", "Supervisory controller", "Software", "draft", [("interfaces-with", "IF-CAN-001"), ("implemented-by", "@src/controller.py")],
             "## Responsibility\n\nCoordinate the operating state, report health and prevent unsafe transitions. The physical shutdown circuit remains independent."),
            ("CMP-MECH-001", "component", "Thermal module enclosure", "Mechanical", "draft", [("depends-on", "ASM-THERM-002")],
             "## Responsibility\n\nProvide the module load path, coolant interface and service access.\n\n## Design constraints\n\nMaintain isolation clearances and protect coolant seals during replacement."),
            ("IF-CAN-001", "interface", "Supervisor CAN interface", "Systems", "stable", [],
             "## Participants\n\n- Platform supervisory controller\n- External energy supervisor\n\n## Contract\n\nClassical CAN at 500 kbit/s. Health frame identifier 0x180. Signal encoding and timeout behavior are controlled by the interface owner."),
            ("DEC-001", "decision", "Independent shutdown path", "Systems", "stable", [("derives-from", "REQ-SAFE-001"), ("allocated-to", "CMP-HW-001")],
             "## Context\n\nSoftware and communication failures must not prevent isolation.\n\n## Decision\n\nUse a hardwired shutdown path independent of the supervisory application.\n\n## Alternatives considered\n\nSoftware-only shutdown was rejected because it shares a common failure path.\n\n## Consequences\n\nAdditional wiring and hardware verification are required."),
            ("CON-001", "constraint", "Module mass budget", "Mechanical", "draft", [("allocated-to", "CMP-MECH-001")],
             "## Constraint\n\nThe replaceable module mass shall not exceed 24 kg.\n\n## Rationale\n\nSupports the planned two-person service procedure."),
            ("ASM-001", "assumption", "External shutdown latency", "Systems", "draft", [],
             "## Assumption\n\nThe external supervisor is assumed to assert the shutdown input within 50 ms of detecting the hazardous condition.\n\n## Resolution\n\nObtain measured latency and written agreement from the external supervisor owner. This is not a verified fact."),
            ("ASM-THERM-002", "assumption", "Available coolant inlet temperature", "Mechanical", "draft", [],
             "## Assumption\n\nThe site cooling loop is assumed to provide coolant at or below 25 °C.\n\n## Resolution\n\nConfirm against the site interface agreement and summer operating data."),
            ("HAZ-001", "hazard", "Unintended energy delivery", "Systems", "draft", [],
             "## Hazard\n\nContinued energy delivery after an emergency request could expose service personnel to hazardous conditions.\n\n## Control strategy\n\nIndependent isolation and controlled service access. This example is not a completed safety assessment."),
            ("RISK-001", "risk", "Cooling interface remains unconfirmed", "Mechanical", "draft", [("depends-on", "ASM-THERM-002")],
             "## Risk\n\nA warmer site coolant supply may reduce available continuous power.\n\n## Next action\n\nResolve the cooling interface before freezing the thermal design."),
            ("VER-SAFE-001", "verification", "Shutdown timing measurement", "Systems", "stable", [("produces", "EVID-SAFE-042"), ("executed-using", "@tools/analyze_shutdown.py")],
             "## Objective\n\nMeasure current decay after shutdown assertion.\n\n## Method\n\nCapture the shutdown input and output current using synchronized acquisition. Run the timing analyzer on the CSV trace.\n\n## Pass criteria\n\nOutput current falls below 1 A within 250 ms.\n\n## Preconditions\n\nRated operating current, calibrated acquisition and controlled test setup."),
            ("VER-THERM-002", "verification", "Continuous load thermal soak", "Mechanical", "draft", [],
             "## Objective\n\nDemonstrate the operating temperature envelope.\n\n## Method\n\nDischarge at 80 A for two hours at 30 °C ambient. Log all cell temperatures.\n\n## Pass criteria\n\nNo monitored cell exceeds 45 °C."),
            ("VER-COM-003", "verification", "Telemetry interval analysis", "Software", "draft", [],
             "## Objective\n\nMeasure health-frame timing at maximum bus load.\n\n## Pass criteria\n\nEvery interval is at most 120 ms."),
            ("VER-HW-005", "verification", "Contactor weld fault injection", "Hardware", "draft", [],
             "## Objective\n\nInject a welded-contactor condition.\n\n## Pass criteria\n\nEnergization is inhibited and the correct fault is reported."),
            ("EVID-SAFE-042", "evidence", "Shutdown run 042 · example", "Systems", "draft", [("produces", "@test-results/shutdown-042.csv")],
             "## Result\n\n**Synthetic demonstration only.** The example trace reaches less than 1 A after 191 ms, leaving 59 ms against the 250 ms limit.\n\n## Applicability\n\nNo physical system baseline is claimed. Re-run against controlled measurements before making an engineering conclusion."),
            ("TOOL-001", "tool", "Shutdown timing analyzer", "Systems", "stable", [("supports", "VER-SAFE-001"), ("implemented-by", "@tools/analyze_shutdown.py")],
             "## Method\n\nRead synchronized CSV samples, find shutdown assertion and the first subsequent current value below 1 A, and calculate elapsed time.\n\n## Limitations\n\nThe simple example uses the first crossing; it does not evaluate contact bounce, sampling uncertainty or sustained isolation."),
        ]
        for aid, kind, name, discipline, status, links, body in artifacts:
            meta = {"ekf": "0.1", "id": aid, "type": kind, "title": name, "status": status, "discipline": discipline,
                    "generated": {"by": "human:example-author", "at": now()}}
            if links:
                meta["relations"] = [{"type": rel, "resource" if target.startswith("@") else "target": target.lstrip("@")} for rel, target in links]
            if kind == "evidence":
                meta.update(result="example-pass", execution={"tool": "tools/analyze_shutdown.py", "command": "python3 tools/analyze_shutdown.py test-results/shutdown-042.csv"})
            path = root / "engineering" / kind / (aid.lower() + ".md")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialize(meta, body), encoding="utf-8")
        for path, text in {"tools/analyze_shutdown.py": ANALYZER,
                           "test-results/shutdown-042.csv": "time_s,shutdown,current_a\n10.500,0,80\n10.522,1,80\n10.600,1,42\n10.700,1,3\n10.713,1,0.8\n10.750,1,0.1\n",
                           "src/controller.py": '"""Illustrative implementation resource; not production firmware."""\nHEALTH_INTERVAL_MS = 100\n'}.items():
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    def git(*args):
        subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "user.name=EKF Studio", "-c", "user.email=studio@localhost", *args], cwd=root, check=True, capture_output=True)
    git("init", "-b", "main")
    git("add", ".")
    git("commit", "-m", "Initialize example EKF engineering repository" if demo else "Initialize EKF engineering repository")
    git("tag", "-a", "example-v0.1" if demo else "initial", "-m", "Initial engineering baseline")
