# Competitor Watchlist

<!--
This file is the single source of truth for what the competitor-intel skill
monitors. Edit it by hand, or ask Claude in plain English:
  "add Rival Co as a direct competitor to Acme Ledger"
  "Acme Classic is end of life — watch for competitors poaching its customers"
  "add a group watch for the PayCo / LedgerLite merger"

Format (see references/watchlist-format.md):
  ## Section              Settings, Our Products, Competitors, Group Watches, ...
  ### Entry              a product, competitor, or group watch
  #### vs Competitor     (under a product) one matchup: how they compete with it
  - key: value           a field; list fields are comma-separated
  - plain bullet         a list item (Market Watches, Noise Terms, Global Exclusions, ...)
Quote any term that contains a comma, or must match as an exact phrase.
-->

## Settings

- watch: acme
- company: Acme Corp
- cadence: weekly
- lookback_days: 7
- overlap_days: 2
- max_items: 8
- seen_window_days: 90
- timezone: UTC
- group_by: product
- outputs: markdown, html, chat
- quiet_runs: note
- deliver_to: local

## Our Products

<!-- One ### per product. Under it, one "#### vs <Competitor>" per real, in-market rival.
     type: direct | adjacent | internal. "how" is the angle Claude uses to judge impact;
     it is context, never evidence. Keywords here are product-specific search terms. -->

### Acme Ledger
- status: active
- area: Accounting
- markets: US, UK
- priority: high
- description: Cloud accounting for mid-market firms
- siblings: Acme Books Lite

#### vs Rival Books
- type: direct
- role: incumbent leader
- how: Default choice for mid-market firms moving off desktop; wins on accountant-partner network.
- keywords: "Rival Books" mid-market, "Rival Books" accountants, "Rival Books" AI

#### vs PayCo
- type: adjacent
- watch_for: PayCo adding general ledger or close features to its payments product
- keywords: PayCo accounting, PayCo ledger

### Acme Pay
- status: active
- area: Payments
- markets: US
- description: Embedded payments for SaaS platforms

#### vs PayCo
- type: direct
- role: category leader
- how: Best-known embedded payments brand; competes on partner revenue share.
- keywords: PayCo embedded payments, "PayCo" platform partners

### Acme Classic
- status: active
- lifecycle: sunsetting
- priority: high
- description: Legacy desktop accounting, end of life 2027; customers are migrating

#### vs Rival Books
- type: direct
- role: migration target
- how: Markets migration packages to Acme Classic customers during the sunset window.
- keywords: "Rival Books" migration, "switch from Acme Classic"

## Competitors

<!-- Brand-level facts shared by every product a competitor touches.
     keywords here catch brand-wide news (funding, M&A, leadership).
     parent: a group that owns this brand; news about the parent maps to its brands' products.
     ambiguous: yes when the name is a common word or collides with another company. -->

### Rival Books
- status: active
- domain: rivalbooks.example
- parent: Rival Group
- keywords: "Rival Books"
- exclude: "rival books review"
- priority: high

### Rival Group
- status: active
- keywords: "Rival Group" software, "Rival Group" acquisition

### PayCo
- status: active
- domain: payco.example
- ambiguous: yes
- verify: Not PayCo Logistics (unrelated freight company)
- keywords: "PayCo" payments

## Group Watches

<!-- Standing, cross-product watches: consolidation, PE roll-ups, mergers that can move
     several of our products at once. Each runs once per run, not once per product. -->

### Rival Group roll-up
- status: active
- affects: Acme Ledger, Acme Classic
- competitors: Rival Books, Rival Group
- context: Rival Group is acquiring adjacent tools to bundle a whole-of-market suite.
- keywords: "Rival Group" acquires, "Rival Books" merger

## Market Watches

<!-- Category-level queries for new entrants and industry moves. -->
- "mid-market accounting software" funding
- "embedded payments" acquisition

## Noise Terms

<!-- Negated in every query. Use for SEO and listicle phrasing, never for your own brand. -->
- best accounting software
- top 10
- alternatives to

## Global Exclusions

<!-- Never competitor news: your own brand, domain and products. Applied when validating items,
     NOT negated in searches (that would hide "competitor wins customer from us" stories).
     Our product names, aliases, siblings and internal matchups are added automatically. -->
- Acme Corp
- acme.example

## Suggestions

<!-- The skill appends candidate competitors/terms here. Nothing here is searched until you promote it. -->

## Change Log

<!-- One line per edit. The skill appends here when it changes this file. -->
- 2026-10-28: Created watchlist from template.
