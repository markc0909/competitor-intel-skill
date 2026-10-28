#!/usr/bin/env python3
"""competitor-intel helper: the deterministic half of the skill.

Claude does the research and judgement; this script does everything that must
be mechanical and repeatable: parsing the Markdown watchlist, planning queries,
fingerprinting events, deduplicating against history, validating digests,
rendering outputs, and updating persistent state.

Stdlib only. Python 3.9+.

Data lives in $COMPETITOR_INTEL_HOME (default ~/.competitor-intel), one folder
per watch:

    <home>/<watch>/watchlist.md   human-edited config (source of truth)
    <home>/<watch>/state.json     seen log, per-competitor cutoffs, run history
    <home>/<watch>/runs/<run-id>/ archived digests and rendered outputs
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "watchlist.md"

CATEGORIES = {
    "funding", "m&a", "leadership", "geography", "customer", "regulatory",
    "product", "partnership", "pricing", "incident", "event", "other",
}
CONFIDENCE = {"high", "medium", "low"}
LIST_FIELDS = {
    "aliases", "markets", "competes_with", "products", "keywords", "exclude",
    "outputs", "siblings", "affects", "competitors",
}
MATCHUP_TYPES = {"direct": 0, "adjacent": 1, "internal": 9}
PRIORITY = {"high": 0, "normal": 1, "low": 2}
INT_SETTINGS = {
    "lookback_days": 7, "overlap_days": 2, "max_items": 8, "seen_window_days": 90,
}
DEFAULT_SETTINGS = {
    "cadence": "weekly", "timezone": "UTC", "outputs": ["markdown", "html", "chat"],
    "quiet_runs": "note", "deliver_to": "local", "group_by": "tier", **INT_SETTINGS,
}
ENTRY_SECTIONS = {"our products", "competitors", "group watches"}
BULLET_SECTIONS = {"market watches", "noise terms", "global exclusions", "suggestions", "change log"}
MARKET_KEY = "_market"
GROUP_PREFIX = "_group:"
MAX_NEGATIVES = 6
TRACKING_PARAMS = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|ref|ref_src|cmpid|ocid)$", re.I)
CHAT_LIMIT = 3000


class IntelError(Exception):
    pass


# --------------------------------------------------------------------------- paths

def home_dir() -> Path:
    return Path(os.environ.get("COMPETITOR_INTEL_HOME", "~/.competitor-intel")).expanduser()


def watch_dir(args) -> Path:
    if getattr(args, "dir", None):
        return Path(args.dir).expanduser()
    if getattr(args, "watch", None):
        return home_dir() / args.watch
    watches = list_watches()
    if len(watches) == 1:
        return home_dir() / watches[0]
    if not watches:
        raise IntelError("No watches found. Run: intel.py init --watch <slug>")
    raise IntelError(f"Several watches exist ({', '.join(watches)}); pass --watch.")


def list_watches() -> list[str]:
    root = home_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "watchlist.md").is_file())


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_json(path: Path, data) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------- time helpers

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def local_today(cfg: dict | None = None) -> str:
    """Today's date in the watch's configured timezone, for human-facing log lines."""
    tz = dt.timezone.utc
    name = (cfg or {}).get("settings", {}).get("timezone", "UTC")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(name)
    except Exception:
        pass
    return now_utc().astimezone(tz).strftime("%Y-%m-%d")


def system_timezone() -> str:
    """Best-effort IANA name for the machine's timezone; UTC if unknown."""
    if os.environ.get("TZ") and "/" in os.environ["TZ"]:
        return os.environ["TZ"].lstrip(":")
    try:
        target = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return "UTC"


