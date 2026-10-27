# Competitor Watchlist

<!--
This file is the single source of truth for what the competitor-intel skill
monitors. Edit it by hand, or ask Claude in plain English:
  "add Rival Co as a competitor to Acme Ledger"
  "pause the Acme Pay product"
  "add the search term 'embedded payments funding' to market watches"

Format rules (kept simple so it stays both human- and machine-readable):
  ## Section       one of the sections below
  ### Entry name   a product or competitor
  - key: value     a field; list fields are comma-separated
  - plain bullet   a list item (Market Watches, Global Exclusions, Suggestions)
Quote any term that contains a comma: "Smith, Jones & Co".
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
- outputs: markdown, html, chat
- quiet_runs: note
- deliver_to: local

## Our Products

### Acme Ledger
- status: active
- description: Cloud accounting for mid-market firms
- aliases: Ledger by Acme
- markets: US, UK

### Acme Pay
- status: active
- description: Embedded payments for SaaS platforms
- markets: US

## Competitors

### Rival Books
- status: active
- domain: rivalbooks.example
- competes_with: Acme Ledger
- products: Rival Books Cloud, Rival Books Payroll
- keywords: "Rival Books", rivalbooks.example
- exclude: "rival books review", "rival books vs"
- priority: high

### PayCo
- status: active
- domain: payco.example
- competes_with: Acme Pay
- keywords: PayCo payments, "PayCo embedded"
- exclude: "PayCo coupon"
- priority: normal

### Old Rival
- status: paused
- competes_with: Acme Ledger
- keywords: "Old Rival"
- notes: Acquired 2025; keep for history, do not search

## Market Watches

<!-- Category-level search terms run once per run, not once per competitor. -->
- "mid-market accounting software" funding
- "embedded payments" acquisition
- "accounting software" regulation

## Global Exclusions

<!-- Terms or domains that must never count as competitor news. Include your own brand. -->
- Acme Corp
- acme.example
- "best accounting software"

## Suggestions

<!-- The skill appends candidate competitors/terms here. Nothing here is searched until you promote it. -->

## Change Log

<!-- One line per edit. The skill appends here when it changes this file. -->
- 2026-10-28: Created watchlist from template.
