import csv
import random

import numpy as np

from cluster import embed, recent_articles

random.seed(42)
pool = recent_articles(hours=24 * 14)
vectors = embed(pool)
sim = vectors @ vectors.T
src = np.array([a["source"] for a in pool])

mask = np.triu(sim > 0.35, k=1) & (src[:, None] != src[None, :])
pairs = np.argwhere(mask).tolist()
random.shuffle(pairs)

with open("evaluation/pairs_to_label.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url_a", "url_b", "source_a", "title_a", "source_b", "title_b", "similarity", "label"])
    for i, j in pairs[:120]:
        a, b = pool[i], pool[j]
        w.writerow([a["url"], b["url"], a["source"], a["title"], b["source"], b["title"],
                    round(float(sim[i, j]), 3), ""])
print(f"{min(len(pairs), 120)} pairs written (from {len(pairs)} candidates)")