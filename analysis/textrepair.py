"""
Text passthrough for marker comments (kept as a stable hook in the pipeline).

Historically the source arrived as a UTF-16 export whose French accents had been
destroyed by a lossy upstream transcode (every accented letter became "??", most
apostrophes "???"), and this module repaired them on a best-effort basis.

The current export (raw/forms-*.json) is clean UTF-8 with intact accents, so no
repair is needed -- and the old "??"->"e" rule would now *corrupt* legitimate
punctuation (e.g. "the path just ends??" -> "...endse"). `repair_text` is
therefore an identity function today. It is kept so callers (analyze.py,
build_map.py) need no change and so repair can be reinstated if a corrupted
legacy export is ever reprocessed (the mapping lives in this file's git history).
"""


def repair_text(s):
    return s