def iso(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> dt.datetime:
    v = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        v += "T00:00:00+00:00"
    v = v.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(v)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


# --------------------------------------------------------------- watchlist parser

def split_list(value: str) -> list[str]:
    """Split on commas outside double quotes. Quotes are kept: they mean exact phrase."""
    out, buf, quoted = [], [], False
    for ch in value:
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
        elif ch == "," and not quoted:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return [x for x in out if x]


def unquote(term: str) -> str:
    return term.strip().strip('"').strip()


def parse_watchlist(path: Path) -> dict:
    """Sections (##) hold fields, entries (###) or bullets. Product entries may hold
    matchups (#### vs <Competitor>), each with its own fields."""
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    sections: dict[str, dict] = {}
    section = entry = matchup = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        where = f"{path.name}:{lineno}"
        if line.startswith("## "):
            section = line[3:].strip().lower()
            sections.setdefault(section, {"fields": {}, "entries": {}, "items": []})
            entry = matchup = None
        elif line.startswith("### ") and section:
            entry, matchup = line[4:].strip(), None
            if entry in sections[section]["entries"]:
                raise IntelError(f"{where}: duplicate entry '{entry}' in '{section}'")
            sections[section]["entries"][entry] = {"name": entry, "matchups": []}
        elif line.startswith("#### ") and section:
            m = re.match(r"^####\s+vs\.?\s+(.+)$", line, re.I)
            if not m or not entry or section != "our products":
                raise IntelError(f"{where}: '####' is only for '#### vs <Competitor>' under a product")
            matchup = {"competitor": m.group(1).strip()}
            sections[section]["entries"][entry]["matchups"].append(matchup)
        elif re.match(r"^\s*[-*] ", line) and section:
            body = re.sub(r"^\s*[-*] ", "", line).strip()
            m = re.match(r"^([a-z_]+):\s*(.*)$", body)
            if section in BULLET_SECTIONS or not m:
                sections[section]["items"].append(body)
                continue
            key, value = m.group(1), m.group(2).strip()
            if matchup is not None:
                target = matchup
            elif entry:
                target = sections[section]["entries"][entry]
            else:
                target = sections[section]["fields"]
            target[key] = split_list(value) if key in LIST_FIELDS else value
    return sections


def _yes(value) -> bool:
    return str(value).strip().lower() in {"yes", "true", "y", "1"}


def load_config(wdir: Path) -> dict:
    """Parse watchlist.md into products, competitor entities, matchups and watches.

    The model mirrors how competitive maps are usually written: per product, a list
    of competitors with a competition type, an angle ("how they compete") and
    product-specific search terms. Competitor entities hold brand-level facts
    (domain, parent group, ambiguity) shared across every product they touch.
    """
    path = wdir / "watchlist.md"
    if not path.is_file():
        raise IntelError(f"Missing {path}. Run: intel.py init --watch <slug>")
    s = parse_watchlist(path)
    get = lambda name: s.get(name, {"fields": {}, "entries": {}, "items": []})
    errors, warnings = [], []

    settings = dict(DEFAULT_SETTINGS)
    settings.update(get("settings")["fields"])
    for key in INT_SETTINGS:
        try:
            settings[key] = int(settings[key])
        except (TypeError, ValueError):
            errors.append(f"Settings: {key} must be an integer (got {settings[key]!r})")
    if isinstance(settings.get("outputs"), str):
        settings["outputs"] = split_list(settings["outputs"])
    if settings["group_by"] not in ("tier", "product"):
        errors.append("Settings: group_by must be 'tier' or 'product'")
    settings.setdefault("watch", wdir.name)

    known = {"settings"} | ENTRY_SECTIONS | BULLET_SECTIONS
    for name, sec in s.items():
        if name not in known:
            warnings.append(f"Unknown section '## {name}' is ignored")
        elif sec["entries"] and name not in ENTRY_SECTIONS:
            errors.append(f"'### {next(iter(sec['entries']))}' sits under '## {name}'; "
                          "### entries belong under Our Products, Competitors or Group Watches")

    # -- products
    products = list(get("our products")["entries"].values())
    for p in products:
        p["status"] = str(p.get("status", "active")).lower()
        p["lifecycle"] = str(p.get("lifecycle", "current")).lower()
        p["priority"] = str(p.get("priority", "normal")).lower()
        for f in ("aliases", "markets", "siblings"):
            p.setdefault(f, [])
        if p["priority"] not in PRIORITY:
            errors.append(f"Product '{p['name']}': priority must be high, normal or low")
    by_product = {p["name"]: p for p in products}
    active_products = [p["name"] for p in products if p["status"] == "active"]
    if not products:
        errors.append("Our Products: add at least one product (### Name)")

    # -- competitor entities
    entities = get("competitors")["entries"]
    for e in entities.values():
        e.pop("matchups", None)
        e["status"] = str(e.get("status", "active")).lower()
        e["ambiguous"] = _yes(e.get("ambiguous", "no"))
        for f in ("aliases", "products", "keywords", "exclude", "competes_with"):
            e.setdefault(f, [])

    # Shorthand: competes_with on an entity == a plain direct matchup on each product.
    for e in entities.values():
        for pname in e["competes_with"]:
            if pname not in by_product:
                errors.append(f"Competitor '{e['name']}': competes_with names unknown product '{pname}'")
            elif not any(m["competitor"] == e["name"] for m in by_product[pname]["matchups"]):
                by_product[pname]["matchups"].append({"competitor": e["name"], "type": "direct"})

    # -- matchups
    internal_names = set()
    for p in products:  # our own products, aliases and siblings are never competitors
        internal_names.update([p["name"], *p["aliases"], *p["siblings"]])
        for m in p["matchups"]:
            m["product"] = p["name"]
            m["type"] = str(m.get("type", "direct")).lower()
            for f in ("keywords", "exclude"):
                m.setdefault(f, [])
            if m["type"] not in MATCHUP_TYPES:
                errors.append(f"{p['name']} vs {m['competitor']}: type must be direct, adjacent or internal")
            if m["type"] == "internal":
                internal_names.add(m["competitor"])
                continue
            if m["competitor"] not in entities:  # allowed: entity inferred from the matchup
                entities[m["competitor"]] = {"name": m["competitor"], "status": "active", "ambiguous": False,
                                             "aliases": [], "products": [], "keywords": [], "exclude": [],
                                             "competes_with": [], "inferred": True}

    for e in entities.values():
        if e.get("parent") and e["parent"] not in entities:
            errors.append(f"Competitor '{e['name']}': parent '{e['parent']}' is not a ### entry under Competitors")
    children: dict[str, list[str]] = {}
    for e in entities.values():
        if e.get("parent"):
            children.setdefault(e["parent"], []).append(e["name"])

    def family(name: str) -> set[str]:
        """An entity plus all its descendants: news about a parent affects every brand under it."""
        out, stack = set(), [name]
        while stack:
            n = stack.pop()
            if n not in out:
                out.add(n)
                stack.extend(children.get(n, []))
        return out

    matchups = [m for p in products for m in p["matchups"] if m["type"] != "internal"]
    for e in entities.values():
        fam = family(e["name"])
        rows = [m for m in matchups if m["competitor"] in fam]
        e["affects"] = sorted({m["product"] for m in rows if m["product"] in active_products})
        e["directness"] = min((MATCHUP_TYPES[m["type"]] for m in rows if m["type"] in MATCHUP_TYPES), default=9)
        if e["status"] == "active" and not e["affects"]:
            e["status"] = "inactive"
            if rows:
                warnings.append(f"Competitor '{e['name']}': all its products are paused; skipping")
            elif not e.get("inferred"):
                warnings.append(f"Competitor '{e['name']}': not matched to any product; skipping")
        own_kw = e["keywords"] or [kw for m in rows if m["competitor"] == e["name"] for kw in m["keywords"]]
        if e["status"] == "active" and not own_kw and not children.get(e["name"]):
            errors.append(f"Competitor '{e['name']}': needs keywords (on the entity or its matchups)")
        if e["name"] in internal_names:
            errors.append(f"'{e['name']}' is listed as internal/sibling but also as a competitor")

    # -- group watches: standing, cross-product watches (e.g. consolidation moves)
    groups = list(get("group watches")["entries"].values())
    for g in groups:
        g.pop("matchups", None)
        g["status"] = str(g.get("status", "active")).lower()
        for f in ("affects", "competitors", "keywords", "exclude"):
            g.setdefault(f, [])
        for pname in g["affects"]:
            if pname not in by_product:
                errors.append(f"Group watch '{g['name']}': affects unknown product '{pname}'")
        for cname in g["competitors"]:
            if cname not in entities:
                warnings.append(f"Group watch '{g['name']}': competitor '{cname}' is not on the watchlist")
        if g["status"] == "active" and not g["keywords"]:
            errors.append(f"Group watch '{g['name']}': needs keywords")
    active_groups = [g["name"] for g in groups if g["status"] == "active"]

    exclusions = [unquote(x) for x in get("global exclusions")["items"]]
    active_entities = [n for n, e in entities.items() if e["status"] == "active"]

    return {
        "path": str(path),
        "settings": settings,
        "products": products,
        "competitors": list(entities.values()),
        "group_watches": groups,
        "active_products": active_products,
        "active_competitors": active_entities,
        "active_groups": active_groups,
        "watch_keys": active_entities + [GROUP_PREFIX + g for g in active_groups] + [MARKET_KEY],
        "market_watches": get("market watches")["items"],
        "noise_terms": [unquote(x) for x in get("noise terms")["items"]],
        "global_exclusions": exclusions,
        "internal_names": sorted(internal_names),
        "suggestions": get("suggestions")["items"],
        "errors": errors,
        "warnings": warnings,
    }


def entity_of(cfg: dict, name: str) -> dict | None:
    return next((e for e in cfg["competitors"] if e["name"] == name), None)


def product_of(cfg: dict, name: str) -> dict | None:
    return next((p for p in cfg["products"] if p["name"] == name), None)


# ------------------------------------------------------------------------- state

def empty_state(watch: str) -> dict:
    return {"version": 1, "watch": watch, "cutoffs": {}, "seen": [], "runs": [], "tier3": []}


def load_state(wdir: Path) -> dict:
    path = wdir / "state.json"
    return read_json(path) if path.is_file() else empty_state(wdir.name)


def plan_window(cfg: dict, state: dict, now: dt.datetime) -> dict:
    """Per-competitor search window. Competitors that failed last time keep their old cutoff."""
    st = cfg["settings"]
    default_since = now - dt.timedelta(days=st["lookback_days"])
    overlap = dt.timedelta(days=st["overlap_days"])
    out = {}
    for key in cfg["watch_keys"]:
        cut = state["cutoffs"].get(key)
        since = parse_time(cut) - overlap if cut else default_since
        out[key] = iso(since)
    return {"until": iso(now), "since_by_watch": out}


# ---------------------------------------------------------------- normalisation

def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", host, path, query, ""))


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def fingerprint(item: dict) -> str:
    basis = "|".join([norm(item.get("competitor", "")), norm(item.get("category", "")), norm(item.get("event_key", ""))])
    return hashlib.sha256(basis.encode()).hexdigest()


# ------------------------------------------------------------------- digest ops

def load_digest(path: Path) -> dict:
    d = read_json(path)
    d.setdefault("items", [])
    d.setdefault("suppressed", {})
    d.setdefault("coverage_gaps", [])
    d.setdefault("suggestions", [])
    return d


def do_fingerprint(digest: dict) -> None:
    for item in digest["items"]:
        item["event_fingerprint"] = fingerprint(item)
        src = item.get("source") or {}
        if src.get("url"):
            src["url"] = canonical_url(src["url"])
        for extra in item.get("corroboration", []) or []:
            if extra.get("url"):
                extra["url"] = canonical_url(extra["url"])


def do_dedupe(digest: dict, state: dict) -> list[dict]:
    seen_fp = {s["fingerprint"] for s in state["seen"]}
    seen_url = {s["url"] for s in state["seen"] if s.get("url")}
    kept, removed, batch_fp, batch_url = [], [], set(), set()
    for item in digest["items"]:
        fp, url = item.get("event_fingerprint"), (item.get("source") or {}).get("url")
        reason = None
        if fp in seen_fp:
            reason = "already reported (fingerprint)"
        elif url and url in seen_url:
            reason = "already reported (url)"
        elif fp in batch_fp or (url and url in batch_url):
            reason = "duplicate within this digest"
        if reason:
            removed.append({"headline": item.get("headline"), "competitor": item.get("competitor"), "reason": reason})
            continue
        batch_fp.add(fp)
        if url:
            batch_url.add(url)
        kept.append(item)
    digest["items"] = kept
    return removed


def rank_key(item: dict, cfg: dict):
    """Tier, then product priority, directness of competition, breadth, confidence, recency."""
    pub = item.get("published_at") or "1970-01-01"
    try:
        ts = -parse_time(pub).timestamp()
    except ValueError:
        ts = 0
    prods = [product_of(cfg, n) for n in item.get("our_products") or []]
    prio = min((PRIORITY.get(p["priority"], 1) for p in prods if p), default=1)
    ent = entity_of(cfg, item.get("competitor", ""))
    direct = ent["directness"] if ent else 5
    if ent and ent.get("priority") == "high":
        direct -= 0.5
    conf = {"high": 0, "medium": 1, "low": 2}.get(item.get("confidence"), 3)
    return (item.get("tier", 9), prio, direct, -len(prods), conf, ts)


def validate_digest(digest: dict, cfg: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    products = set(cfg["active_products"])
    competitors = {e["name"]: e for e in cfg["competitors"]}
    groups = set(cfg["active_groups"])
    excl = [n.lower() for n in cfg["global_exclusions"] if n]
    internal = set(excl) | {n.lower() for n in cfg["internal_names"]}
    cap = cfg["settings"]["max_items"]
    if len(digest["items"]) > cap:
        errors.append(f"{len(digest['items'])} items exceeds max_items={cap}; move the rest to suppressed")
    for i, item in enumerate(digest["items"], 1):
        tag = f"item {i} ({item.get('headline', '?')[:50]})"
        for f in ("event_key", "competitor", "category", "headline", "what_changed", "why_it_matters",
                  "published_at", "confidence", "tier", "our_products", "source"):
            if not item.get(f):
                errors.append(f"{tag}: missing {f}")
        if item.get("tier") not in (1, 2):
            errors.append(f"{tag}: tier must be 1 or 2 (tier 3 goes in suppressed counts)")
        if item.get("category") and item["category"] not in CATEGORIES:
            errors.append(f"{tag}: category '{item['category']}' not in {sorted(CATEGORIES)}")
        if item.get("confidence") and item["confidence"] not in CONFIDENCE:
            errors.append(f"{tag}: confidence must be high/medium/low")
        unknown = [p for p in item.get("our_products") or [] if p not in products]
        if unknown:
            errors.append(f"{tag}: our_products {unknown} are not active products in the watchlist")
        comp = item.get("competitor", "")
        if comp.lower() in internal:
            errors.append(f"{tag}: '{comp}' is one of ours (sibling, internal or global exclusion), not a competitor")
        ent = competitors.get(comp)
        if item.get("group_watch") and item["group_watch"] not in groups:
            errors.append(f"{tag}: group_watch '{item['group_watch']}' is not an active Group Watch")
        if comp and not ent and not item.get("group_watch") and comp.lower() not in internal:
            warnings.append(f"{tag}: competitor '{comp}' is not on the watchlist; add a suggestion")
        elif ent and not item.get("group_watch"):
            off_map = [p for p in item.get("our_products") or [] if p not in ent["affects"]]
            if off_map:
                warnings.append(f"{tag}: no {comp} matchup for {off_map}; confirm the impact or add a matchup suggestion")
        src = item.get("source") or {}
        for f in ("title", "publisher", "url"):
            if not src.get(f):
                errors.append(f"{tag}: source.{f} missing")
        if src.get("url") and not re.match(r"^https?://", src["url"]):
            errors.append(f"{tag}: source.url must be http(s)")
        if item.get("event_fingerprint") != fingerprint(item):
            errors.append(f"{tag}: event_fingerprint missing or stale; run prepare")
        if item.get("published_at"):
            try:
                parse_time(item["published_at"])
            except ValueError:
                errors.append(f"{tag}: published_at is not an ISO date")
        hit = [e for e in excl if e in src.get("url", "").lower()]
        if hit:
            warnings.append(f"{tag}: source URL matches exclusion {hit}; is this really competitor news?")
    return errors, warnings


# ---------------------------------------------------------------------- render

TIER_LABEL = {1: "Act now", 2: "Worth knowing"}


def fmt_date(value: str) -> str:
    try:
        return parse_time(value).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value or "")


def digest_sections(d: dict, cfg: dict) -> list[tuple[str, list[dict]]]:
    """Ordered (heading, items). By tier, or by our product so the report reads
    'what happened to your competitors, by product line'."""
    if cfg["settings"]["group_by"] != "product":
        return [(f"Tier {t} · {TIER_LABEL[t]}", [x for x in d["items"] if x["tier"] == t]) for t in (1, 2)]
    cross = [x for x in d["items"] if len(x["our_products"]) > 1 or x.get("group_watch")]
    out = [("Cross-portfolio", cross)]
    for p in cfg["active_products"]:
        out.append((p, [x for x in d["items"] if x not in cross and x["our_products"][0] == p]))
    return out


def item_tags(x: dict, cfg: dict) -> list[str]:
    tags = list(x["our_products"])
    if cfg["settings"]["group_by"] == "product":
        tags.insert(0, f"Tier {x['tier']} · {TIER_LABEL[x['tier']]}")
    if x.get("group_watch"):
        tags.append(f"Watch: {x['group_watch']}")
    return tags + [x["category"], f"{x['confidence']} confidence", fmt_date(x["published_at"])]


def render_markdown(d: dict, cfg: dict) -> str:
    st = cfg["settings"]
    lines = [f"# {st.get('company', 'Competitor')} competitor intel",
             f"_{fmt_date(d['window']['since'])} – {fmt_date(d['window']['until'])} · generated {fmt_date(d['generated_at'])}_", ""]
    if d.get("summary"):
        lines += [d["summary"], ""]
    if not d["items"]:
        lines += ["**No material competitor developments this period.**", ""]
    for heading, items in digest_sections(d, cfg):
        if not items:
            continue
        lines += [f"## {heading}", ""]
        for x in items:
            src = x["source"]
            mark = "🔴 " if x["tier"] == 1 else ""
            lines += [
                f"### {mark}{x['competitor']}: {x['headline']}",
                " · ".join(f"`{t}`" for t in item_tags(x, cfg)),
                "",
                f"**What changed.** {x['what_changed']}",
                "",
                f"**Why it matters.** {x['why_it_matters']}",
                "",
            ]
            if x.get("follow_up"):
                lines += [f"**Follow up.** {x['follow_up']}", ""]
            refs = [f"[{src['title']}]({src['url']}) — {src['publisher']}"]
            refs += [f"[{c.get('title', c['url'])}]({c['url']})" for c in x.get("corroboration") or [] if c.get("url")]
            lines += ["Sources: " + " · ".join(refs), ""]
    lines += render_footer_md(d)
    return "\n".join(lines).rstrip() + "\n"


def render_footer_md(d: dict) -> list[str]:
    out = []
    t3 = (d.get("suppressed") or {}).get("tier3_by_competitor") or {}
    if t3:
        out += ["## Noise suppressed", "", ", ".join(f"{k}: {v}" for k, v in sorted(t3.items())), ""]
    if d.get("coverage_gaps"):
        out += ["## Coverage gaps", ""] + [f"- {g.get('competitor')}: {g.get('reason')}" for g in d["coverage_gaps"]] + [""]
    if d.get("suggestions"):
        out += ["## Suggested watchlist changes", ""]
        out += [f"- {s.get('type')}: {s.get('value')} — {s.get('reason', '')}" for s in d["suggestions"]] + [""]
    return out


def render_chat(d: dict, cfg: dict) -> str:
    """Plain text that pastes cleanly into Slack, Teams, WhatsApp or email."""
    head = f"*{cfg['settings'].get('company', 'Competitor')} competitor intel* · {fmt_date(d['window']['until'])}"
    if not d["items"]:
        return head + "\nNo material competitor developments this period.\n"
    blocks = []
    for x in d["items"]:
        mark = "🔴 " if x["tier"] == 1 else ""
        blocks.append(f"{mark}*{', '.join(x['our_products'])}* · {x['competitor']}: {x['headline']}\n"
                      f"{x['why_it_matters']}\n{x['source']['url']}")
    out, dropped = head, 0
    for b in blocks:
        if len(out) + len(b) + 2 > CHAT_LIMIT - 60:
            dropped += 1
            continue
        out += "\n\n" + b
    if dropped:
        out += f"\n\n+{dropped} more in the full report."
    return out + "\n"


HTML_CSS = """
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#57534e;--card:#fff;--line:#e7e5e4;--t1:#b91c1c;--t2:#1d4ed8;--link:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#0c0a09;--fg:#f5f5f4;--muted:#a8a29e;--card:#1c1917;--line:#292524;--t1:#f87171;--t2:#93c5fd;--link:#93c5fd}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:32px 16px 64px}h1{font-size:1.6rem;margin:0 0 4px}
.meta{color:var(--muted);font-size:.9rem;margin-bottom:24px}h2{font-size:1rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:32px 0 12px}
article{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--t2);border-radius:10px;padding:16px 18px;margin:0 0 14px}
article.t1{border-left-color:var(--t1)}article h3{margin:0 0 6px;font-size:1.08rem}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}.tags span{font-size:.78rem;border:1px solid var(--line);border-radius:999px;padding:2px 8px;color:var(--muted)}
p{margin:6px 0}a{color:var(--link)}.src{font-size:.9rem;margin-top:10px}ul{padding-left:20px}
@media print{body{background:#fff;color:#000}article{break-inside:avoid}}
"""


def render_html(d: dict, cfg: dict) -> str:
    e = html.escape
    company = cfg["settings"].get("company", "Competitor")
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>{e(company)} Competitor Intel</title><style>{HTML_CSS}</style></head><body><main>",
             f"<h1>{e(company)} competitor intel</h1>",
             f"<div class='meta'>{e(fmt_date(d['window']['since']))} – {e(fmt_date(d['window']['until']))}"
             f" · generated {e(fmt_date(d['generated_at']))}</div>"]
    if d.get("summary"):
        parts.append(f"<p>{e(d['summary'])}</p>")
    if not d["items"]:
        parts.append("<p><strong>No material competitor developments this period.</strong></p>")
    for heading, items in digest_sections(d, cfg):
        if not items:
            continue
        parts.append(f"<h2>{e(heading)}</h2>")
        for x in items:
            src = x["source"]
            refs = [f"<a href='{e(src['url'])}' rel='noopener'>{e(src['title'])}</a> — {e(src['publisher'])}"]
            refs += [f"<a href='{e(c['url'])}' rel='noopener'>{e(c.get('title', c['url']))}</a>"
                     for c in x.get("corroboration") or [] if c.get("url")]
            parts.append(
                f"<article class='t{x['tier']}'><h3>{e(x['competitor'])}: {e(x['headline'])}</h3>"
                f"<div class='tags'>{''.join(f'<span>{e(t)}</span>' for t in item_tags(x, cfg))}</div>"
                f"<p><strong>What changed.</strong> {e(x['what_changed'])}</p>"
                f"<p><strong>Why it matters.</strong> {e(x['why_it_matters'])}</p>"
                + (f"<p><strong>Follow up.</strong> {e(x['follow_up'])}</p>" if x.get("follow_up") else "")
                + f"<div class='src'>Sources: {' · '.join(refs)}</div></article>")
    t3 = (d.get("suppressed") or {}).get("tier3_by_competitor") or {}
    if t3:
        parts.append("<h2>Noise suppressed</h2><p>" + e(", ".join(f"{k}: {v}" for k, v in sorted(t3.items()))) + "</p>")
    if d.get("coverage_gaps"):
        parts.append("<h2>Coverage gaps</h2><ul>" + "".join(
            f"<li>{e(str(g.get('competitor')))}: {e(str(g.get('reason')))}</li>" for g in d["coverage_gaps"]) + "</ul>")
    if d.get("suggestions"):
        parts.append("<h2>Suggested watchlist changes</h2><ul>" + "".join(
            f"<li>{e(str(s.get('type')))}: {e(str(s.get('value')))} — {e(str(s.get('reason', '')))}</li>"
            for s in d["suggestions"]) + "</ul>")
    parts.append("</main></body></html>")
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------- watchlist edits

