#!/usr/bin/env python3
"""Gathers current-affairs headlines from RSS feeds, optionally enriches them with
Claude (exam notes), and merges into affairs.json. Stdlib only."""
import json, os, re, sys, html, hashlib, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

OUT = os.path.join(os.path.dirname(__file__), "affairs.json")
FEEDS = [
 ("The Hindu – Andhra Pradesh", "https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss"),
 ("The Hindu – National", "https://www.thehindu.com/news/national/feeder/default.rss"),
 ("PIB", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"),
 ("Google News – Andhra Pradesh", "https://news.google.com/rss/search?q=Andhra+Pradesh+government+OR+APPSC+when:2d&hl=en-IN&gl=IN&ceid=IN:en"),
 ("Google News – India policy", "https://news.google.com/rss/search?q=India+Union+Cabinet+OR+Supreme+Court+OR+RBI+OR+ISRO+when:2d&hl=en-IN&gl=IN&ceid=IN:en"),
]
CATS = ["Andhra Pradesh","National / Polity","Economy","Science & Tech","International","Environment","Schemes & Governance","Awards & Sports","Security"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_ENRICH = int(os.environ.get("MAX_ENRICH", "10"))
MAX_AGE_DAYS = 3

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (appsc-current-affairs bot)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()

def clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

def parse(xml_bytes, src):
    out = []
    for it in ET.fromstring(xml_bytes).iter("item"):
        title, link = clean(it.findtext("title")), (it.findtext("link") or "").strip()
        try:
            d = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
        except Exception:
            d = datetime.now(timezone.utc)
        if not title or not link.startswith("https://"):
            continue
        s = clean(it.findtext("description"))
        if s.lower().startswith(title.lower()[:40]):
            s = ""
        out.append({"id": "n-" + hashlib.sha1(link.encode()).hexdigest()[:10], "date": d.strftime("%Y-%m-%d"),
                    "ts": d.isoformat(), "cat": "Andhra Pradesh" if "Andhra" in src else "National / Polity",
                    "title": title, "sum": s[:300] or title, "bg": [], "rel": [], "ex": [], "mcq": [],
                    "src": src, "link": link, "enriched": False, "ai": False})
    return out

def enrich(item, key):
    prompt = ("You prepare notes for APPSC Group 1 and Group 2 (Andhra Pradesh) aspirants. News headline: %r. Snippet: %r. "
      "Reply with ONLY a JSON object: {\"relevant\": bool (false for sports scores, crime, gossip, local trivia with no exam value), "
      "\"cat\": one of %s, \"sum\": 2-3 neutral sentences, \"bg\": 3-4 key background facts, \"rel\": 2-3 earlier related events/laws/schemes, "
      "\"ex\": [\"Prelims: ...\", \"Mains: ...\"], \"mcq\": [[question, answer], [question, answer]]}. "
      "Use only facts you are confident about; do not invent numbers.") % (item["title"], item["sum"], CATS)
    body = json.dumps({"model": MODEL, "max_tokens": 900, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {"content-type": "application/json",
            "x-api-key": key, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = json.load(r)["content"][0]["text"]
    d = json.loads(text[text.index("{"): text.rindex("}") + 1])
    if not d.get("relevant", True):
        return None
    for k in ("sum", "bg", "rel", "ex", "mcq"):
        if d.get(k): item[k] = d[k]
    if d.get("cat") in CATS: item["cat"] = d["cat"]
    item["enriched"], item["ai"] = True, True
    return item

def main():
    data = {"items": [], "seen": []}
    if os.path.exists(OUT):
        data = json.load(open(OUT, encoding="utf-8"))
    seen, items = set(data.get("seen", [])), data["items"]
    have = {i["id"] for i in items} | {re.sub(r"\W", "", i["title"].lower()) for i in items}
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    fresh = []
    feeds = [("Fixture", None)] if "--fixture" in sys.argv else FEEDS
    for src, url in feeds:
        try:
            raw = open(sys.argv[sys.argv.index("--fixture") + 1], "rb").read() if url is None else get(url)
            fresh += parse(raw, src)
            print("ok", src)
        except Exception as e:
            print("feed failed", src, e)
    key, added, calls = os.environ.get("ANTHROPIC_API_KEY"), 0, 0
    for it in sorted(fresh, key=lambda x: x["ts"], reverse=True):
        norm = re.sub(r"\W", "", it["title"].lower())
        if it["id"] in seen or it["id"] in have or norm in have or datetime.fromisoformat(it["ts"]) < cutoff:
            continue
        if key:
            if calls >= MAX_ENRICH: continue
            calls += 1
            try:
                it = enrich(it, key)
            except Exception as e:
                print("enrich failed", e); continue
            if it is None:
                seen.add(norm); continue
        items.append(it); have.update({it["id"], norm}); seen.add(it["id"]); added += 1
    items.sort(key=lambda x: (x["date"], x.get("ts", "")), reverse=True)
    data = {"updated": datetime.now(timezone.utc).isoformat(), "seen": sorted(seen)[-4000:], "items": items}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=0))
    print("added", added, "total", len(items))

if __name__ == "__main__":
    main()
