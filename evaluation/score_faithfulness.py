import csv
from collections import Counter

PATH = "evaluation/faithfulness_to_review.csv"
rows = list(csv.DictReader(open(PATH, encoding="utf-8-sig")))
print(f"{len(rows)} rows in file")

valid = {"yes", "partly", "no"}
labelled = [r for r in rows if r["verdict"].strip().lower() in valid]
print(f"{len(labelled)} rows have a verdict")

if not labelled:
    raise SystemExit(
        "No verdicts found. Open the CSV, fill the 'verdict' column with yes / partly / no, "
        "save it as CSV (not .xlsx), close Excel, and run this again."
    )

c = Counter(r["verdict"].strip().lower() for r in labelled)
total = len(labelled)
print(dict(c))
print(f"Fully supported: {c['yes']}/{total} ({100 * c['yes'] / total:.0f}%)")
print(f"Fully or partly supported: {c['yes'] + c['partly']}/{total} "
      f"({100 * (c['yes'] + c['partly']) / total:.0f}%)")