def append_to_section(path: Path, section: str, lines: list[str]) -> None:
    """Append bullet lines to the end of a '## section' block, creating it if needed."""
    text = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, l in enumerate(text) if l.strip().lower() == f"## {section.lower()}"), None)
    if start is None:
        text += ["", f"## {section}", ""]
        start = len(text) - 2
    end = next((i for i in range(start + 1, len(text)) if text[i].startswith("## ")), len(text))
    insert_at = end
    while insert_at > start + 1 and not text[insert_at - 1].strip():
        insert_at -= 1
    text[insert_at:insert_at] = lines
    atomic_write(path, "\n".join(text).rstrip() + "\n")


# --------------------------------------------------------------------- commands

def cmd_init(args) -> int:
    wdir = watch_dir(args)
    if (wdir / "watchlist.md").exists() and not args.force:
        raise IntelError(f"{wdir / 'watchlist.md'} already exists (use --force to overwrite)")
    src = Path(args.from_file).expanduser() if args.from_file else TEMPLATE
    text = src.read_text(encoding="utf-8")
    if args.company:
        text = re.sub(r"^- company:.*$", f"- company: {args.company}", text, count=1, flags=re.M)
    text = re.sub(r"^- watch:.*$", f"- watch: {wdir.name}", text, count=1, flags=re.M)
    if not args.from_file:
        tz = system_timezone()
        text = re.sub(r"^- timezone:.*$", f"- timezone: {tz}", text, count=1, flags=re.M)
        today = local_today({"settings": {"timezone": tz}})
        text = re.sub(r"^- \d{4}-\d{2}-\d{2}: Created watchlist from template\.$",
                      f"- {today}: Created watchlist from template.", text, flags=re.M)
    atomic_write(wdir / "watchlist.md", text)
    if not (wdir / "state.json").exists() or args.force:
        write_json(wdir / "state.json", empty_state(wdir.name))
    (wdir / "runs").mkdir(exist_ok=True)
    print(json.dumps({"watch_dir": str(wdir), "watchlist": str(wdir / "watchlist.md"),
                      "state": str(wdir / "state.json")}, indent=2))
    return 0


