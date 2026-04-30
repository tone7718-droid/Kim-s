"""KBO team code/name mappings.

Canonical codes (used as JSON keys and in game IDs):
    KIA, SS, LG, OB, KT, SSG, LT, HH, NC, WO

Aliases cover what different data sources call each team:
- Naver Sports API uses HT for KIA, OB for 두산, SS for 삼성, etc.
- SK Wyverns rebranded to SSG Landers in 2021 — both alias to SSG.
- 키움 was previously 넥센 (Nexen / HE).
"""

TEAMS = [
    {"code": "KIA", "name": "KIA",  "aliases": ["KIA", "HT", "기아"]},
    {"code": "SS",  "name": "삼성", "aliases": ["SS", "삼성"]},
    {"code": "LG",  "name": "LG",   "aliases": ["LG"]},
    {"code": "OB",  "name": "두산", "aliases": ["OB", "DS", "두산"]},
    {"code": "KT",  "name": "KT",   "aliases": ["KT", "kt"]},
    {"code": "SSG", "name": "SSG",  "aliases": ["SSG", "SK"]},
    {"code": "LT",  "name": "롯데", "aliases": ["LT", "롯데"]},
    {"code": "HH",  "name": "한화", "aliases": ["HH", "한화"]},
    {"code": "NC",  "name": "NC",   "aliases": ["NC"]},
    {"code": "WO",  "name": "키움", "aliases": ["WO", "HE", "키움", "넥센"]},
]

NAME_TO_CODE = {alias: t["code"] for t in TEAMS for alias in t["aliases"]}
CODE_TO_NAME = {t["code"]: t["name"] for t in TEAMS}


def normalize_code(s: str) -> str:
    """Map any known alias/code to our canonical code. Empty string if unknown."""
    s = (s or "").strip()
    return NAME_TO_CODE.get(s, "")
