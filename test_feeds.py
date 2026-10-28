import feedparser
from feeds import FEEDS

for name, url in FEEDS.items():
    d = feedparser.parse(url, agent="geo-event-compare/0.1 (student project)")
    n = len(d.entries)
    print(("OK  " if n else "FAIL"), f"{name:15s} {n:3d} entries")
    if n:
        print("     ", d.entries[0].get("title", "")[:80])