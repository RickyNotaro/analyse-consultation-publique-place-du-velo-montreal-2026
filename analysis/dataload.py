"""
Shared loader for the map markers of question 11865.

Two source formats have been received from the consultation platform, and this
module reads both transparently so the rest of the pipeline sees one shape:

  - legacy  raw/pretty.json         : UTF-16 (BOM ff fe), native JSON types,
                                       accented text lost to an upstream
                                       transcode ("??"), early June extract.
  - current raw/forms-YYYY-MM-DD.json: UTF-8, every value stored as a *string*
                                       (marker_location is a JSON string,
                                       marker_category / user_id / comment_id are
                                       strings), clean accents.

`load_markers()` picks the newest dated export by default, sniffs the encoding
from the BOM, and coerces the marker fields the pipeline uses to native types
(ints and a [lon, lat] float list) so downstream code needs no per-format branch.
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "raw")

QUESTION_ID = 11865


def default_source():
    """Newest raw/forms-*.json if any, else the legacy raw/pretty.json."""
    forms = sorted(glob.glob(os.path.join(RAW_DIR, "forms-*.json")))
    if forms:
        return forms[-1]
    return os.path.join(RAW_DIR, "pretty.json")


def _read_json(path):
    # UTF-16 files start with the BOM ff fe; everything else is treated as UTF-8
    # (utf-8-sig also strips a UTF-8 BOM if one is present).
    with open(path, "rb") as f:
        head = f.read(2)
    encoding = "utf-16" if head == b"\xff\xfe" else "utf-8-sig"
    with open(path, encoding=encoding) as f:
        return json.load(f)


def _as_int(v):
    if v is None or v == "":
        return None
    return int(v)


def _as_location(v):
    """Return [lon, lat] as floats. Accepts a native list or a JSON string."""
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return [None, None]
        v = json.loads(v)
    if not isinstance(v, list) or len(v) < 2:
        return [None, None]
    return [v[0], v[1]]


def load_markers(path=None):
    """Return the list of question-11865 markers with native-typed fields."""
    path = path or default_source()
    doc = _read_json(path)
    question = next(q for q in doc["data"] if str(q.get("id")) == str(QUESTION_ID))
    markers = question["mapMarkers"]
    for m in markers:
        m["marker_category"] = _as_int(m.get("marker_category"))
        m["user_id"] = _as_int(m.get("user_id"))
        m["comment_id"] = _as_int(m.get("comment_id"))
        m["marker_location"] = _as_location(m.get("marker_location"))
        likes = m.get("likes") or []
        for lk in likes:
            lk["user_id"] = _as_int(lk.get("user_id"))
        m["likes"] = likes
    return markers
