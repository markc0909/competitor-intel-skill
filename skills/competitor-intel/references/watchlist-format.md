# Watchlist format

`watchlist.md` is ordinary Markdown with a small number of conventions, so a person can edit it in any editor and `intel.py` can parse it the same way every time.

## Syntax

| Element | Meaning |
|---|---|
| `## Section` | One of the sections below. Case-insensitive. |
| `### Entry` | One product (under Our Products) or one competitor (under Competitors). The heading text is the entry's canonical name. |
| `- key: value` | A field on the current entry, or a setting under `## Settings`. Keys are lowercase with underscores. |
| `- plain text` | A list item, used in Market Watches, Global Exclusions, Suggestions, and Change Log. |
| `<!-- … -->` | A comment. The parser ignores it. |

List fields are comma-separated. A value in double quotes is one term, even if it contains a comma, and the quotes are kept because they mean "exact phrase" to a search engine. For example: `keywords: "Smith, Jones & Co", smithjones.example`.

## Sections

### Settings

| Key | Default | Meaning |
|---|---|---|
| `watch` | folder name | Slug for this watch |
| `company` | — | Your company name, used in report titles |
| `cadence` | `weekly` | `daily`, `weekly`, or `monthly`. Informational: the schedule actually controls when runs happen. Keep the two in sync. |
| `lookback_days` | 7 | Search window for a competitor's first run, or after a reset |
| `overlap_days` | 2 | How far each window reaches back before the last cutoff, to catch late-indexed stories |
| `max_items` | 8 | Hard cap on Tier 1 + Tier 2 items per digest |
| `seen_window_days` | 90 | How long reported events are remembered for dedupe |
| `timezone` | `UTC` | IANA name, such as `America/New_York`. Used for dates in log lines. |
| `outputs` | `markdown, html, chat` | Which files `render` writes |
| `quiet_runs` | `note` | `note` delivers a one-line "nothing material" message. `silent` delivers nothing. |
| `deliver_to` | `local` | Comma-separated destinations. See `scheduling.md`. |

### Our Products

One `###` entry per product:

| Key | Required | Meaning |
|---|---|---|
| `status` | yes | `active` or `paused`. Competitors whose only products are paused are skipped. |
| `description` | recommended | One line. Helps Claude write a specific "why it matters". |
| `aliases` | no | Other names for the product |
| `markets` | no | Geographies or segments, for judging relevance |

### Competitors

One `###` entry per competitor:

| Key | Required | Meaning |
|---|---|---|
| `status` | yes | `active` or `paused` |
| `competes_with` | yes | Exact `###` names from Our Products |
| `keywords` | yes if active | Search terms. Start with the quoted brand name. |
| `domain` | no | Official domain. Adds a `site:` newsroom query. |
| `products` | no | The competitor's own product names. Useful context and good keywords. |
| `exclude` | no | Terms to negate in this competitor's queries |
| `priority` | no | `high` or `normal`. A tie-breaker when ranking. |
| `notes` | no | Free text for people. Ignored by the script. |

### Market Watches

Bullets with category-level queries that run once per run, not once per competitor. Use them to catch new entrants and industry-wide moves. For example: `"embedded payments" acquisition`.

### Global Exclusions

Bullets with terms or domains that mark a result as not competitor news. These are added as negative terms to every query, and flagged if they show up in an item. **Always include your own brand and domain**, and any product name that collides with a competitor's.

### Suggestions

Written by `intel.py commit` from the digest's `suggestions`. Nothing here is searched. When the user accepts a suggestion, move it into the right section and delete its line.

### Change Log

Bullets written by `intel.py log`. Keep one line per change, saying what changed and why. This is the audit trail for "why are we watching this?".

## Example competitor entry

```markdown
### Rival Books
- status: active
- domain: rivalbooks.example
- competes_with: Acme Ledger
- products: Rival Books Cloud, Rival Books Payroll
- keywords: "Rival Books", rivalbooks.example, "Rival Books Cloud"
- exclude: "rival books review", "rival books vs"
- priority: high
```
