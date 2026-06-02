"""
color_mapping.py  —  Canonical color logic for the Wardrobe footwear master.

PURPOSE
    Single source of truth for two derived, color-related fields so the
    dashboard and the master never have to be reconciled by hand again:

        swatch       a hex color for the UI chip / sort key
        color_lane   a human color-family bucket (Black, Brown, Tan, ...)

    Both are DERIVED from each item's `color` string (plus `tags`), with a
    small per-id override table for the handful of items whose true color was
    sampled from a photo and can't be inferred from the name (e.g. two shoes
    both named just "Brown" that are actually different shades).

USAGE (in the master export pipeline)
    from color_mapping import apply_color_mapping
    apply_color_mapping(data)          # mutates data["active"] + data["retired"]
                                       # sets item["swatch"] and item["color_lane"]

    # or per-item:
    from color_mapping import swatch_for, color_lane
    item["swatch"]     = swatch_for(item)
    item["color_lane"] = color_lane(item["color"], item.get("tags"))

DESIGN NOTES
    * Rules are ordered; the FIRST matching substring wins. More specific
      tokens ("dark espresso brown", "burnished dark tan") are listed before
      generic ones ("brown", "tan") so they take priority.
    * There is intentionally NO grey "#888880 / Other" fallback. Any color
      that reaches the end resolves to a neutral mid-brown swatch and the
      "Brown" lane, which is correct for this (overwhelmingly brown) collection
      and avoids the old "everything shows as other" bug. If you ever add a
      genuinely new family (e.g. green, olive), add a rule below.
    * To re-tune a swatch from a photo: add/extend an entry in SWATCH_OVERRIDES
      keyed by item id. That always wins over the name-based table.
"""

# ---------------------------------------------------------------------------
# Per-id swatch overrides: dashboard color corrections that should ALWAYS win
# (they replaced grey "#888880" sentinels or were sampled from the photos and
# are truer than the generic name-derived shade).
# ---------------------------------------------------------------------------
SWATCH_OVERRIDES = {
    "s_11":  "#6E4A2C",   # Alden 2816 PTB        (Burnished Dark Tan)
    "s_12":  "#80614F",   # Alden 29364F PTB      (Brown CXL — photo)
    "s_34":  "#794D42",   # Stefano Bemer 4202    (Brown 020 — photo)
    "s_43":  "#7A5441",   # Edward Green Dover     (Dark Oak — photo)
    "s_50":  "#C8A877",   # Hender Scheme MIP-05  (Natural veg tan)
    "s_51":  "#C9AD91",   # Hermes Espadrille     (Light brown — photo)
    "s_66":  "#46291C",   # Mr. Zhao Chelsea       (Dark Espresso)
    "s_75":  "#C19164",   # RL (C&J) Cap Toe       (Light Tan — photo)
    "s_82":  "#9C6A33",   # Red Wing 9871          (Gold tan / Oro russet)
    "s_87":  "#AA5633",   # Santoni Split-Toe      (Red Clay — photo)
    "s_113": "#7E5E4A",   # Alden D9622 Algonquin (Brown scotch grain — photo)
    "r_1":   "#6E4334",   # Bed|Stu sneaker        (Reddish Brown)
    "r_2":   "#6E4334",   # Cheaney Chelsea        (Reddish Brown)
}

# Sentinel the dashboard used for "couldn't classify" — treat as missing.
_GREY_SENTINEL = "#888880"

# ---------------------------------------------------------------------------
# Name -> hex table. Ordered; first substring hit wins. Lower-cased compare.
# ---------------------------------------------------------------------------
_SWATCH_TABLE = [
    # Horween shell / Alden color codes
    ("color 8",            "#3a1414"),
    ("ravello",            "#8B3A1F"),
    ("cigar",              "#5C3A1F"),
    ("color 4",            "#6B3525"),
    ("color 2",            "#A04020"),
    ("whisk",              "#A05020"),   # whiskey
    # naturals (specific before generic)
    ("natural unfinished", "#C8A877"),
    ("raw shell",          "#A87850"),
    ("natural",            "#A87850"),
    # reds / burgundies
    ("burgundy",           "#5C2424"),
    ("bordeaux",           "#5C2424"),
    ("snuff",              "#B8826A"),
    # neutrals
    ("nero",               "#1f1f1f"),
    ("charcoal",           "#383838"),
    ("black",              "#1f1f1f"),
    ("dark grey",          "#3a3a3c"),
    ("dark gray",          "#3a3a3c"),
    ("grey",               "#3a3a3c"),
    ("gray",               "#3a3a3c"),
    ("navy",               "#1F2848"),
    ("blue",               "#2A3858"),
    ("ecru",               "#E5DCC8"),
    ("cream",              "#E5DCC8"),
    ("white",              "#F0EDE5"),
    # browns (specific before generic)
    ("dark espresso",      "#46291C"),
    ("espresso",           "#3F2818"),
    ("dark chocolate",     "#3a2818"),
    ("ebony",              "#3F2A1B"),
    ("dark oak",           "#7A5441"),
    ("oak",                "#7A5441"),
    ("mahogany",           "#5A2D1F"),
    ("chestnut",           "#7C3A1F"),
    ("tan cognac",         "#A8602A"),
    ("cognac",             "#8B4520"),
    ("tobacco",            "#9A6238"),
    ("noix",               "#7C5235"),
    ("walnut",             "#7C5235"),
    ("red clay",           "#AA5633"),
    ("clay",               "#AA5633"),
    ("reddish",            "#6E4334"),
    ("rust",               "#9C6A33"),
    ("teak",               "#5A3520"),
    ("rye",                "#7C5230"),
    ("caramel",            "#A56F35"),
    ("amber",              "#7C4525"),
    ("gold",               "#9C6A33"),   # "gold tan"
    ("burnished dark tan", "#6E4A2C"),
    ("dark tan",           "#6E4A2C"),
    ("light tan",          "#C19164"),
    ("tan",                "#C09060"),
    ("light brown",        "#C9AD91"),
    ("brown 020",          "#794D42"),
    ("medium brown",       "#7B5235"),
    ("mid-brown",          "#7B5235"),
    ("dark brown",         "#3F2A1B"),
    ("brown",              "#5C3825"),
]

