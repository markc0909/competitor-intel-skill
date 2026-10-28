# Installing and testing competitor-intel

A step-by-step guide for anyone trying the skill for the first time. Each step says what should happen, so you can tell whether it worked.

**You need:** Claude Code (desktop app or CLI), Python 3.9+ (`python3 --version`), git, and a Claude setup with web search available.

## 1. Install

**Option A: as a plugin (recommended).** In Claude Code:

```
/plugin marketplace add markc0909/competitor-intel-skill
/plugin install competitor-intel@competitor-intel
```

Restart Claude Code, or start a new session, so the skill loads.

**Option B: as a personal skill.**

```bash
git clone https://github.com/markc0909/competitor-intel-skill.git
```

```bash
./competitor-intel-skill/install.sh
```

**Expected:** `Installed to …/.claude/skills/competitor-intel`.

### Stop the permission prompts

A run makes dozens of web searches and page fetches. By default Claude Code asks before each new tool, and WebFetch asks again for each new site. The skill declares the tools it needs (`allowed-tools` in SKILL.md), but some hosts don't apply that, so add the rules to your user settings too. In `~/.claude/settings.json`, merge these into any existing `permissions` block:

```json
{
  "permissions": {
    "allow": [
      "WebSearch",
      "WebFetch",
      "Bash(python3 */competitor-intel/scripts/intel.py *)"
    ]
  }
}
```

Or, to have Claude do it, paste this into Claude Code. It asks you once to approve the edit to your settings file. Start a new session afterwards.

```text
Add these three rules to the "permissions.allow" list in my user settings file,
~/.claude/settings.json: "WebSearch", "WebFetch", and
"Bash(python3 */competitor-intel/scripts/intel.py *)".
If the file doesn't exist, create it. If it already has settings or a permissions
block, merge these in and keep everything else unchanged. Show me the file afterwards.
```

- [ ] A run finishes without asking you to approve searches, fetches, or `intel.py` commands.

You need these rules for scheduled runs. Nobody is there to click Allow, so without them a run stalls on its first search. They apply to every session, so Claude can fetch any URL without asking. To limit that to one project, put them in that project's `.claude/settings.json` instead.

## 2. Offline smoke test (about 1 minute, no web searches)

This exercises the helper script end to end against a made-up company. Run it from a clone of the repo. If you installed with Option A, clone the repo too, just for this step.

```bash
cd competitor-intel-skill
export COMPETITOR_INTEL_HOME=$(mktemp -d)
INTEL="python3 skills/competitor-intel/scripts/intel.py"
$INTEL init --watch acme
$INTEL config --plan > /dev/null && echo "config OK"
cp skills/competitor-intel/templates/example-digest.json "$COMPETITOR_INTEL_HOME/d.json"
$INTEL prepare --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL render  --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL commit  --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL prepare --input "$COMPETITOR_INTEL_HOME/d.json"
```

**Pass if:**

- [ ] `config OK` prints.
- [ ] The first `prepare` shows `"items": 3` and `"errors": []`.
- [ ] `render` lists `index.html`, `digest.md`, and `chat.txt`, along with an `attachment` path. Open that path in a browser: you should see a **Cross-portfolio** section, then one section per product.
- [ ] `commit` shows `"status": "committed"` and `"suggestions_added": 1`.
- [ ] The second `prepare` shows `"items": 0`, with all three items removed as `already reported`. That's the dedupe working.

Everything goes into the temp folder. Your real data isn't touched.

## 3. Live test in Claude (5–15 minutes)

Open a **new** Claude Code session and go through these in order.

1. **Set up.** Say: *"Set up a competitor watch for my company,"* then describe 1–3 of your products and 2–4 competitors in a sentence or two.
   - [ ] Claude creates `~/.competitor-intel/<watch>/watchlist.md`.
   - [ ] It shows you the products, competitors, and sample searches, and asks you to confirm.
2. **Run.** Say: *"Run the competitor watch."*
   - [ ] Claude searches the web.
   - [ ] The response **has `index.html` attached** and summarises the item count, top headline, coverage gaps, and the run folder path.
   - [ ] Every item cites a source URL.
   - [ ] On a quiet week you get a "nothing material" page, not filler.
3. **Edit by prompt.** Say: *"Add <competitor> as a direct competitor to <product>, and add '<phrase>' as a noise term."*
   - [ ] Claude edits the watchlist, validates it, and adds a line to `## Change Log`.
4. **Re-run.** Run the watch again straight away.
   - [ ] Nothing from step 2 is reported a second time.
5. **Status.** Say: *"Show the competitor watch status."*
   - [ ] You see the last run, the number of events remembered, and the noise counts.

## 4. Optional: scheduled runs

In the Claude desktop app, say: *"Schedule the competitor watch every Monday at 7am."*

- [ ] A scheduled task appears in the app.
- [ ] On "run now" (or the first scheduled run), the response attaches `index.html`.
- [ ] A new `runs/<run-id>/` folder appears under `~/.competitor-intel/<watch>/`.

The computer has to be awake at the scheduled time. For other ways to schedule, see [scheduling.md](skills/competitor-intel/references/scheduling.md).

## 5. Clean up

```bash
rm -rf ~/.competitor-intel/<watch>
```

To uninstall, run `/plugin uninstall competitor-intel@competitor-intel` (Option A), or `rm -rf ~/.claude/skills/competitor-intel` (Option B).

## Known limits

- The Claude web search tool is US-focused and has no date filter, so results for non-US competitors can be thin. A competitor whose searches return nothing is recorded as a **coverage gap**, not a quiet week, and its search window stays open so the next run covers the missed period.
- The example companies in the template and fixture (Acme, Rival Books, PayCo) are made up. Nothing in this repo is real competitive intelligence.

## Reporting problems

Open an issue at <https://github.com/markc0909/competitor-intel-skill/issues> and include the command or prompt that failed, its output, and the output of `$INTEL status`. Remove any company-confidential competitor names first.
