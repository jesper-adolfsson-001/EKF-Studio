# EKF Studio

A local web workspace for **Engineering Knowledge Format v0.1**. Engineering artifacts are ordinary UTF-8 Markdown files with YAML frontmatter. Git records changes, reviewed proposals and baselines. The browser graph and reports are derived from those files.

The included example is a modular energy platform covering systems, hardware, software and mechanical engineering. All example content and measurements are synthetic and labelled accordingly. You can use any engineering discipline, additional artifact types, custom metadata and additional relationships.

## Run

Requirements: **Python 3.10+**, **Git**, and **PyYAML**. Linux with **Bubblewrap** is required for shell execution; all other features work without it. The browser UI has no build step, external fonts, CDN dependencies, Node runtime, or model subscription.

```bash
python3 -m pip install -r requirements.txt
python3 -m ekf serve
```

Open the **browser access link printed in the terminal** (at localhost:8840). The link authorizes this browser once; afterwards you can use http://localhost:8840 normally until the server restarts. On a fresh installation, **Projects** opens first. Create a project there; Studio creates its folder, files and separate Git repository. Subsequent starts reopen the last selected project.

## Local projects and GitHub

Select **Projects** in the sidebar to create, open and switch projects. **New local project** asks for a project name and folder name. Each project has its own artifacts, assets, Git history, baselines and draft proposals. **Remove from list** keeps the files on your computer. **Open local folder** registers an existing EKF project without moving it; when the server runs in WSL, enter its WSL path.

New projects are stored under `projects/` by default. Existing EKF repositories directly under that folder, such as `projects/Aster` and `projects/MyGarden`, appear automatically. Choose another container with `python3 -m ekf serve --projects /path/to/projects`. The former `workspace/` folder is optional; existing projects can be opened through **Open local folder** or `--repo`.

From the active project's card or **Settings**, select **GitHub setup**:

1. **Sign in to GitHub.** Studio uses the official GitHub CLI, downloading and checking the helper if needed. If an installed CLI is too old for Studio's sign-in flow, Studio downloads a compatible helper without changing that system installation. Copy the displayed code, select **Continue on GitHub**, authorize the connection and return to Studio.
2. **Publish as a new repository** creates a repository in your account or organization. Choose **Private** (the default) or **Public** before selecting **Create repository & upload**. Public makes the uploaded files and history readable by anyone.
3. **Choose existing repository** lists your repositories with pagination and a filter, or accepts a GitHub URL. An empty repository can receive your approved local main. A populated repository must share history with the local project; Studio refuses to combine unrelated projects.

Alternatively, **Projects → Open from GitHub** downloads an existing EKF repository into a new local project folder and opens it. It does not overwrite an existing folder. If a transfer fails, the message explains how to retry; partial local files are retained. An ongoing setup can be reopened through **GitHub setup** or **View setup progress** after refreshing Projects.

Publication uploads approved main and its history. Unapproved draft proposal branches remain local. GitHub setup does not yet submit proposals as pull requests, fetch remote main through the proposal buttons, or publish subsequent local approvals automatically. The current review and merge workflow remains local. Use the connected repository's GitHub link to manage collaborators.

The project catalog and GitHub account configuration live under the projects container's hidden `.ekf/` folder. Each project also has excluded `.ekf/` runtime state. Studio refuses to upload main history containing that runtime directory. Agent tokens belong to individual projects: an MCP connection can access only its project while that project is selected in Studio. Reconfigure the MCP token path when moving to another project.

Optional terminal setup for an empty project:

```bash
python3 -m ekf init projects/my-system --title "My system"
python3 -m ekf serve --repo projects/my-system --port 8841
```

To open an existing repository:

```bash
python3 -m ekf serve --repo /absolute/path/to/engineering-repository
```

