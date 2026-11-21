# Contributing

Thanks for helping out! All changes go through a branch and a pull request that at least one teammate reviews before it reaches `main`. Nobody pushes directly to `main`.

## Contents

- [Reading this guide in VS Code](#reading-this-guide-in-vs-code)
- [Recommended VS Code extensions](#recommended-vs-code-extensions)
- [Workflow](#workflow)
- [Keeping secrets out of Git](#keeping-secrets-out-of-git)

## Reading this guide in VS Code

Markdown files are easier to read as a rendered page than as plain text. VS Code can show a preview without any extension:

- Open the file and click the preview icon (a magnifying glass over a page) in the top-right corner of the editor.
- Or press `Ctrl+Shift+V` (`Cmd+Shift+V` on Mac) to open the preview in a new tab.
- Or press `Ctrl+K`, release, then press `V` to open the preview side by side with the text.

You can also press `Ctrl+Shift+P` and run **Markdown: Open Preview**.



## Recommended VS Code extensions

Open the Extensions view with `Ctrl+Shift+X` (`Cmd+Shift+X` on Mac), search for the name, and click **Install**.

| Extension | Why you need it |
| --- | --- |
| **PlatformIO IDE** | Build and upload the firmware to the ESP32 boards. Only needed if you work with real hardware. |
| **GitHub Pull Requests** | Review and comment on pull requests without leaving VS Code. Optional. |
| **Python** | Syntax highlighting and help when editing the simulator and tools. Optional. |

Restart VS Code after installing PlatformIO. The first start can take a few minutes while it downloads its tools.

## Workflow

1. [Get the latest main](#1-get-the-latest-main)
2. [Create a branch](#2-create-a-branch)
3. [Make and commit your changes](#3-make-and-commit-your-changes)
4. [Open a pull request](#4-open-a-pull-request)
5. [Get it reviewed and merged](#5-get-it-reviewed-and-merged)

### 1. Get the latest main

In VS Code, click the branch name in the bottom-left corner and select `main`. Then open **Source Control** (`Ctrl+Shift+G`) and click **Sync Changes**.

Terminal alternative (`Ctrl+ö`):

```bash
git checkout main
git pull
```

Make sure you have no unsaved or uncommitted changes before you switch branch.

### 2. Create a branch

Press `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac), run **Git: Create Branch...** and enter a name in this format:

```text
RESQ-<ticket-number>/NEW/<short-description>
```

Example: `RESQ-59/NEW/add-3d-view`

- `RESQ-59` is the Jira ticket.
- `NEW` is the type of work.
- Use lowercase letters and hyphens in the description. No spaces or special characters.

The new branch name now shows in the bottom-left corner. You are on your own branch.

### 3. Make and commit your changes

Edit and save your files (`Ctrl+S`), then test them. For example, run the simulator:

```bash
python simulator/server.py
```

Then open **Source Control** (`Ctrl+Shift+G`), stage your files with **+**, write a message that starts with the ticket number, and click **Commit**:

```text
RESQ-59: add 3D view
```

> [!IMPORTANT]
> Never commit `.env`, `include/secrets.h` or the `GROUP_KEY`. See [Keeping secrets out of Git](#keeping-secrets-out-of-git).

Click **Publish Branch** to upload the branch to GitHub. If you commit again on the same branch, click **Sync Changes** instead.

### 4. Open a pull request

On GitHub, click **Compare & pull request** and:

- Title it `RESQ-59: short description`.
- Explain what you changed and why.
- Select at least one teammate under **Reviewers**.
- Click **Create pull request**.

### 5. Get it reviewed and merged

**Author**

- Fix any comments on the same branch, commit and click **Sync Changes**. The pull request updates automatically.
- When it is approved, click **Merge pull request**, **Confirm merge** and **Delete branch**.
- In VS Code, switch back to `main` and click **Sync Changes**.

**Reviewer**

- Open the pull request on GitHub and click the **Files changed** tab.
- Click **+** next to a line to leave a comment.
- Check that the change matches the ticket, that the code is clear and that no secrets are included.
- Optional: test the change yourself. Press `Ctrl+Shift+P` and run **Git: Fetch**, click the branch name in the bottom-left corner and select the branch (it starts with `origin/RESQ-`), then run the simulator. Switch back to `main` afterwards.
- Click **Review changes**, choose **Approve**, **Request changes** or **Comment**, and click **Submit review**.

## Keeping secrets out of Git

`.env`, `include/secrets.h` and the `GROUP_KEY` must never end up on GitHub. The repository is public, and anything pushed stays in the Git history even if you delete the file afterwards.

### How it is prevented

The `.gitignore` file in the project root lists files Git must ignore:

```text
.env
include/secrets.h
.pio/
__pycache__/
```

Ignored files do not appear in **Source Control** in VS Code, so you cannot stage them by accident. To check that a file is ignored, run this in the terminal:

```bash
git check-ignore -v .env
```

If it prints a line with a rule, the file is ignored. If it prints nothing, the file is **not** protected. Add it to `.gitignore` and tell the team.

### Before every commit

1. Open **Source Control** (`Ctrl+Shift+G`).
2. Look at the **Staged Changes** list. It should contain only the files you meant to change.
3. If `.env` or `secrets.h` appears there, click the **−** (Unstage Changes) button next to it.
4. Prefer staging files one by one with **+** over **Stage All Changes**.

### If you made a mistake

| Situation | What to do |
| --- | --- |
| Staged, not yet committed | Click **−** next to the file in **Staged Changes**. |
| Committed, not yet pushed | Press `Ctrl+Shift+P`, run **Git: Undo Last Commit**, unstage the file with **−**, and commit again without it. |
| Already pushed to GitHub | Tell the project owner **immediately**. Deleting the file in a new commit is not enough, because the key is still in the history. The `GROUP_KEY` must be changed and every board re-flashed. |

If a secret file was committed at some point before it was ignored, Git keeps tracking it and `.gitignore` has no effect. Stop tracking it (the file stays on your disk):

```bash
git rm --cached .env
git commit -m "Stop tracking .env"
```