_NEUTRAL_FALLBACK = "#6B4A33"   # mid-brown; never grey "other"


def derive_swatch(color):
    """Map a color NAME to a representative hex (name-based, no per-id logic)."""
    c = (color or "").lower()
    for token, hexv in _SWATCH_TABLE:
        if token in c:
            return hexv
    return _NEUTRAL_FALLBACK


def swatch_for(item):
    """Final swatch for an item, in priority order:
        1. explicit per-id override (dashboard color corrections)
        2. the item's existing curated swatch, if present and not the grey
           "#888880" sentinel  (preserves the master's hand-picked hexes)
        3. name-derived swatch
    """
    if item.get("id") in SWATCH_OVERRIDES:
        return SWATCH_OVERRIDES[item["id"]]
    existing = (item.get("swatch") or "").strip()
    if existing and existing.lower() != _GREY_SENTINEL:
        return existing
    return derive_swatch(item.get("color"))


# ---------------------------------------------------------------------------
# Color-lane (color family) classifier. Ordered; first hit wins.
# Mirrors the dashboard's getColorLane().
# ---------------------------------------------------------------------------
def color_lane(color, tags=None):
    c = (color or "").lower()
    tags = [t.lower() for t in (tags or [])]

    if "color 8" in c or "color 8" in tags or "color-8" in tags:
        return "Color 8"
    if "ravello" in c:                                   return "Ravello"
    if "cigar" in c:                                     return "Cigar"
    if "color 4" in c:                                   return "Color 4"
    if "color 2" in c:                                   return "Color 2"
    if "whisk" in c:                                     return "Whisky"
    if "natural" in c and "reverse" in c:                return "Natural reverse"
    if "burgundy" in c or "bordeaux" in c or "burgundy" in tags:
        return "Burgundy"
    if "snuff" in c:                                     return "Snuff"
    # hard color families first (so "White - natural" stays white)
    if any(k in c for k in ("black", "ebon", "nero")):   return "Black"
    if any(k in c for k in ("navy", "blue", "cobalt")):  return "Blue/Navy"
    if any(k in c for k in ("grey", "gray", "charcoal")):return "Grey/Charcoal"
    if any(k in c for k in ("white", "ecru", "ivory", "cream")):
        return "White/Ecru"
    # brown / tan family
    if any(k in c for k in ("espresso", "dark chocolate", "dark brown")):
        return "Dark brown"
    if "medium brown" in c or "mid-brown" in c:          return "Medium brown"
    if "walnut" in c:                                    return "Walnut"
    if "mahogany" in c:                                  return "Mahogany"
    if "tobacco" in c or "noix" in c:                    return "Tobacco/Noix"
    if "oak" in c:                                       return "Oak"
    if any(k in c for k in ("clay", "brick", "rust", "reddish", "russet")):
        return "Russet/Red"
    if "cognac" in c or "chestnut" in c:                 return "Cognac/Chestnut"
    if any(k in c for k in ("teak", "rye", "oro", "amber")):
        return "Warm patinated"
    if any(k in c for k in ("natural", "raw", "undyed", "veg tan")):
        return "Natural"
    if any(k in c for k in ("tan", "gold", "caramel", "camel", "wheat", "sand", "beige")):
        return "Tan"
    if any(k in c for k in ("greige", "taupe", "stone", "mushroom")):
        return "Greige/Taupe"
    if "brown" in c:                                     return "Brown"
    return "Brown"   # neutral fallback for this collection — never "Other"


# ---------------------------------------------------------------------------
# Bulk helper
# ---------------------------------------------------------------------------
def apply_color_mapping(data, set_lane=True):
    """Mutate a master dict in place: set swatch (+ color_lane) on every item.

    `data` is the parsed master JSON: {"active": [...], "retired": [...], ...}.
    Returns the same dict for convenience.
    """
    for section in ("active", "retired"):
        for item in data.get(section, []):
            item["swatch"] = swatch_for(item)
            if set_lane:
                item["color_lane"] = color_lane(item.get("color"), item.get("tags"))
    return data


if __name__ == "__main__":
    # Quick self-check: print the lane + swatch for every distinct color.
    import json, sys
    if len(sys.argv) > 1:
        d = json.load(open(sys.argv[1]))
        seen = {}
        for it in d.get("active", []) + d.get("retired", []):
            seen[it.get("color")] = (color_lane(it.get("color"), it.get("tags")),
                                     swatch_for(it))
        for col in sorted(seen, key=lambda x: (x or "")):
            lane, sw = seen[col]
            print(f"{sw}  {lane:16}  {col}")