The selected directory must contain `ekf.yaml` and be a Git repository root with at least one commit. The tool adds `/.ekf/` to its local Git exclude file for runtime state. It never imports engineering content into an authoritative database. Commit external edits using Git before saving or running tools in Studio. Refresh the browser view to pick up external changes. To create the included synthetic example explicitly, run `python3 -m ekf init projects/example --demo`, then open it through Projects.

## Use the workspace

- **Overview:** graph, artifact counts, planned verification coverage and engineering advisories. Choose a **Type** above the mini graph, then choose an artifact from the **Root** list. **All types** shows every artifact, including custom types. The type filter narrows the root choices; connected items of other types remain visible in the graph. The root stays on the left; the next columns show connected artifacts one, two and three links away, following both incoming and outgoing relationships. The preview shows up to three artifacts per distance, prioritizing those with more connections, and reports how many are displayed. **Explore graph** opens the full neighborhood. Type and root choices are remembered per workspace in the current browser tab. If a type is absent from a selected baseline, the selector falls back to All types. If the root is absent, the view uses the first intent or available artifact in the selected type.
- **Knowledge library:** search, filter, inspect, create and edit artifacts; import an existing Markdown artifact; edit custom metadata; record explicitly human reviews. Tables and cards show compact **In** and **Out** relation counts with clickable item IDs; expand **+N** to see more. Hover a link for its relationship type and item title. The item pane keeps incoming and outgoing links above its content tabs, so you can navigate between linked artifacts in either direction. Resource links open the text viewer. All navigation respects the selected baseline.
- **Editing links:** use **+** beside Incoming or Outgoing in the item pane, or the link buttons in the artifact editor. Choose a relationship (including custom types), search by ID/title, and filter by artifact type or discipline. Results show 20 items per page; selected items stay selected across searches, filters and pages. Choose **Add selected links**, review the explicit source → relationship → target changes, then save. Existing identical links are disabled. **Manage links → Existing links** supports searching, changing relationship types and removing links without deleting items. Resource links and custom link metadata are preserved; outgoing JSON remains under **Advanced** for specialist edits.
- **Saving links:** outgoing links are stored on the displayed item; incoming links are stored on the other source items. A save updates all affected Markdown files in one Git commit. From the artifact editor, **Apply to draft** keeps link changes pending until **Save artifact**, including incoming links to a new item. Cancel or Escape returns to the editor without applying that picker session. If a source was edited elsewhere, the whole save is rejected; reopen the editor to use its current contents. Link editing is unavailable while browsing a baseline.
- **Traceability:** generated graph and requirement → verification → evidence matrix. Hover or keyboard-focus an artifact to highlight incoming links in dashed blue and outgoing links in green; unrelated nodes and links fade. Both graphs have zoom buttons, a zoom percentage and Fit reset. Drag the background to pan, Ctrl/⌘-scroll to zoom at the pointer, or use `+`, `-` and `0` when the graph has keyboard focus. Select an artifact for its details or a bounded impact neighborhood.
- **Create a child from a graph:** right-click an item in either graph and choose **Create child…** (or focus it and press **Shift+F10**). Choose the child's artifact type and discipline, enter its title, and review the suggested Stable ID. Select the relationship type, including custom types. The arrow preview shows the link direction: **Child → parent** defaults to `derives-from`; choose **Parent → child** for relationships such as `verified-by`. **Create child** saves the child and its parent link in one commit and refreshes the graph. Cancel makes no changes. Baseline menus only allow inspection.
- **Artifact type, discipline and IDs:** the creation and editing forms have dropdowns for **Artifact type** and **Discipline**, including existing workspace values and **Add custom…** choices. New items receive a suggested type-based ID, such as `REQ-001`, `CMP-001` or `VER-001`; custom types use their uppercase name, such as `LOAD-CASE-001`. Suggestions advance the numbered series and skip occupied IDs and artifact paths. Changing type updates an automatic ID and any pending incoming links to that draft. You can enter a custom ID; it then stays unchanged when selecting another type. **Suggest ID** refreshes the workspace data and restores automatic suggestions without clearing the form. IDs are checked again on save, so competing creations cannot overwrite one another. A saved item's ID always stays fixed, even if its type or discipline changes.
- **Verification:** syntax and graph conformance, verification planning, evidence and advisory findings. Evidence and verification definitions remain distinct.
- **Generated views:** requirements, architecture/interfaces, traceability, verification, safety and design review Markdown reports, stamped with their source Git revision.
- **Agent workbench:** sandboxed shell execution, run history, output inspection and evidence proposals. Any installed CLI in the mounted runtime can be used; temporary Python or shell tools can be created in `/tmp` or `/output`.
- **Change proposals:** actual Git branches with file diffs, relationship additions/removals, affected artifacts and advisory findings. A human approves a merge or rejects the proposal. An explicit merge commit records human approval in Git. Proposals must incorporate the latest main and pass current checks before approval.
- **History & baselines:** real Git commit history and annotated Git tags. Browse saved versions read-only and compare baselines with each other or the current workspace. Existing baselines remain immutable.

