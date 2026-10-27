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
