import csv
import json

from db import get_conn

conn = get_conn()
rows = conn.execute("SELECT payload FROM events ORDER BY created_at DESC LIMIT 40").fetchall()
with open("evaluation/faithfulness_to_review.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["event_title", "kind", "claim", "cited_text", "verdict"])
    for r in rows:
        p = json.loads(r["payload"])
        a = p["analysis"]
        if not a["same_event"]:
            continue
        by_n = {x["n"]: x for x in p["articles"]}
        items = [("summary", a["summary"], list(by_n))]
        items += [("fact", c["claim"], c["sources"]) for c in a["agreed_facts"]]
        for kind, text, nums in items:
            cited = " || ".join(f"[{by_n[n]['source']}] {by_n[n]['title']}. {by_n[n]['snippet']}"
                                for n in nums if n in by_n)
            w.writerow([a["event_title"], kind, text, cited, ""])