Save creates a Git commit with a `human:local` message on a proposal branch. The first save from main creates that branch automatically; subsequent edits accumulate in the same proposal. Main changes only after approval. Agent proposals also use separate branches. Git hooks and commit signing are disabled for application-generated operations so opening a repository does not execute its hooks. Git's normal CLI remains available for branches, comparisons, remote pull requests and rollback.

## Work on a change proposal

1. Open an artifact on **main** and edit it. The editor explains that your first save creates a branch and proposal. You can also select the workspace name at the top left and choose **Start a new change** to name one before editing.
2. The top-left workspace control and a persistent banner show the active proposal. Artifact edits, new items, links, images/files, human review records and manifest edits accumulate there. Saves create commits on that branch; the approved files in the main project folder stay unchanged.
3. Choose **Review proposal** to inspect the accumulated file diff, relationship changes and validation findings. Rename the proposal there if needed. Use **Continue editing** to return to the library.
4. Select **Bring in latest main**. Studio merges main **into the proposal branch**, leaving main unchanged. If files conflict, select **Resolve** and keep the proposal version, keep the main version, or edit the complete resolved text. Binary conflicts offer a choice of versions. Resolving the last conflict finishes this update; approval still requires a separate check.
5. Expand **Last update from main** to inspect its file changes, then choose **Inspect updated branch** to review the combined requirements, links and evidence in the library. Make further edits if needed. Select **Check proposal** when ready; this checks your branch without silently merging more changes. If main has advanced, bring it in first.
6. **Approve & merge** merges **the proposal branch into main**. It becomes available only when the branch contains the current main, has saved changes, is clean, and passes checks against those exact main/proposal commits. Further edits or main commits invalidate those checks. Approval records a merge commit with both parent commits; the Git ref transaction verifies and locks both branch tips while main is updated.
7. **Reject** archives the proposal and retains its branch and working folder. Its changes do not enter main.

Open **Help** in the sidebar or **Workflow help** in a proposal for the [plain-language workflow guide](docs/workflow-help.md), including a requirements example, the two merge directions, conflicts and baselines.

The workspace control lets you switch between **main · Approved state** and open proposals. Switching preserves other drafts, and the active proposal survives a server restart. This is a single-user selection shared by the running Studio instance; stale browser drafts are rejected when their branch context has changed. Accounts, roles and concurrent multiuser sessions are not implemented.

Each proposal has an isolated Git worktree in `<project>/.ekf/worktrees/<proposal-id>/`. **Workspace settings → Working files** shows the active folder. Relative Markdown assets stay beside their Markdown files inside that worktree and arrive in the main folder on approval. Keep the project's hidden `.git` and `.ekf` directories when backing it up; pending proposal records and worktrees need both. After moving a project containing worktrees, use Git's `worktree repair` to repair their paths.

