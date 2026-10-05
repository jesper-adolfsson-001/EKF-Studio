## The idea: prepare a change before making it official

You can develop a set of requirements, update their links and add supporting evidence while the approved project stays available. When the proposed work is ready, review it together and accept it as one change.

You do not need to use Git commands for this workflow.

## A few useful words

| Word in Studio | What it means for your engineering work |
| --- | --- |
| **Main** | The project's current approved set of requirements and other artifacts. |
| **Branch** | A working version where you prepare a change. It starts from main and keeps your edits separate. |
| **Change proposal** | The review package for that branch: its purpose, saved changes, links and findings. |
| **Commit** | A saved checkpoint. Studio creates one when you save a change, so its history is recorded. |
| **Merge** | Combine changes from one branch into another. The direction matters. |
| **Conflict** | Two versions changed the same part in ways Studio cannot safely combine. You choose the intended result. |
| **Baseline** | A named snapshot you can revisit and compare later. It stays fixed while work continues. |

## Your everyday workflow

1. **Start a change.** Select the workspace name at the top left, then **Start a new change**. Give it a purpose, such as “Add pump protection requirements.” You can also edit an item on main: the first save automatically creates a branch and proposal.
2. **Develop your proposal.** Edit requirements, create items, connect links and add images or evidence. Saved edits accumulate in the active proposal. The top-left selector and banner show where you are working. Main stays unchanged.
3. **Bring in approved changes.** Open **Review proposal** and choose **Bring in latest main**. This merges main **into your branch**. It is a separate preparation step; it does not approve or publish your proposal. You can do it whenever useful, and repeat it if main changes again.
4. **Inspect the combined result.** Expand **Last update from main** to see what that update changed. Select **Inspect updated branch** to read the requirements in the library, follow their links and review verification or evidence. Make any further edits needed. **Accumulated changes** shows what your proposal would add to the current main.
5. **Check the proposal.** Return to **Review proposal** and select **Check proposal**. This runs automated checks on the version you have just inspected. It does not bring in more changes. If main has moved ahead, bring it in and inspect the result first.
6. **Make the decision.** When the result is satisfactory and checks pass, select **Approve & merge**. This merges **your branch into main**, making the reviewed changes part of the approved project. **Reject** archives the proposal without changing main; its branch is preserved.

You can stop after any save and return later. The workspace selector lets you switch between main and open proposals, and Studio remembers your selected proposal after a restart. Save unfinished form edits before switching.

## Example: protecting a garden pump

You start a proposal to limit the pump to ten minutes of continuous operation. You update the requirement and add a linked verification method.

Meanwhile, a separate proposal to stop the pump when a sensor fails is accepted into main. Your branch still has the earlier approved version until you choose **Bring in latest main**.

After that update, your branch contains both changes. You inspect how the time limit and sensor-failure response interact, adjust the verification method if needed, and run **Check proposal**. Only after your review do you choose **Approve & merge**.

This also helps one engineer working on several proposals: accepting one proposal changes main, and the others can then bring that change in before approval.

## When Studio asks you to resolve a conflict

Open **Resolve** beside each conflicting file. Compare the proposal version with the main version. Keep one complete version, or edit the resolved text to combine the intended changes. Keeping one version replaces the whole file, so check that you retain everything needed. For artifact text, preserve its metadata at the top, including its stable ID. Images and other binary files offer a choice of versions.

Resolving the last conflict finishes the update into your branch. Inspect the result and select **Check proposal** before approval. A merge without file conflicts still needs engineering review: two individually reasonable requirements can contradict each other.

## Why approval may be unavailable

- **Main has newer changes:** bring in latest main, inspect your branch and check again.
- **You edited after checking:** save your work and run **Check proposal** again.
- **Conflicts or validation errors remain:** resolve them first. Checks include artifact structure, unique IDs, relationship targets and missing local attachments.
- **There are no proposed changes:** there is nothing to approve yet.
- **Files were edited outside Studio:** finish and commit those edits with Git before continuing in Studio.

Passing automated checks does not prove that a requirement is correct, complete or adequately verified. Review the engineering meaning, affected links, verification and evidence before approval. Checks are tied to the exact versions of main and your proposal; a later change requires fresh checks.

## What main means in this version

Main is the approved branch in this local project. **Bring in latest main** reads that branch; it does not fetch changes from a remote server. If you use a remote repository, update local main with Git first.

## Projects and GitHub setup

Choose **Projects** in the sidebar to create a local project, open an existing folder, or switch projects. Studio creates the initial files and Git history for new projects. Each project keeps its own items, attachments, proposals and baselines. Removing a project from the list keeps its files on your computer. Save unfinished form edits before switching.

To share the approved project, open **GitHub setup** on its project card or in Settings. Sign in using the displayed code and **Continue on GitHub**. Then choose an existing repository or publish a new one. New repositories default to **Private**; choose **Public** only when anyone should be able to read the approved files and their history. Empty existing repositories can receive your local main. Populated repositories must share its history; use **Open from GitHub** for a separate project instead.

**Open from GitHub** downloads an existing EKF project into a new local folder. Publication uploads approved main; unfinished proposals stay local. GitHub setup currently establishes the repository connection and initial upload. Shared pull requests, remote updates through the proposal buttons and automatic uploads after local approval are future work. Repository access can be managed through the provided GitHub link.

Studio currently has one shared active proposal selection and a local human reviewer. Separate user accounts, permissions and simultaneous user sessions are future work. The branch workflow is already useful for keeping several proposals separate.

Baselines are a different tool: they record a fixed version for reference. For an approved baseline, switch to main before creating it. You can also baseline a draft, but doing so does not approve it.
