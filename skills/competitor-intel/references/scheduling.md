# Scheduling and delivery

The skill is designed to run unattended. Every scheduled run is a fresh conversation, so continuity comes from the watch folder (`watchlist.md` and `state.json`), not from chat memory.

## The scheduled prompt

Every scheduler below uses the same self-contained prompt. Replace `<slug>` and the delivery line.

```text
Use the competitor-intel skill to do an unattended Run for watch "<slug>".
Follow the Run procedure in SKILL.md exactly: config --plan, research, prepare,
render, deliver, commit. Ask no questions. Do not edit products or competitors
in the watchlist; only append suggestions via commit. If config fails or
delivery fails, do not commit — report the problem instead.
Deliver to the destinations in the watchlist's deliver_to setting.
End with a 3-line summary: item count, top headline, where outputs are.
```

## Option A: Claude desktop app scheduled task (recommended)

Claude Code's desktop app can run a prompt on a schedule, on your machine, with your tools and connectors. Ask Claude:

> Schedule the competitor-intel run for watch "acme" every Monday at 7am.

Claude creates the scheduled task with the prompt above. Runs happen locally, so `~/.competitor-intel/` persists between runs with no extra setup. You can see past runs and edit or pause the task from the app's scheduled tasks view, or by asking Claude.

The computer has to be awake at the scheduled time. A run you miss can be started by hand, and the per-competitor cutoffs mean nothing gets skipped.

## Option B: headless `claude -p` from cron or launchd

For a server, or any machine without the desktop app:

```bash
# crontab -e   (Mondays 07:00)
0 7 * * 1  cd ~ && claude -p "$(cat ~/.competitor-intel/acme/scheduled-prompt.txt)" \
  --allowedTools "Bash(python3:*) WebSearch WebFetch Read Write Edit" \
  >> ~/.competitor-intel/acme/cron.log 2>&1
```

Save the scheduled prompt to `scheduled-prompt.txt` in the watch folder. Use `--allowedTools` to grant only what a run needs. Add your delivery connectors' tools if `deliver_to` uses them.

## Option C: cloud routine

Claude Code's cloud scheduled agents (`/schedule`) run in a fresh cloud checkout of a git repository, so `~/.competitor-intel` doesn't persist there. To use them:

1. Put the watch folder in a git repository, such as `intel/acme/` in a private repo.
2. Tell the prompt to pass `--dir intel/acme` to every `intel.py` command, and to **commit and push `watchlist.md`, `state.json`, and `runs/` at the end**.
3. Remember that only the connectors configured for the cloud environment are available for delivery.

## Delivery (`deliver_to`)

`deliver_to` in the watchlist settings is a comma-separated list. Writing a destination there is the user's standing authorisation for unattended runs to send to it. Never send anywhere that isn't listed.

| Value | What Claude does |
|---|---|
| `local` | Nothing extra. The files in `runs/<run-id>/` are the deliverable. |
| `email:<address>` | Sends `digest.md` (or the HTML) through a connected email tool. If the tool can only draft, it creates a draft and says so. |
| `slack:<#channel>` / `teams:<channel>` | Posts `chat.txt` through the connected Slack or Teams tool |
| `notion:<page or database>` | Creates a page from `digest.md` under that parent |
| `artifact` | Publishes `index.html` as a private page, where the host supports that |
| `folder:<path>` | Copies the run folder to that path, such as a synced drive |

If the tool for a destination isn't connected, deliver locally, mention it in the run summary, and still commit: the research succeeded, and the local files are a valid delivery. If a send was *attempted* and errored, don't commit. The next run retries, and dedupe keeps it from double-reporting.

## Cadence tips

- **Weekly** is the default. Use `lookback_days: 7` and `overlap_days: 2`.
- **Daily**: set `lookback_days: 2`, `overlap_days: 1`, and `max_items: 5`. Consider `quiet_runs: silent`.
- **Monthly**: set `lookback_days: 31`, `overlap_days: 3`, and `max_items: 12`.
- A separate monthly "trends" prompt can read `state.json` (`runs`, `tier3`, `seen`) to summarise patterns, such as which competitor is most active, without searching again.
