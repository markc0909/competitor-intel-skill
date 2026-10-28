# Watchlist format

`watchlist.md` is ordinary Markdown with a few conventions. A person can edit it in any editor, and `intel.py` parses it the same way every time.

The model follows how competitive maps are usually written: **per product**, a list of the rivals that compete with it, each with a competition type, the angle they compete on, and search terms specific to that product. Facts about a competitor that hold across every product (its domain, parent group, and whether its name is ambiguous) are written once, under Competitors.

## Syntax

| Element | Meaning |
|---|---|
| `## Section` | One of the sections below. Case-insensitive. |
| `### Entry` | A product, a competitor, or a group watch. The heading text is its canonical name. |
| `#### vs Competitor` | A **matchup** under a product, describing one competitor in relation to that product. |
| `- key: value` | A field on the nearest entry or matchup, or a setting under `## Settings`. |
| `- plain text` | A list item, in Market Watches, Noise Terms, Global Exclusions, Suggestions, and Change Log. |
| `<!-- … -->` | A comment. The parser ignores it. |

List fields are comma-separated. A value in double quotes is one term, even with commas inside, and the quotes are kept because they mean "exact phrase" to a search engine.

## Settings

| Key | Default | Meaning |
|---|---|---|
| `watch` | folder name | Slug for this watch |
| `company` | — | Your company name, used in report titles |
| `cadence` | `weekly` | `daily`, `weekly`, or `monthly`. Informational: the schedule controls when runs actually happen. |
| `lookback_days` | 7 | Search window for a first run |
| `overlap_days` | 2 | How far each window reaches back before the last cutoff, to catch late-indexed stories |
| `max_items` | 8 | Hard cap on Tier 1 + Tier 2 items per digest |
| `seen_window_days` | 90 | How long reported events are remembered for dedupe |
| `timezone` | system | IANA name, used for dates in log lines |
| `group_by` | `tier` | `product` groups the report by our product line, with a Cross-portfolio section first. `tier` groups by Act now / Worth knowing. |
| `outputs` | `markdown, html, chat` | Extra files `render` writes. `index.html` is always written, because every run's response attaches it. `markdown` adds `digest.md`, and `chat` adds `chat.txt`. |
| `quiet_runs` | `note` | `note` delivers a one-line "nothing material" message. `silent` delivers nothing. |
| `deliver_to` | `local` | Destinations. See `scheduling.md`. |

## Our Products

One `###` entry per product:

| Key | Meaning |
|---|---|
| `status` | `active` or `paused`. Paused products are not monitored. |
| `lifecycle` | `current` (default), `sunsetting`, or `legacy`. A sunsetting product is a **churn-risk window**: competitor migration offers and customer wins against it rank higher (see classification.md). |
| `priority` | `high`, `normal` (default), or `low`. Used when ranking and cutting items. Set `low` for legacy lines that only matter when specific deals are in play. |
| `area` | Portfolio grouping, such as "UK CRM" or "Payments" |
| `markets` | Geographies or segments |
| `description` | One line on what the product is, so Claude can write a specific "why it matters" |
| `aliases` | Other names for the product |
| `siblings` | Other products **we** own that sell into the same market. These are never competitors. |

Our product names, aliases, and siblings are automatically treated as "ours": an item whose competitor is one of them fails validation.

### Matchups: `#### vs <Competitor>`

Under a product, one block per real, in-market rival. Leave out aspirational or loosely adjacent players.

| Key | Meaning |
|---|---|
| `type` | `direct` (default), `adjacent`, or `internal`. **Direct**: same buyers, same job. **Adjacent**: not competing today, but watch for a specific move. **Internal**: one of ours (such as a migration path); never searched, and automatically excluded. |
| `role` | A short label for their position, such as `incumbent leader`, `growth challenger`, `suite incumbent`, `category leader`, `independent specialist`, `migration target`, `niche`, or `name-collision risk` |
| `how` | How they actually compete with this product. This is the angle Claude uses to judge impact and write "why it matters". **It's context, not evidence**: never cite it as a current fact. |
| `watch_for` | For adjacent rivals: the move that would make them direct, such as "move upmarket into sales CRM". If news shows that move, it's at least Tier 2. |
| `keywords` | Search terms specific to this matchup, such as "Rival Books New Zealand" under an NZ product or "Rival Books migration" under a sunsetting one |
| `exclude` | Extra negative terms for this matchup's queries |

The `<Competitor>` name must match a `### Competitors` entry if one exists. If no entry exists, a minimal one is created automatically.

Shorthand: a competitor entry with `competes_with: Product A, Product B` is the same as a plain `direct` matchup under each of those products, with no product-specific keywords.

## Competitors

One `###` entry per competing **company or brand**. These are brand-level facts shared across all of its matchups:

| Key | Meaning |
|---|---|
| `status` | `active` or `paused` |
| `keywords` | Brand-level search terms that catch company-wide news (funding, M&A, leadership) for every product the brand touches |
| `domain` | Official domain. Adds a `site:` newsroom query. |
| `parent` | A `### Competitors` entry that owns this brand, such as a product brand owned by a larger vendor. News about the parent maps to every product its brands compete with. |
| `ambiguous` | `yes` when the name is a common word (such as Cover, Street, or Funnel) or collides with another company. Claude must confirm each result is about this company. |
| `verify` | A specific disambiguation note, such as "PayCo here is the payments company, not PayCo Logistics". This implies `ambiguous`. |
| `aliases`, `products` | Other names, and the competitor's own product names |
| `exclude` | Negative terms for all of this brand's queries |
| `priority` | `high` puts this brand ahead of others at the same tier when ranking |
| `notes` | Free text for people. Ignored by the script. |

A competitor that only appears inside matchups doesn't need an entry. Add one when you have a domain, a parent, an ambiguity note, or brand-wide keywords.

## Group Watches

A standing watch on a cross-product theme, such as a consolidation move, a PE roll-up, or a merger, where one deal can change the picture for several of our products at once. Each runs once per run.

| Key | Meaning |
|---|---|
| `status` | `active` or `paused` |
| `affects` | Our products this theme touches |
| `competitors` | The competitor entries involved |
| `context` | One or two sentences on why this is being watched (context, not evidence) |
| `keywords` | The theme's search terms |

Items found through a group watch set `group_watch: <name>` in the digest and render in the **Cross-portfolio** section.

## Market Watches

Bullets with category-level queries for new entrants and industry moves.

## Noise Terms

Bullets that get negated in every query (except `site:` queries): listicle and SEO phrasing such as `best … software` or `top 10`. **Never put your own brand here.** It would hide the stories where a competitor wins one of your customers.

## Global Exclusions

Bullets for your own brand and domain, plus anything else that is never competitor news. These are **not** negated in searches. They're checked when items are validated: an item whose competitor matches one fails, and a source URL that matches one gets a warning.

## Suggestions and Change Log

`intel.py commit` appends `## Suggestions`, and `intel.py log` appends `## Change Log`. Nothing under Suggestions is searched until it's promoted into a real section.
