import csv

from sklearn.cluster import AgglomerativeClustering

from cluster import embed, recent_articles

rows = [r for r in csv.DictReader(open("evaluation/pairs_to_label.csv", encoding="utf-8"))
        if r["label"].strip() in ("0", "1")]
pool = recent_articles(hours=24 * 14)
index = {a["url"]: i for i, a in enumerate(pool)}
vectors = embed(pool)
gold = [(index[r["url_a"]], index[r["url_b"]], int(r["label"]))
        for r in rows if r["url_a"] in index and r["url_b"] in index]
print(f"{len(gold)} labelled pairs, {sum(y for *_, y in gold)} positives\n")
print("threshold  precision  recall   F1")

for t in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    labels = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average", distance_threshold=t
    ).fit_predict(vectors)
    tp = fp = fn = 0
    for i, j, y in gold:
        same = labels[i] == labels[j]
        tp += same and y == 1
        fp += same and y == 0
        fn += (not same) and y == 1
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    print(f"{t:8.2f}  {p:9.2f}  {r:6.2f}  {f1:5.2f}")