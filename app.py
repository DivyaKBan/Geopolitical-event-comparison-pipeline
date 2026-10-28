import json
import sqlite3

import streamlit as st

DB = "data/events.db"

st.set_page_config(page_title="Same Event, Different Reports", layout="wide")
st.title("Same event, different reports")
st.caption("Groups reports from several outlets about the same event and shows where they agree "
           "and where they differ. Built from headlines and short snippets. It is a reading aid, "
           "not analysis or advice. Always read the original articles.")

@st.cache_data(ttl=600)
def load():
    try:
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT payload, last_seen FROM events ORDER BY last_seen DESC").fetchall()
        last_run = conn.execute("SELECT MAX(finished_at) FROM runs").fetchone()[0]
        conn.close()
    except sqlite3.Error:
        return [], None
    events = []
    for payload, last_seen in rows:
        p = json.loads(payload)
        if p["analysis"]["same_event"]:
            p["last_seen"] = last_seen
            events.append(p)
    return events, last_run

events, last_run = load()
if not events:
    st.info("No events yet. Run the pipeline first.")
    st.stop()

latest_day = max(e["last_seen"][:10] for e in events)
if not st.sidebar.checkbox("Include earlier days", value=False):
    events = [e for e in events if e["last_seen"][:10] == latest_day]

types = sorted({e["analysis"]["event_type"] for e in events})
countries = sorted({c for e in events for c in e["analysis"]["countries"]})
sel_type = st.sidebar.selectbox("Event type", ["All"] + types)
sel_countries = st.sidebar.multiselect("Country", countries)

if sel_type != "All":
    events = [e for e in events if e["analysis"]["event_type"] == sel_type]
if sel_countries:
    events = [e for e in events if set(sel_countries) & set(e["analysis"]["countries"])]

st.caption(f"Last updated: {last_run} UTC. Showing {len(events)} events.")

for e in events:
    a = e["analysis"]
    outlets = {x["source"] for x in e["articles"]}
    by_n = {x["n"]: x for x in e["articles"]}
    with st.expander(f"{a['event_title']}  ·  {len(outlets)} outlets"):
        st.write(a["summary"])
        st.caption(f"Type: {a['event_type']}  |  Countries: {', '.join(a['countries'])}")
        if a["agreed_facts"]:
            st.markdown("**What the reports agree on**")
            for c in a["agreed_facts"]:
                who = ", ".join(by_n[n]["source"] for n in c["sources"] if n in by_n)
                st.markdown(f"- {c['claim']} *({who})*")
        if a["differences"]:
            st.markdown("**Where they differ**")
            for d in a["differences"]:
                st.markdown(f"- **{d['topic']}**")
                for v in d["views"]:
                    if v["source"] in by_n:
                        st.markdown(f"  - {by_n[v['source']]['source']}: {v['says']}")
        st.markdown("**Sources**")
        for x in e["articles"]:
            st.markdown(f"- [{x['source']}: {x['title']}]({x['url']})")