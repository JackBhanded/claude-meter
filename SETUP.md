# Ship Claude Meter to the world — your first public repo

This walks you from "code on my laptop" to "live on GitHub, downloadable by anyone, getting traction". You've never used git before — that's fine. Every step assumes nothing.

We'll do this in **3 phases**:

1. **Prep** — take a screenshot, install GitHub Desktop, pick a repo name
2. **Push** — create the repo, commit, push, cut a release
3. **Spread** — pin, tag, post, get the first 100 stars

If anything breaks at any step, paste the exact error message back at me.

---

## Phase 1 — Prep

### 1a. Take a screenshot of the working widget

Open Claude Meter on your machine. Hover over the ticker so the tooltip is visible. Take a screenshot of just the ticker + tooltip (Win + Shift + S, drag a rectangle around both).

Save it as **`C:\Users\Jack\Documents\Claude\Projects\Claude usage on taskbar\assets\screenshot.png`** — the README already references that path. Crop tightly. Aim for ~1200 × 600 pixels.

The screenshot is the **single most important thing** for stars. Most people scroll a GitHub README for two seconds and judge from the picture.

### 1b. Install GitHub Desktop

If you don't have it: **https://desktop.github.com/** → "Download for Windows" → run the installer. It opens automatically.

Sign in with your GitHub account when prompted.

### 1c. Pick a repo name

Suggestions (lowercase, hyphens, short):
- `claude-meter` ← recommended, matches the product name
- `claude-meter-windows`
- `claude-usage-meter`

Pick one. We'll use **`claude-meter`** below — substitute if you chose different.

---

## Phase 2 — Push

### 2a. Create the empty repo on GitHub

1. Open **https://github.com/new** in your browser.
2. Fill in:
   - **Repository name**: `claude-meter`
   - **Description**: `Windows taskbar widget showing your live Claude usage — per-model breakdown, reset countdowns, single .exe.`
   - **Public** (yes, we want everyone to find it)
   - **Initialize this repository with…** — leave **all three boxes unchecked**. We have our own README, .gitignore, LICENSE — checking them will fight ours.
3. Click **Create repository**.

You'll land on a setup page — keep that tab open, we'll come back to it.

### 2b. Connect this folder to the new repo

In GitHub Desktop:

1. **File → Add local repository…**
2. **Choose…** → navigate to `C:\Users\Jack\Documents\Claude\Projects\Claude usage on taskbar` → **Select Folder**.
3. It'll say "This directory does not appear to be a Git repository." — click **create a repository** in that warning.
4. Fill in:
   - **Name**: `claude-meter`
   - **Description**: same as before
   - **Local path**: leave as-is
   - **Initialize this repository with a README**: **UNCHECK** (we have one)
   - **Git Ignore**: leave as **None**
   - **License**: leave as **None**
5. Click **Create Repository**.

GitHub Desktop now sees this folder as a git repo. You'll see all your files listed as changes in the left sidebar.

### 2c. First commit

Bottom-left of GitHub Desktop has two text fields:

- **Summary**: `Initial commit — Claude Meter v0.1`
- **Description**: leave empty (or add a line if you want)

Click the blue **Commit to main** button.

That snapshot is now in your local git history. Nothing is on GitHub yet.

### 2d. Publish to GitHub

The top toolbar button now says **Publish repository**. Click it.

- **Name**: `claude-meter`
- **Description**: filled in
- **Keep this code private**: **UNCHECK** (we want public)
- Click **Publish Repository**.

It pushes. Takes 5–15 seconds.

Now go back to the github.com tab from step 2a and refresh. You should see all your files — the README rendering at the bottom with your screenshot and badges. 🎉

### 2e. Cut the first release (auto-builds the .exe)

We set up a GitHub Action that builds `ClaudeMeter.exe` automatically when you push a version tag. Here's how to push that tag:

In GitHub Desktop: **Repository → Open in Terminal** (or "Open in Command Prompt", depending on Windows version).

In the terminal that opens, type these exactly:

```cmd
git tag v0.1.0
git push origin v0.1.0
```

Now go to the github.com page for your repo and click the **Actions** tab. You'll see a workflow called "Release" running. Takes ~3–5 minutes.

When it finishes (green check), click the **Releases** link in the right sidebar of your repo's main page. You'll see "Release v0.1.0" with `ClaudeMeter.exe` attached. Anyone can now download it.

---

## Phase 3 — Spread the word

The repo is live. Now make it stand out. Here's a launch checklist, roughly in order:

### Day 1 — Make the repo discoverable

#### Add topics
On your repo's main page, click the ⚙️ gear next to "About" (top right). Add **topics** so people searching can find it:
```
claude  claude-code  anthropic  windows  taskbar  system-tray
usage-tracker  python  pyside6  qt  windows-10  windows-11
```

