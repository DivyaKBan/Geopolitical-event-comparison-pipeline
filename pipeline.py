import json
import time
from datetime import datetime, timedelta, timezone

from analyze import analyze, clean_analysis, pick_articles
from cluster import cluster_articles, event_key, recent_articles
from collect import collect
from config import KEEP_DAYS, MAX_EVENTS_PER_RUN
from db import get_conn, init_db

def run():
    started = datetime.now(timezone.utc).isoformat()
    init_db()
    ok, failed_feeds, new = collect()
    if ok == 0:
        raise SystemExit("All feeds failed. Stopping so the problem is visible.")

    articles = recent_articles()
    groups = cluster_articles(articles)
    print(f"{len(articles)} recent articles -> {len(groups)} multi-outlet clusters")

    now = datetime.now(timezone.utc).isoformat()
    analyzed = cached = failed = 0
    conn = get_conn()
    for group in groups[:MAX_EVENTS_PER_RUN]:
        key = event_key(group)
        if conn.execute("SELECT 1 FROM events WHERE event_key=?", (key,)).fetchone():
            conn.execute("UPDATE events SET last_seen=? WHERE event_key=?", (now, key))
            conn.commit()
            cached += 1
            continue
        picked = pick_articles(group)
        result = analyze(picked)
        if result is None:
            failed += 1
            continue
        result, dropped = clean_analysis(result, len(picked))
        payload = {
            "analysis": result.model_dump(),
            "dropped_claims": dropped,
            "articles": [
                {"n": i, "source": a["source"], "title": a["title"], "snippet": a["snippet"],
                 "url": a["url"], "published": a["published"]}
                for i, a in enumerate(picked, start=1)
            ],
        }
        conn.execute(
            "INSERT INTO events (event_key, created_at, last_seen, payload) VALUES (?,?,?,?)",
            (key, now, now, json.dumps(payload)),
        )
        conn.commit()
        analyzed += 1
        print(f"  analyzed: {result.event_title}")
        time.sleep(2)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    conn.execute("DELETE FROM events WHERE last_seen < ?", (cutoff,))
    conn.execute(
        "INSERT INTO runs (started_at, finished_at, feeds_ok, feeds_failed, new_articles, "
        "clusters, analyzed, cached, failed) VALUES (?,?,?,?,?,?,?,?,?)",
        (started, datetime.now(timezone.utc).isoformat(), ok, failed_feeds, new,
         len(groups), analyzed, cached, failed),
    )
    conn.commit()
    conn.close()

    vac = get_conn()                 # shrink the file so it stays small in git
    vac.isolation_level = None
    vac.execute("VACUUM")
    vac.close()
    print(f"Done. analyzed={analyzed} cached={cached} failed={failed}")

if __name__ == "__main__":
    run()