Checks cover EKF syntax, IDs and relationship targets, the manifest, and missing local `assets/` references in Markdown images/links. Engineering advisories remain visible and do not become proof of engineering correctness. A clean textual merge can still fail validation—for example, if two branches introduce the same stable ID. External uncommitted changes block saving or merging in the affected folder; Studio does not discard them.

**New proposal** remains available for explicit batches of file changes. Agent proposals are based on the currently selected working state and remain separate for review. Baselines capture the currently selected branch commit, including draft branches; they remain immutable after approval or rejection. Main is local: update it from your remote with Git before checking a proposal when remote collaboration is involved.

## Markdown, images and attachments

The item editor uses [MDXEditor](https://mdxeditor.dev/editor/docs/images) for rich text, headings, lists, links, tables and code blocks. Switch to **Markdown source** for direct editing. Content that the rich editor cannot parse opens in source mode with its original text preserved.

- Use **Add image** to upload images, or the image toolbar to insert an image URL. Images can also be pasted or dropped into rich text.
- Use the controls below an image to choose **Left**, **Center** or **Right**, edit its description, and set width/height in pixels. Click the image to reveal drag handles. Leave one dimension blank to preserve proportions; **Reset size** restores its natural size.
- Use **Attach file** for PDFs, documents, spreadsheets and other files. The viewer displays images and offers file links for download.
- Uploads stay in the draft until **Save artifact**. The item, its new files and any pending link changes are committed together. Cancel discards pending uploads. Each file can be up to **10 MB**, with **20 MB / 50 files** per save.

For `engineering/requirements/item.md`, uploads are stored in `engineering/requirements/assets/`. Generated filenames avoid collisions; Markdown uses relative references such as `![Diagram](assets/diagram-abc123.png)` and `[Specification](assets/specification-abc123.pdf)`. Sized/aligned images use ordinary HTML `<img>` tags with width/height attributes and `ekf-image-left`, `ekf-image-center` or `ekf-image-right` classes. Studio styles these classes in both editor and viewer; other Markdown tools may need equivalent CSS. Images are constrained to the available viewing width.

Existing relative image/file references resolve from the Markdown file's directory. Baseline views load repository attachments from the same Git revision as the item. External image URLs continue to point to their external source. Files in an `assets` folder are attachments, so attached Markdown documents are excluded from the artifact index. Removing a reference leaves previously committed files available to other items and old baselines; new uploads removed from the draft are not saved.

## Browse and compare baselines

Open **History & baselines** and select **Browse** beside a baseline, or choose a baseline using **Workspace version** in the top bar. The library, artifact details, graph, impact neighborhood, verification and downloaded reports all use that saved Git revision. Related resource links also open their historical contents. A persistent banner identifies the baseline and marks it **Read only**; editing, approvals and execution are unavailable in this view.

The selected baseline stays active across navigation and browser reloads in the same tab. Choose **Return to current workspace** to resume normal work. Browsing reads Git objects directly: it does not check out a branch, change the index, overwrite working files or require a clean working tree.

To compare versions:

1. Select **Compare** beside a baseline, or open the **Compare versions** tab.
2. Choose the **From** and **To** versions. Each side can be a baseline or the current workspace. **Swap** reverses the direction.
3. Select **Compare versions** to load or refresh the result.
4. Inspect added, modified, removed and moved artifacts; relationship additions/removals; verification coverage and evidence applicability; changes in engineering findings; and other file changes, including scripts and the manifest.
5. Select **View changes** for a Markdown/text difference. Artifact differences also offer both complete source versions. Binary resources and files exceeding the 2 MB text limit are listed without a text preview; difference previews are limited to 4,000 lines.

Artifacts are matched by stable ID, so a file move is distinct from removing and recreating an artifact. Duplicate IDs must be resolved before comparing versions. Current-workspace comparisons include uncommitted and untracked visible files and are explicitly marked when dirty; refresh the comparison after further edits. Hidden paths and symbolic links remain inaccessible.

Verification is evaluated against each version's own revision. Differences in applicability or deterministic findings are prompts for engineering review, not proof that a design or result is correct. Browsing and comparison do not introduce branch switching, restoration or merge conflict resolution.

## Try the executable engineering loop

1. Open **Agent workbench** in the example workspace.
2. Run the prefilled command:

   ```bash
   python3 tools/analyze_shutdown.py test-results/shutdown-042.csv
   ```

3. Inspect the synthetic result: **191 ms**, against a **250 ms** limit, giving **59 ms** margin.
4. Select `VER-SAFE-001` and choose **Propose evidence**.
5. Review the proposed artifact, verification link, execution log, captured result and input hashes, then approve the Git change if appropriate.

Generated evidence is deliberately `unassessed`: a zero exit code or a program printing `PASS` does not establish an engineering conclusion. An engineer evaluates the pass criteria, input validity and baseline applicability. Example measurements must not be mistaken for physical-system evidence.

Evidence records the analyzed commit, not the later commit which adds the evidence. Coverage calls evidence “current” only when its baseline equals the selected current HEAD; otherwise it explicitly requests an applicability review. This conservative first version does not automatically prove equivalence between an earlier design and a later evidence-only commit.

## Connect an AI agent

Studio supplies **MCP tools** and execution capabilities, not a bundled language model. Connect an existing MCP-compatible agent using the dependency-free stdio adapter. Run it from this application's directory, using the Python environment containing PyYAML:

```bash
python3 -m ekf.mcp \
  --url http://127.0.0.1:8840 \
  --token-file /absolute/path/to/workspace/.ekf/agent-token
```

The workbench has connection instructions. Supported tools:

| Tool | Capability |
| --- | --- |
| `search` | Find IDs, titles and content in a bounded result set |
| `read_artifact` | Read source and structured metadata by stable ID |
| `read_resource` | Inspect a repository text resource |
| `validate` | Run deterministic conformance and advisory checks |
| `impact` | Assemble context up to ten relationship steps away |
| `history` | Inspect commits and baselines |
| `propose_change` | Create a Git branch with proposed file changes |
| `run_tool` | Execute a sandboxed shell command or script |
| `run_status` | Read status, logs, input hashes and output metadata |
| `read_output` | Read an output text file |
| `propose_evidence` | Connect a completed execution to verification through a reviewed proposal |

The permission-restricted agent token can read, execute isolated tools and propose changes. It **cannot** directly save artifacts, create baselines, record human reviews or approve a merge through the API. Human browser access requires a separate launch key; merely visiting `/` does not issue an approval-capable session. Both credentials are stored privately under `.ekf/`, excluded from tool snapshots and agent resource reads. An external agent with independently granted host filesystem/shell access still has whatever permissions its own host application grants; this API does not revoke those.

Persistent agent-created tools can be proposed under `tools/`. Give important methods a `type: tool` artifact linked with `implemented-by` and `supports`. `propose_change` accepts arbitrary UTF-8 repository resources, so the same process covers test scripts, model configuration and source code.

### Example: connect OpenAI Codex

Run Codex and EKF Studio on the same machine/environment. The examples below use this checkout at `/home/jesper/web-apps/ekf-tool-001` and an existing `workspace/` repository. Replace that repository path with your selected project, such as `projects/MyGarden`, and adjust the Python executable and port as needed.

**1. Start EKF Studio and leave it running.**

```bash
cd /home/jesper/web-apps/ekf-tool-001
python3 -m ekf serve --repo workspace --port 8840
```

If Studio is already running on that port, use the existing instance. Starting Studio creates `workspace/.ekf/agent-token`. The MCP adapter reads that file; you do not need to copy the token into Codex configuration or provide an OpenAI API key to EKF Studio. Use the browser access link printed by Studio for reviewing and approving proposals.

**2. Register the adapter with Codex in another terminal.**

```bash
codex mcp add ekf-studio -- \
  /usr/bin/python3 \
  /home/jesper/web-apps/ekf-tool-001/ekf/mcp.py \
  --url http://127.0.0.1:8840 \
  --token-file /home/jesper/web-apps/ekf-tool-001/workspace/.ekf/agent-token
```

Everything after `--` is the local adapter command. Codex launches it and exchanges MCP messages over stdin/stdout; the adapter then calls Studio's authenticated local API. Absolute paths let it work when Codex is opened in a different project. Port `8840` serves the web app/API, **not a Streamable HTTP MCP endpoint**, so do not register it with `codex mcp add ekf-studio --url ...`.

Alternatively, add this equivalent configuration to `~/.codex/config.toml` instead of running the registration command. Keep any existing configuration; add or update only this server's table:

```toml
[mcp_servers.ekf-studio]
command = "/usr/bin/python3"
args = [
  "/home/jesper/web-apps/ekf-tool-001/ekf/mcp.py",
  "--url", "http://127.0.0.1:8840",
  "--token-file", "/home/jesper/web-apps/ekf-tool-001/workspace/.ekf/agent-token",
]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Codex also supports project-scoped `.codex/config.toml` for trusted projects. Local Codex clients using the same Codex host share MCP configuration. See the [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp) for configuration scope and supported options.

**3. Check the registration and open a fresh Codex session.**

```bash
codex mcp list
codex mcp get ekf-studio
codex
```

Inside the Codex terminal UI, enter `/mcp` to inspect active servers. `codex mcp list` shows configuration; a successful tool call confirms the live connection. Try:

> Use the ekf-studio MCP tools to validate the engineering repository. Summarize its conformance errors, verification gaps and unresolved assumptions. Do not modify anything.

Then try the example engineering workflow:

> Use the ekf-studio MCP tools to inspect REQ-SAFE-001 and its impact neighborhood. Read VER-SAFE-001 and the shutdown analyzer. Run `python3 tools/analyze_shutdown.py test-results/shutdown-042.csv` with `run_tool`, poll `run_status`, and explain the result and limitations. Propose evidence linked to VER-SAFE-001 for my review. Keep the synthetic-data qualification and do not edit repository files directly or approve the proposal.

Review the result in **Agent workbench** and **Change proposals** in the browser. Codex's MCP tool permissions still apply; an EKF change proposal needs a separate human approval in Studio before it is merged.

**Troubleshooting**

| Symptom | Check |
| --- | --- |
| Adapter exits with a missing-file error | Start Studio first, then check the absolute `mcp.py` and `agent-token` paths. For another workspace, use that workspace's token. |
| Connection refused | Keep the Studio server running and match its port. `127.0.0.1` refers to the machine/environment running the adapter. |
| Unauthorized / HTTP 401 | Point `--token-file` at `.ekf/agent-token` from the running workspace, not `human-token` or the browser access link. Restart the Codex session after changing credentials. |
| Server configured but absent from the session | Open a fresh Codex session and check `/mcp`. For project configuration, confirm the project is trusted. |
| Reads work but execution is unavailable | Check **Workspace settings → Recheck sandbox**. Bubblewrap availability affects `run_tool`, not graph reads or validation. |

To remove the registration later, run `codex mcp remove ekf-studio`. This removes the Codex connection, not your engineering repository.

## Execution policy

The runner mounts a snapshot of the clean repository at `/workspace` read-only, a per-run output directory at `/output` writable, and system binaries/libraries read-only. Hidden files, `.git`, `.ekf`, virtual environments and `node_modules` are excluded. There is no host home, credentials directory, inherited environment, network access or external-system write capability. Repository files visible in the snapshot are intentionally readable by the tool; do not put credentials in ordinary engineering resources.

Bubblewrap uses fresh namespaces, drops capabilities and starts a new session. Execution has a 15-second wall-clock deadline, 10-second CPU and 512 MB address-space limits per process, process/file-descriptor limits, output monitoring and capped displayed logs. The snapshot limit is 100 MB/10,000 files. Output monitoring stops runs exceeding 32 MB or 100 visible output files; individual files are limited to 16 MB. Monitoring is periodic, not an aggregate cgroup quota. This is a local engineering workbench, not a hardened hostile multi-tenant execution service.

If Bubblewrap or kernel namespace support is unavailable, commands are rejected. There is **no unsandboxed fallback**. Install Bubblewrap through your Linux distribution and use **Recheck sandbox** in settings. Package downloads, cloud APIs, hardware control and deployment need a separately designed permission policy and are unavailable in this version.

Run state lives in `.ekf/runs/`; accepted evidence and text outputs are copied into source-controlled files. Binary and text outputs larger than 2 MB remain in the local run directory and are not automatically embedded in proposals. Failed or interrupted runs never automatically become accepted evidence. Runtime state is local; keep it if unmerged review notes or pending output files matter.

## Engineering CI and testing

Read-only CI validation works even before a repository is initialized with Git:

```bash
python3 -m ekf validate --repo workspace
python3 -m ekf report --repo workspace --kind review > review-package.md
python3 -m unittest discover -s tests -v
```

Validation exits 1 for syntax, identity or unresolved-target errors, and 0 when those checks pass. Engineering warnings are advisory. Custom project rules and language-model semantic checks are not a certification mechanism.

The browser test creates an isolated temporary Git repository, starts a local server, uses a real browser and executes real Bubblewrap analyses:

```bash
npm ci
npx playwright install --with-deps chromium
npm run test:browser
```

`EKF_CHROMIUM` may select an existing Chromium executable; `EKF_PLAYWRIGHT` may select an existing Playwright package. `EKF_TEST_PORT` defaults to 8842. Screenshots include `/tmp/ekf-studio-overview.png`, `/tmp/ekf-studio-mobile.png` and `/tmp/ekf-proposal-review.png`. Set `EKF_BROWSER_SUITE=workflow` to run the focused proposal workflow checks.

See [the implementation/conformance map](docs/conformance.md) for coverage against the supplied EKF draft.

## First-version scope

This is a local, single-user application bound to loopback. It does not provide multi-user identity, a hosted service, remote PR integration, hardware access, model credentials, semantic certification, binary CAD editing or a universal engineering ontology. Arbitrary unknown types and metadata are preserved. Plain Markdown without frontmatter is treated as documentation; Markdown beginning with frontmatter is validated as an artifact. Metadata supports ordinary safe YAML, including aliases and merges, with bounded nesting/expansion. Path access excludes symlinks and hidden directories. Evidence applicability is conservative and requires engineering judgement.

## Implementation

- `ekf/core.py`: YAML artifacts, reproducible graph, conformance, impact, Git changes/baselines and reports.
- `ekf/workflow.py`: isolated proposal worktrees, accumulated changes, conflict resolution and merge checks tied to exact commits.
- `ekf/runner.py`: Bubblewrap execution and reproducibility records.
- `ekf/server.py`: loopback HTTP API, human session/agent capability separation and static assets.
- `ekf/mcp.py`: stdio MCP bridge.
- `web/`: browser interface and bundled Markdown editor/viewer, with sanitized Markdown rendering and restrictive security headers.
- `frontend/`: React island for MDXEditor, attachment staging and Markdown rendering. Run `npm ci` then `npm run build` after changing these sources; commit the generated `web/dist/` files with the source. Bundles are included, so running Studio still requires no Node installation or external CDN.
- `tests/`: format, repository, execution and full browser workflow verification.

References: [Bubblewrap's security model](https://github.com/containers/bubblewrap#sandbox-security), [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