def cmd_list(args) -> int:
    print(json.dumps({"home": str(home_dir()), "watches": list_watches()}, indent=2))
    return 0


def build_queries(cfg: dict, window: dict) -> list[dict]:
    """Starting query set. Matchup keywords carry product context; entity keywords catch
    brand-level news (funding, M&A) for every product the entity or its brands touch.

    Global exclusions are deliberately NOT negated in queries: '-"OurBrand"' would drop
    exactly the stories where a competitor wins a customer from us. They are applied
    when validating items instead. Only Noise Terms and per-row excludes are negated.
    """
    since = window["since_by_watch"]
    plan: dict[str, dict] = {}

    def add(key, kw, products, excludes, matchup=None, verify=None, noise=True):
        terms = [*excludes, *(cfg["noise_terms"] if noise else [])]
        neg = list(dict.fromkeys(unquote(x) for x in terms if x))[:MAX_NEGATIVES]
        q = " ".join([kw, *(f'-"{n}"' for n in neg)]).strip()
        row = plan.setdefault(q, {"watch": key, "query": q, "since": since[key], "products": [], "matchups": []})
        row["products"] = sorted(set(row["products"]) | set(products))
        if matchup:
            row["matchups"].append(matchup)
        if verify:
            row["verify"] = verify

    active = set(cfg["active_products"])
    for e in cfg["competitors"]:
        if e["status"] != "active":
            continue
        verify = e.get("verify") or ("Ambiguous name: confirm the article is about this company"
                                     if e["ambiguous"] else None)
        for p in cfg["products"]:
            if p["name"] not in active:
                continue
            for m in p["matchups"]:
                if m["competitor"] != e["name"] or m["type"] == "internal":
                    continue
                label = f"{p['name']} vs {e['name']} ({m['type']})"
                for kw in m["keywords"]:
                    add(e["name"], kw, [p["name"]], [*e["exclude"], *m["exclude"]], label, verify)
        for kw in e["keywords"]:
            add(e["name"], kw, e["affects"], e["exclude"], None, verify)
        if e.get("domain"):
            add(e["name"], f"site:{e['domain']} news OR announces OR launches", e["affects"], [], noise=False)
    for g in cfg["group_watches"]:
        if g["status"] == "active":
            for kw in g["keywords"]:
                add(GROUP_PREFIX + g["name"], kw, g["affects"], g["exclude"])
    for term in cfg["market_watches"]:
        add(MARKET_KEY, term, [], [])
    return list(plan.values())


