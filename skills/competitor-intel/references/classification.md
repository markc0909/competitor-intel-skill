# Classification

Classify every candidate event **before** writing anything about it. If you summarise first, SEO noise comes out as polished noise.

## Tiers

**Tier 1: act now.** These lead the digest and get a 🔴 marker in chat output.

- Funding round, acquisition, merger, or divestiture
- C-suite or other strategically significant leadership change
- Entering or leaving a geography or market segment
- A material public customer win or loss, especially one of ours
- Regulatory action, litigation, or a certification won or lost that affects market access
- A security incident or outage that hits customers or market access

**Tier 2: worth knowing.**

- A product or major feature launch, or a product being sunset
- A partnership or integration
- A pricing or packaging change
- A strategically relevant conference keynote, research report, analyst placement, or award

**Tier 3: suppress, and only count it.** These never become items. Add them to `suppressed.tier3_by_competitor`.

- "Best of" and "X vs Y" listicles, review-site content
- Routine vendor blog or marketing posts with no material change
- SEO pages whose business is ranking vendors
- Reposts of something already reported
- Job postings, unless a cluster of them clearly signals a Tier 1 or Tier 2 move. In that case, report the move with `confidence: low`.

**Borderline means suppress.** A missed minor item costs less than a digest people learn to ignore.

## Use the watchlist's map

The watchlist says *why* each competitor matters. Use it:

- **Matchup `type`.** News from a `direct` rival about the matched product is the default case. News from an `adjacent` rival is normally Tier 3, **unless** it shows the `watch_for` move (for example, an adjacent vendor launching a module that competes head-on). Then it's at least Tier 2, and Tier 1 if it's a launch into our customer base.
- **Matchup `how`.** This is the angle to test the news against. If a best-of-breed rival's pitch is "works with every suite", then its new integration with a suite incumbent matters *because of* that pitch. Say so in `why_it_matters`. Never cite `how` as a fact: it's a prior, written when the map was made.
- **Product `lifecycle: sunsetting`.** This is a live churn-risk window. Competitor migration offers, "switch from" campaigns, and public customer wins aimed at that product's base are **Tier 1**.
- **Product `priority: low`.** Report it only if it's Tier 1, or if it clearly ties to a deal in play.
- **Competitor `parent`.** Treat news about a parent group (a fund, holding company, or acquirer) as news about every brand under it. List every one of our products those brands touch.
- **Group watches.** A consolidation move that touches two or more of our products is Tier 1 by default. Set `group_watch` on the item.
- **`ambiguous` / `verify`.** Drop any result you can't tie to the right company by domain, product, or market. A name collision, such as a different company with a similar name, is never an item.

## Categories

`funding`, `m&a`, `leadership`, `geography`, `customer`, `regulatory`, `product`, `partnership`, `pricing`, `incident`, `event`, `other`

## Confidence

- **high**: a primary source (the competitor, a regulator, or a filing), or two independent reputable outlets
- **medium**: one reputable secondary source
- **low**: a single weak source, or an inference from signals. Say this in `what_changed`.

## Relevance test

Before keeping an item, finish this sentence: *"This matters to **<one of our products>** because…"*. If the honest ending is generic ("…it's a competitor"), downgrade the item to Tier 3.

## Ranking (when over `max_items`)

1. Tier
2. Number of our products affected
3. How direct the competition is (`priority: high` competitors first)
4. Confidence and source authority
5. Recency

`intel.py prepare` sorts by tier, product count, confidence, and recency. Apply the directness judgement yourself when choosing what to cut.
