import numpy as np
import hashlib
from datetime import datetime, timedelta, timezone

from sklearn.cluster import AgglomerativeClustering
from sentence_transformers import SentenceTransformer

from config import MIN_SOURCES, SIMILARITY_DISTANCE, WINDOW_HOURS
from db import get_conn

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

TOPIC_ANCHORS = [
    "war, military strikes, ceasefire and armed conflict between countries",
    "diplomacy, summit, treaty and talks between governments",
    "sanctions, tariffs and international trade disputes",
    "elections, government and political leadership of a country",
    "terrorism, security threats, espionage and defence",
    "energy supply, oil, gas and geopolitical tensions",
    "refugees, humanitarian crisis and international aid",
]
_anchors = None

def get_anchors():
    global _anchors
    if _anchors is None:
        _anchors = get_model().encode(TOPIC_ANCHORS, normalize_embeddings=True)
    return _anchors

def recent_articles(hours=WINDOW_HOURS):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE COALESCE(published, fetched_at) >= ? "
            "ORDER BY COALESCE(published, fetched_at) DESC", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]

def embed(articles):
    texts = [f"{a['title']}. {a['snippet'] or ''}" for a in articles]
    return get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)

def cluster_articles(articles, distance=SIMILARITY_DISTANCE, min_topic=None):
    from config import MIN_TOPIC_SCORE
    min_topic = MIN_TOPIC_SCORE if min_topic is None else min_topic
    if len(articles) < 2:
        return []
    vectors = embed(articles)
    labels = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average", distance_threshold=distance
    ).fit_predict(vectors)
    members = {}
    for idx, label in enumerate(labels):
        members.setdefault(label, []).append(idx)

    events = []
    for idxs in members.values():
        group = [articles[i] for i in idxs]
        if len({a["source"] for a in group}) < MIN_SOURCES:
            continue
        centroid = vectors[idxs].mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        score = float((get_anchors() @ centroid).max())
        if score < min_topic:
            continue
        for a in group:
            a["_topic"] = round(score, 3)
        events.append(group)
    events.sort(key=lambda g: len({a["source"] for a in g}), reverse=True)
    return events

def event_key(group):
    urls = sorted(a["url"] for a in group)
    return hashlib.sha256("|".join(urls).encode()).hexdigest()[:16]