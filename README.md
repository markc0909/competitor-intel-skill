# competitor-intel

An open-source Claude skill that monitors your competitors on a schedule and gives you a short, cited digest of what actually changed. No dashboards, no database: what to watch lives in a plain Markdown file you can read, diff, and edit by asking Claude.

```
watchlist.md  ──►  Claude researches  ──►  intel.py dedupes & validates  ──►  digest.md / index.html / chat.txt
     ▲                                                                              │
     └──────────── suggestions + change log ◄──── state.json (seen events, cutoffs) ◄┘
```

## What you get

- **A Markdown watchlist** (`watchlist.md`) with your products, your competitors, which product each competitor threatens, search keywords, market-wide watch terms, exclusions, and delivery settings.
- **Prompt-driven upkeep.** Say "add LedgerLite as a competitor to Acme Ledger" or "stop tracking the term 'embedded finance'". Claude edits the file, validates it, and writes a line to the change log.
- **Noise control.** Tier 1 (funding, M&A, leadership, regulatory), Tier 2 (launches, partnerships, pricing), and Tier 3 (listicles and SEO noise, which are only counted). Ten articles about one deal count as one event.
- **Memory between runs.** `state.json` remembers what was already reported (by semantic fingerprint and canonical URL) and a cutoff for each competitor. A failed search never silently skips a week, and a re-run never alerts twice.
- **One digest, many formats.** Markdown, a self-contained responsive HTML page, and chat text that pastes cleanly into Slack, Teams, or WhatsApp, all rendered from the same JSON so they can't disagree.
- **Self-improving coverage.** Each run can suggest new competitors or keywords. They go into a `## Suggestions` section for you to accept or dismiss, and they're never applied automatically.

## Install

**As a Claude Code plugin** (once this repo is on GitHub):

```
/plugin marketplace add markc0909/competitor-intel-skill
/plugin install competitor-intel@competitor-intel
```

**As a personal skill** (copies to `~/.claude/skills/competitor-intel`):

```bash
git clone https://github.com/markc0909/competitor-intel-skill.git && ./competitor-intel-skill/install.sh
```

**Claude.ai / Claude desktop (chat)**: zip `skills/competitor-intel/` and upload it under Settings → Capabilities → Skills. Chat sandboxes may not keep files between conversations, so for scheduled runs with persistent state, use Claude Code (desktop app, CLI, or a cloud routine backed by a git repo).

Requirements: Python 3.9+ (stdlib only), plus a web search tool in Claude.

## Quick start

1. In Claude, say: **"Set up a competitor watch for my company."** Describe your products and competitors in a sentence or two. Claude drafts `~/.competitor-intel/<watch>/watchlist.md` and shows it to you to confirm.
2. Say: **"Run the competitor watch."** You get `digest.md`, `index.html`, and `chat.txt` under `~/.competitor-intel/<watch>/runs/<run-id>/`.
3. Say: **"Schedule it every Monday at 7am and email the digest to me."** See [scheduling.md](skills/competitor-intel/references/scheduling.md) for the desktop scheduled task, cron + `claude -p`, and cloud routine options.

From then on, tell Claude in plain language when you want to change what's monitored.

## Repository layout

```
.claude-plugin/              plugin + marketplace manifests
skills/competitor-intel/
  SKILL.md                   the procedure Claude follows (setup, run, maintain, review)
  scripts/intel.py           deterministic helper: parse, plan, prepare, render, commit, log, status
  templates/watchlist.md     starter watchlist (synthetic example company)
  templates/example-digest.json  synthetic digest fixture for testing renderers
  references/                watchlist format, classification rules, digest schema, scheduling
install.sh                   copy-install for ~/.claude/skills
```

## The helper CLI

Claude runs these commands for you. They also work on their own for debugging:

```bash
INTEL="python3 ~/.claude/skills/competitor-intel/scripts/intel.py"
$INTEL init --watch acme --company "Acme Corp"   # create watch folder from template
$INTEL config --plan                             # validate watchlist; print windows + query plan
$INTEL prepare --input digest.json               # fingerprint, dedupe vs history, rank, validate
$INTEL render  --input digest.json               # write md/html/chat to runs/<run-id>/
$INTEL commit  --input digest.json --delivered-to local   # record run; advance cutoffs
$INTEL log "Added LedgerLite as competitor"      # append to watchlist change log
$INTEL status                                    # last run, seen count, Tier 3 noise trend
```

Set `COMPETITOR_INTEL_HOME` to keep data somewhere other than `~/.competitor-intel`, or pass `--dir <path>` to use a watch folder inside a git repo.

## Try it without searching

```bash
export COMPETITOR_INTEL_HOME=$(mktemp -d)
INTEL="python3 skills/competitor-intel/scripts/intel.py"
$INTEL init --watch acme
cp skills/competitor-intel/templates/example-digest.json "$COMPETITOR_INTEL_HOME/d.json"
$INTEL prepare --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL render  --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL commit  --input "$COMPETITOR_INTEL_HOME/d.json"
$INTEL prepare --input "$COMPETITOR_INTEL_HOME/d.json"   # replay: both items removed as already seen
```

## Design notes

- **Markdown as config.** The watchlist is the one place to change what's monitored. It's diff-friendly and readable by non-engineers, and the parser is deliberately simple (`##` sections, `###` entries, `- key: value` fields).
- **Claude judges, the script counts.** Classification and analysis need judgement. Hashing, dedupe, windows, and state updates must be deterministic. Mixing the two is how digests drift.
- **State only advances after delivery.** `commit` is the last step and is idempotent per run.
- **Nothing in this repo is real intelligence.** The template and fixture use made-up companies.

## License

MIT