def cmd_config(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    if args.plan:
        window = plan_window(cfg, load_state(wdir), now_utc())
        cfg["window"] = window
        cfg["queries"] = build_queries(cfg, window)
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    return 1 if cfg["errors"] else 0


def cmd_prepare(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    state = load_state(wdir)
    path = Path(args.input)
    digest = load_digest(path)
    digest.setdefault("watch", wdir.name)
    digest.setdefault("generated_at", iso(now_utc()))
    digest.setdefault("window", plan_window(cfg, state, now_utc()))
    do_fingerprint(digest)
    removed = do_dedupe(digest, state)
    digest["items"].sort(key=lambda x: rank_key(x, cfg))
    if removed:
        digest.setdefault("suppressed", {}).setdefault("already_seen", []).extend(removed)
    write_json(path, digest)
    errors, warnings = validate_digest(digest, cfg)
    print(json.dumps({"items": len(digest["items"]), "removed": removed,
                      "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
    return 1 if errors else 0


def cmd_validate(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    digest = load_digest(Path(args.input))
    errors, warnings = validate_digest(digest, cfg)
    print(json.dumps({"items": len(digest["items"]), "errors": errors, "warnings": warnings}, indent=2))
    return 1 if errors else 0


def cmd_render(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    digest = load_digest(Path(args.input))
    errors, _ = validate_digest(digest, cfg)
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 1
    out = Path(args.out) if args.out else wdir / "runs" / run_id(digest)
    out.mkdir(parents=True, exist_ok=True)
    outputs = cfg["settings"]["outputs"]
    files = {"digest.json": json.dumps(digest, indent=2, ensure_ascii=False) + "\n"}
    if "markdown" in outputs:
        files["digest.md"] = render_markdown(digest, cfg)
    if "html" in outputs:
        files["index.html"] = render_html(digest, cfg)
    if "chat" in outputs:
        files["chat.txt"] = render_chat(digest, cfg)
    for name, body in files.items():
        atomic_write(out / name, body)
    manifest = {"run_id": run_id(digest), "out_dir": str(out), "files": sorted(files),
                "event_fingerprints": [x["event_fingerprint"] for x in digest["items"]],
                "quiet": not digest["items"]}
    write_json(out / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


def run_id(digest: dict) -> str:
    return parse_time(digest["generated_at"]).strftime("%Y-%m-%d-%H%M")


def cmd_commit(args) -> int:
    """Record a successful run. Only call after research and delivery both succeeded."""
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    state = load_state(wdir)
    digest = load_digest(Path(args.input))
    errors, _ = validate_digest(digest, cfg)
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 1
    rid = run_id(digest)
    if any(r["run_id"] == rid for r in state["runs"]) and not args.force:
        print(json.dumps({"status": "already committed", "run_id": rid}))
        return 0
    now = now_utc()
    until = digest["window"]["until"]
    gaps = {g.get("competitor") for g in digest.get("coverage_gaps") or []}
    for key in cfg["watch_keys"]:
        if key not in gaps:
            state["cutoffs"][key] = until
    for x in digest["items"]:
        state["seen"].append({"fingerprint": x["event_fingerprint"], "url": x["source"]["url"],
                              "event_key": x["event_key"], "competitor": x["competitor"],
                              "tier": x["tier"], "headline": x["headline"], "first_seen": iso(now), "run_id": rid})
    horizon = now - dt.timedelta(days=cfg["settings"]["seen_window_days"])
    state["seen"] = [s for s in state["seen"] if parse_time(s["first_seen"]) >= horizon]
    t3 = (digest.get("suppressed") or {}).get("tier3_by_competitor") or {}
    if t3:
        state["tier3"].append({"run_id": rid, "counts": t3})
    state["tier3"] = state["tier3"][-26:]
    state["runs"].append({"run_id": rid, "committed_at": iso(now), "window": digest["window"],
                          "items": len(digest["items"]), "coverage_gaps": sorted(g for g in gaps if g),
                          "delivered_to": args.delivered_to or cfg["settings"].get("deliver_to")})
    state["runs"] = state["runs"][-104:]
    write_json(wdir / "state.json", state)

    existing = {s.lower() for s in cfg["suggestions"]}
    new = []
    for s in digest.get("suggestions") or []:
        line = f"{s.get('type', 'note')}: {s.get('value', '')} — {s.get('reason', '')} ({local_today(cfg)})"
        if not any(str(s.get("value", "")).lower() in e for e in existing):
            new.append(f"- {line}")
    if new:
        append_to_section(wdir / "watchlist.md", "Suggestions", new)
    print(json.dumps({"status": "committed", "run_id": rid, "seen_total": len(state["seen"]),
                      "suggestions_added": len(new), "cutoff_held_for": sorted(g for g in gaps if g)}, indent=2))
    return 0


def cmd_log(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    append_to_section(wdir / "watchlist.md", "Change Log", [f"- {local_today(cfg)}: {args.message}"])
    print(json.dumps({"logged": args.message}))
    return 0


def cmd_status(args) -> int:
    wdir = watch_dir(args)
    cfg = load_config(wdir)
    state = load_state(wdir)
    last = state["runs"][-1] if state["runs"] else None
    t3_total: dict[str, int] = {}
    for r in state["tier3"][-4:]:
        for k, v in r["counts"].items():
            t3_total[k] = t3_total.get(k, 0) + int(v)
    print(json.dumps({
        "watch_dir": str(wdir), "company": cfg["settings"].get("company"),
        "cadence": cfg["settings"]["cadence"],
        "active_products": cfg["active_products"], "active_competitors": cfg["active_competitors"],
        "market_watches": len(cfg["market_watches"]), "pending_suggestions": len(cfg["suggestions"]),
        "last_run": last, "runs_total": len(state["runs"]), "seen_events": len(state["seen"]),
        "tier3_last_4_runs": t3_total, "config_errors": cfg["errors"], "config_warnings": cfg["warnings"],
    }, indent=2, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="intel.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--watch", help="watch slug under $COMPETITOR_INTEL_HOME")
        sp.add_argument("--dir", help="explicit watch directory (overrides --watch)")
        sp.set_defaults(fn=fn)
        return sp

    sp = add("init", cmd_init, "create a watch folder from the template")
    sp.add_argument("--company")
    sp.add_argument("--from", dest="from_file", help="start from an existing watchlist.md")
    sp.add_argument("--force", action="store_true")
    sub.add_parser("list", help="list watches").set_defaults(fn=cmd_list)
    sp = add("config", cmd_config, "parse and validate watchlist.md")
    sp.add_argument("--plan", action="store_true", help="include search window and query plan")
    for name, fn, help_ in (("prepare", cmd_prepare, "fingerprint, dedupe, rank and validate a digest"),
                            ("validate", cmd_validate, "validate a digest without changing it")):
        add(name, fn, help_).add_argument("--input", required=True)
    sp = add("render", cmd_render, "render markdown, html and chat outputs")
    sp.add_argument("--input", required=True)
    sp.add_argument("--out", help="output dir (default <watch>/runs/<run-id>)")
    sp = add("commit", cmd_commit, "record a delivered run in state.json")
    sp.add_argument("--input", required=True)
    sp.add_argument("--delivered-to")
    sp.add_argument("--force", action="store_true")
    sp = add("log", cmd_log, "append a line to the watchlist change log")
    sp.add_argument("message")
    add("status", cmd_status, "summarise a watch")

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except IntelError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
