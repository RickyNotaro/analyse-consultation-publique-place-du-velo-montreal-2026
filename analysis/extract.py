"""
Step 1 - Extract & flatten the map markers from question 11865.

Reads raw/pretty.json (UTF-16 encoded), pulls the `mapMarkers` array of the
interactive map question (id 11865), and writes a tidy one-row-per-marker CSV
to output/markers.csv. This CSV is the single source of truth for every later
analysis step.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw", "pretty.json")
OUT_DIR = os.path.join(ROOT, "output")
OUT_CSV = os.path.join(OUT_DIR, "markers.csv")

QUESTION_ID = 11865

# Category id -> English label and the colour the consultation tool used.
CATEGORIES = {
    1: ("Appreciated bike path", "green"),
    2: ("Bike path needing improvement or adjustment", "yellow"),
    3: ("Missing bike path", "magenta"),
    4: ("Bike path to be removed", "red"),
}


def load_markers():
    # The file is UTF-16 (BOM 0xff 0xfe), NOT utf-8.
    with open(RAW, encoding="utf-16") as f:
        doc = json.load(f)
    question = next(q for q in doc["data"] if q["id"] == QUESTION_ID)
    return question["mapMarkers"]


def flatten(markers):
    rows = []
    for i, m in enumerate(markers):
        loc = m.get("marker_location") or [None, None]
        lon, lat = (loc + [None, None])[:2]
        text = (m.get("marker_text") or "").strip()
        likes = m.get("likes") or []
        liker_ids = ";".join(str(l.get("user_id")) for l in likes if l.get("user_id") is not None)
        cat_id = m.get("marker_category")
        cat_en = CATEGORIES.get(cat_id, ("Unknown", "gray"))[0]
        rows.append({
            "marker_index": i,
            "user_id": m.get("user_id"),
            "comment_id": m.get("comment_id"),
            "category_id": cat_id,
            "category_en": cat_en,
            "lon": lon,
            "lat": lat,
            "marker_text": text,
            "text_len": len(text),
            "num_likes": len(likes),
            "liker_ids": liker_ids,
        })
    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    markers = load_markers()
    rows = flatten(markers)
    fields = ["marker_index", "user_id", "comment_id", "category_id", "category_en",
              "lon", "lat", "marker_text", "text_len", "num_likes", "liker_ids"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Sanity check printed to console.
    from collections import Counter
    cat_counts = Counter(r["category_id"] for r in rows)
    total_likes = sum(r["num_likes"] for r in rows)
    authors = len({r["user_id"] for r in rows})
    print(f"Wrote {len(rows)} markers -> {OUT_CSV}")
    print("Category counts:", dict(sorted(cat_counts.items())))
    print(f"Total likes: {total_likes} | Unique authors: {authors}")


if __name__ == "__main__":
    main()