#### Pin the repo to your profile
GitHub profile → **Customize your pins** → check `claude-meter`. It now shows at the top of your profile for any visitor.

#### Add a Website link (optional)
If you have a personal site, put it in the "About" panel. Otherwise leave blank — README is enough.

#### Star your own repo
Click ⭐ Star. (Yes, your own. It's allowed. First-mover energy.)

### Day 2 — Post in two communities

#### Reddit — **r/ClaudeAI** (~80k members, very active)
- **Title**: `I built a Windows taskbar widget for live Claude usage tracking — every quota from /settings/usage, plus per-model breakdown`
- **Body**: 3-line description + screenshot + GitHub link
- Post around 9–11 AM US Eastern for max visibility

#### Reddit — **r/anthropic** (smaller but targeted)
- Same content, slightly different title

#### Don't post elsewhere yet — wait for feedback from these two, fix bugs that surface

### Day 3–5 — Bigger surfaces

#### Hacker News — Show HN
Once you have ~10 stars and feedback iterated in:
- Go to **https://news.ycombinator.com/submit**
- **Title**: `Show HN: Claude Meter – a Windows taskbar widget for Claude usage`
- **URL**: your repo link
- **Text**: a short paragraph explaining what's interesting (the `/api/oauth/usage` endpoint, the per-model breakdown, the comparison to existing tools)
- Post **Tuesday or Wednesday morning, 9 AM US Eastern**. Avoid weekends.

#### X / Twitter
Tweet a 30-second screen-recording with text like:
> Shipped my first open-source project: **Claude Meter** — a Windows taskbar widget that shows your live Claude usage. Per-model breakdown, reset countdowns, single .exe. Built for everyone who hits limits and wants to know before they hit them.
>
> github.com/your-username/claude-meter

Tag `@AnthropicAI` and `@claude_app` — they sometimes amplify community tools.

#### Submit to awesome-lists
- **awesome-claude** → https://github.com/AGI-Edgerunners/Awesome-Claude — open a PR adding your repo under "Tools".
- **awesome-anthropic** → similar pattern.

These are slow-burn discovery sources but generate a long tail of stars.

### Week 2 — Iterate on feedback

- Watch GitHub Issues. Respond within 24 hours.
- Cut **v0.1.1** with whatever the first wave surfaces (it always does — wrong DPI scaling on some monitor, missing edge case in credentials path, etc.).
- The same release Action triggers from `git tag v0.1.1; git push origin v0.1.1`.

### Optional: ProductHunt

Once you have ~50 stars and the bug-fix wave is done, ProductHunt is a force multiplier for getting it in front of non-developers. Launch on a **Tuesday** (highest traffic). DM me if you want help drafting the listing.

---

## When something breaks

The single most useful thing: paste the **exact error message** back at me, and I'll talk you through every recoverable situation. Common ones:

- **"This directory does not appear to be a Git repository"** — click the link inside that warning to create the repo locally.
- **"Repository already exists on GitHub"** — that's fine if it's empty; if it has files (like a README from the initialization step), delete the repo on GitHub and re-create it without checking the README / .gitignore / license boxes.
- **GitHub Action shows red instead of green** — click into the failing run; the line in red is the failure. Copy and paste that back here.
- **"refusing to merge unrelated histories"** — happens if GitHub's initialized files conflict with yours. Delete the github.com repo, re-create it empty, redo step 2d.

---

## Quick glossary (the words I just used)

- **repo / repository** — a project folder tracked by git.
- **commit** — a snapshot of your code with a message attached.
- **push** — upload commits from your machine to GitHub.
- **pull** — download new commits from GitHub to your machine.
- **branch** — a parallel line of work. Default is `main`. You won't need others yet.
- **tag** — a label stuck on a specific commit, used to mark a version like `v0.1.0`.
- **Action / workflow** — a script that runs on GitHub's servers when something happens.
- **Release** — a downloads page tied to a tag, where you publish the `.exe`.

---

## Making future changes

After the launch the cycle is short:

1. Edit files normally.
2. Open GitHub Desktop — it shows what's changed.
3. Type a one-line summary, click **Commit to main**.
4. Click **Push origin** in the top-right.

Done. CI runs the tests on every push.

To ship a new version with a fresh `.exe`:

1. Bump the version in `pyproject.toml` and `src/claude_usage_widget/__init__.py`.
2. Commit + push that change.
3. Open the terminal, run:
   ```cmd
   git tag v0.1.1
   git push origin v0.1.1
   ```
4. Wait for the Release Action to finish — fresh `.exe` appears in Releases.
