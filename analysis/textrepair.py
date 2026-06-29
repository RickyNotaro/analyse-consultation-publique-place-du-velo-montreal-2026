"""
Best-effort repair of corrupted accents in the source data.

The source pretty.json arrived with French accents already destroyed (lossy
transcoding before we received it): every accented letter became "??" and most
apostrophes became "???". This is irreversible from the data alone, but the
underlying words are recognizable, so we repair on a best-effort basis for
readability of charts, themes and map popups.

Rules, applied in order:
  1. A dictionary of the most common corrupted words -> correct French.
  2. "???" -> "'"  (corrupted apostrophe).
  3. "??"  -> "e"  (corrupted accent; e/é/è/ê are by far the most common).

This is cosmetic only. Counts, likes, coordinates and categories are unaffected.
"""
import re

# High-frequency corrupted words whose accent is NOT a plain e->e case, or that
# are common enough to be worth pinning precisely. Keys are lowercase corrupted
# forms; values are the correct French spelling.
REPAIR = {
    "tr??s": "très", "v??lo": "vélo", "v??los": "vélos", "??tre": "être",
    "s??curitaire": "sécuritaire", "pi??tons": "piétons", "pi??ton": "piéton",
    "s??curit??": "sécurité", "s??curiser": "sécuriser", "s??curis??": "sécurisé",
    "m??tres": "mètres", "r??seau": "réseau", "arr??te": "arrête",
    "chauss??e": "chaussée", "appr??ci??": "apprécié", "appr??ci??e": "appréciée",
    "m??me": "même", "v??hicules": "véhicules", "acc??s": "accès",
    "montr??al": "montréal", "n??cessaire": "nécessaire", "am??liorer": "améliorer",
    "ren??": "rené", "d??tour": "détour", "??troite": "étroite",
    "am??nagement": "aménagement", "am??nagements": "aménagements",
    "agr??able": "agréable", "??coles": "écoles", "art??rielle": "artérielle",
    "m??tro": "métro", "l??vesque": "lévesque", "prot??g??e": "protégée",
    "lumi??re": "lumière", "c??te": "côte", "continuit??": "continuité",
    "mobilit??": "mobilité", "am??lioration": "amélioration",
    "s??par??e": "séparée", "d??di??e": "dédiée", "probl??me": "problème",
    "travers??e": "traversée", "d??grad??e": "dégradée", "r??duire": "réduire",
}

_word_re = re.compile(r"[a-zA-Z?']+")


def _fix_word(w):
    lw = w.lower()
    if lw in REPAIR:
        return REPAIR[lw]
    return w


def repair_text(s):
    if not s:
        return s
    s = _word_re.sub(lambda m: _fix_word(m.group(0)), s)
    s = s.replace("???", "'")   # corrupted apostrophe
    s = s.replace("??", "e")    # corrupted accent -> plain e
    return s
