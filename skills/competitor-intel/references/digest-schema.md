# Digest schema

Each run produces exactly one digest JSON. Every output is rendered from it. See `templates/example-digest.json` for a complete (synthetic) example.

```jsonc
{
  "watch": "acme",                       // optional; prepare fills it in
  "generated_at": "2026-10-28T07:00:00Z",// optional; prepare fills it in. Also used as the run id.
  "window": {                            // optional; prepare fills it from the plan
    "since": "2026-10-19T07:00:00Z",
    "until": "2026-10-28T07:00:00Z"      // commit advances cutoffs to this
  },
  "summary": "Two-sentence executive summary.",   // optional
  "items": [                             // Tier 1 and Tier 2 only, at most max_items
    {
      "event_key": "payco-series-c-2026",          // required: stable semantic slug for the event
      "event_fingerprint": "…",                    // written by prepare. Never hand-write this.
      "tier": 1,                                   // required: 1 or 2
      "category": "funding",                       // required: see classification.md
      "competitor": "PayCo",                       // required: exact ### name from the watchlist
      "our_products": ["Acme Pay"],                // required: exact ### names, active products only
      "headline": "PayCo raises $80M Series C",    // required
      "what_changed": "Facts only.",               // required
      "why_it_matters": "Implication for the named product.", // required
      "published_at": "2026-10-22",                // required: ISO date or datetime
      "confidence": "high",                        // required: high | medium | low
      "source": {                                  // required: the most primary source
        "title": "…", "publisher": "…", "url": "https://…"
      },
      "corroboration": [ { "title": "…", "publisher": "…", "url": "https://…" } ], // optional
      "follow_up": "One concrete next action."     // optional
    }
  ],
  "suppressed": {
    "tier3_by_competitor": { "Rival Books": 4 }    // optional; kept in state for trend reporting
    // "already_seen": [...]                        // written by prepare
  },
  "coverage_gaps": [                               // competitors whose searches failed this run
    { "competitor": "PayCo", "reason": "search tool timed out" }  // use "_market" for market watches
  ],
  "suggestions": [                                 // proposed watchlist changes; commit appends these
    { "type": "competitor|keyword|exclusion|product", "value": "LedgerLite", "reason": "…" }
  ]
}
```

## Fingerprint

`event_fingerprint = sha256(norm(competitor) | norm(category) | norm(event_key))`, where `norm` lowercases the text and collapses anything that isn't alphanumeric to `-`. Because the hash ignores the headline and the URL, a new article about an already-reported event still dedupes, as long as you reuse the same `event_key`. That's why keys must describe the event, not the article.

Dedupe also matches on canonical source URL. Canonicalising lowercases the host, drops `www.`, strips tracking parameters and fragments, and removes trailing slashes.
