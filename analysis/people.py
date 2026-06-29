"""
Step 4 (add-on) - People rankings per category, by user_id (anonymized).

Produces:
  - output/top_creators_by_category.csv : top 20 marker creators in each category
  - output/top_likers_by_category.csv   : top 50 likers in each category

A like is attributed to the category of the marker it was placed on. Users are
identified by their numeric `user_id` only -- no names are emitted, so these
files are safe to publish. (The raw survey export does carry {first_name,
last_name,id} objects, but we deliberately do not join them in.)
"""
import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw", "pretty.json")
OUT = os.path.join(ROOT, "output")
QUESTION_ID = 11865
CAT_LABEL = {1: "Appreciated", 2: "Needs improvement", 3: "Missing path", 4: "To be removed"}


def main():
    with open(RAW, encoding="utf-16") as f:
        doc = json.load(f)
    markers = next(q for q in doc["data"] if q["id"] == QUESTION_ID)["mapMarkers"]

    # Per-category counters.
    creators = {c: Counter() for c in CAT_LABEL}
    likers = {c: Counter() for c in CAT_LABEL}
    for m in markers:
        c = m["marker_category"]
        if c not in creators:
            continue
        creators[c][m["user_id"]] += 1
        for like in m.get("likes", []):
            likers[c][like["user_id"]] += 1

    # Write creators (top 20 per category).
    with open(os.path.join(OUT, "top_creators_by_category.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "rank", "user_id", "markers_created"])
        for c in CAT_LABEL:
            for rank, (uid, n) in enumerate(creators[c].most_common(20), 1):
                w.writerow([CAT_LABEL[c], rank, uid, n])

    # Write likers (top 50 per category).
    with open(os.path.join(OUT, "top_likers_by_category.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "rank", "user_id", "likes_given"])
        for c in CAT_LABEL:
            for rank, (uid, n) in enumerate(likers[c].most_common(50), 1):
                w.writerow([CAT_LABEL[c], rank, uid, n])

    # Console summary: top 5 of each.
    for c in CAT_LABEL:
        print(f"\n[{CAT_LABEL[c]}] top creators:")
        for uid, n in creators[c].most_common(5):
            print(f"   {n:3d}  user {uid}")
        print(f"[{CAT_LABEL[c]}] top likers:")
        for uid, n in likers[c].most_common(5):
            print(f"   {n:3d}  user {uid}")
    print("\nWrote top_creators_by_category.csv and top_likers_by_category.csv (user_id only)")


if __name__ == "__main__":
    main()
