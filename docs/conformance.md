# EKF v0.1 implementation and verification map

Source: `Engineering Knowledge Format (EKF) v0.1 Draft.md` in this project (33 sections). This maps the actual draft to the first-version implementation; EKF does not mandate a specific UI, AI model or runtime.

| Draft sections | Requirement or principle | Implementation and evidence |
| --- | --- | --- |
| 1, 2.1, 2.6, 7, 11, 31–33 | Generic engineering knowledge, extensible types, flexible bodies | All twelve core types plus example `tool`; arbitrary custom types, metadata and Markdown bodies. Browser test creates a manufacturing requirement with nested custom metadata. Format test round-trips unknown types. |
| 2.2, 3–6, 29, 32 | UTF-8 Markdown/YAML source, required fields, location-independent identity, reproducible graph | `parse_artifact`, `scan`, `serialize`; no engineering database. Minimal example, missing fields, safe YAML, duplicate IDs, file-move and scan-regeneration tests. `ekf.yaml` manifest and plain `index.md`. |
| 2.3, 16–18 | Git history, changes, review, baselines, lifecycle | UI edits accumulate as commits on isolated `change/*` branches, created automatically on the first save from main. Proposals can be resumed, updated from main, resolved and checked. Human approval requires passing checks tied to both current branch tips; a Git ref transaction guards the merge. Baselines are annotated tags with read-only historical browsing and stable-ID comparisons of artifacts, relationships, coverage, findings and resources. Historical Git objects are read without checkout. Tests cover isolation, restart recovery, stale checks, text/binary conflicts, rejection and Git races. Native Git handles remote PRs and rollback. |
| 2.4, 8–10 | Typed graph relationships, unknown relations and repository resources | Target/resource relationship parsing, reverse links and generated graph/matrix; unknown relationship vocabulary retained. Artifact ID and resource references remain distinct. Resource access is confined to the repository. |
| 2.5, 21, 28 | Agent context, proposals, uncertainty and tool use | Eleven MCP tools expose search, source reads, bounded neighborhoods, validation, Git history, execution and proposed changes. MCP instructions require preserving IDs and explicit assumptions. Proposal metadata records actor and time. Live MCP handshake/search and role-denial tests. Agent semantic judgement is supplied by the user's connected agent. |
| 2.7, 10, 13, 25 | Connect implementation, verification and evidence; reproducibility | Requirement → verification → evidence; links to Python implementation and measurement CSV. Captured evidence includes analyzed Git commit, command, input/output hashes and execution log. Full browser test runs the analyzer, proposes evidence, checks the verification link and merges it. No automatic pass/fail inference. |
| 12 | Assumptions remain explicit | Assumption artifacts and `depends-on` links, unresolved-assumption advisories and impact context. Examples explicitly label uncertainty instead of asserting facts. |
| 14–15 | Origin and distinguishable human/machine reviews | Preserved `sources`, `generated` and `verified` metadata. Proposals stamp `generated.by` as agent or human; human review endpoint is forbidden to the agent token. Unit test verifies attribution. |
| 19 | Derived engineering views | Six Markdown exports from current source or the selected baseline revision. Matrix derived from graph; no parallel manually maintained report database. Unit tests check every report kind and browser test inspects the downloaded matrix. |
| 20, 30 | Deterministic CI; syntax and graph conformance separately | Safe YAML, required metadata, unique IDs, relationship shape and internal target resolution. CLI has nonzero error exit. Unknown types do not fail validation. Advisory rules cover verification gaps, pass-criteria headings, unresolved assumptions, hazard mitigation and baseline mismatch. Tests include invalid YAML and unresolved targets. |
| 2.8, 22–24, 26 | Generic controlled execution and creation of reusable tools | Bubblewrap runs Bash, Python and mounted installed CLIs; temporary scripts can be written in `/tmp` or `/output`. Persistent scripts are version-controlled through file proposals, optionally represented by `type: tool`. Browser test proposes and merges a reusable calculator and executes an existing analysis script. |
| 27 | Distinguish capabilities and preserve human approval | Agent bearer token permits read/execute/propose, while cookie-authenticated human endpoints approve/directly edit/review/tag. No network, host home, inherited secrets, hardware or external-system writes in the runner. API/origin/path tests plus live filesystem, environment and network isolation assertions. |

## Deliberate first-version boundaries

- UI reviews use `human:local`, not authenticated multi-user identities. The active proposal selection is shared by this local Studio instance; concurrent multiuser sessions are deferred.
- Source-controlled files and Git commits/branches are authoritative. Approved changes have an explicit human approval merge commit. Local `.ekf` proposal display metadata and run outputs support workflow but are not a substitute for accepted evidence files.
- Proposed changes show file diffs (including additions/removals and implementation changes), relationship deltas, potentially affected artifacts, verification advisories and unresolved assumptions. Remote pull requests are outside this local version; the actual branches can be used with ordinary Git hosting.
- Current-evidence applicability checks exact commit identity. Prior evidence is visibly flagged for review, including after an evidence-only commit. Automatic dependency-aware applicability proofs are not implemented.
- Semantic AI findings are not fabricated by deterministic checks. Connect an agent to perform advisory semantic review.
- Normal YAML metadata is supported with resource bounds. Recursive YAML aliases, unsafe constructors and duplicate explicit keys are rejected. Files larger than 2 MB are outside the artifact editor/validator limit.
- Script output is captured and reproducible, but engineering assessment is always distinct from process exit status. Binary/large outputs are retained locally instead of silently claimed as committed evidence.

## Acceptance commands

```bash
python3 -m unittest discover -s tests -v
python3 -m ekf validate --repo workspace
npm run test:browser
```

The browser test uses a temporary repository so verification does not alter the user's example workspace. It exercises ten pages, creation/editing/custom metadata, human review, search and impact, proposal isolation/merge, separate updates from main and checks, incoming change previews, workflow help, real sandbox analysis, linked evidence, report download, baseline creation and read-only browsing, historical exports, baseline/current comparisons, resource differences, dirty-file handling, authorization boundaries, a real MCP handshake and mobile navigation.
