import calendar
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser

from config import KEEP_DAYS
from db import get_conn, init_db
from feeds import FEEDS

AGENT = "geo-event-compare/0.1 (student project)"

def clean(text, limit=300):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return " ".join(text.split())[:limit]

def to_iso(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc).isoformat()

def collect():
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    ok = failed = new = 0
    with get_conn() as conn:
        for source, url in FEEDS.items():
            feed = feedparser.parse(url, agent=AGENT)
            if not feed.entries:
                failed += 1
                print(f"FAILED feed: {source}")
                continue
            ok += 1
            for e in feed.entries:
                link, title = e.get("link"), clean(e.get("title"))
                if not link or not title:
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO articles "
                    "(url, source, title, snippet, published, fetched_at) VALUES (?,?,?,?,?,?)",
                    (link, source, title, clean(e.get("summary")), to_iso(e), now),
                )
                new += cur.rowcount
        cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
        conn.execute("DELETE FROM articles WHERE COALESCE(published, fetched_at) < ?", (cutoff,))
    print(f"Feeds ok: {ok}, failed: {failed}, new articles: {new}")
    return ok, failed, new

if __name__ == "__main__":
    collect()