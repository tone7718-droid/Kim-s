"""KBO team code/name mappings.

Statiz uses Korean short names on the schedule page. We canonicalize them
to stable codes that are safe to use as JSON keys and UI identifiers.

If a season uses a different name (e.g. SK Wyverns -> SSG Landers from 2021,
kt wiz casing), add a row here. The scraper looks up names via NAME_TO_CODE.
"""

TEAMS = [
    {"code": "KIA",  "name": "KIA",  "aliases": ["KIA", "기아"]},
    {"code": "SS",   "name": "삼성", "aliases": ["삼성"]},
    {"code": "LG",   "name": "LG",   "aliases": ["LG"]},
    {"code": "OB",   "name": "두산", "aliases": ["두산"]},
    {"code": "KT",   "name": "KT",   "aliases": ["KT", "kt"]},
    {"code": "SSG",  "name": "SSG",  "aliases": ["SSG", "SK"]},
    {"code": "LT",   "name": "롯데", "aliases": ["롯데"]},
    {"code": "HH",   "name": "한화", "aliases": ["한화"]},
    {"code": "NC",   "name": "NC",   "aliases": ["NC"]},
    {"code": "WO",   "name": "키움", "aliases": ["키움"]},
]

NAME_TO_CODE = {alias: t["code"] for t in TEAMS for alias in t["aliases"]}
CODE_TO_NAME = {t["code"]: t["name"] for t in TEAMS}


def to_code(name: str) -> str:
    name = name.strip()
    if name in NAME_TO_CODE:
        return NAME_TO_CODE[name]
    raise ValueError(f"Unknown team name: {name!r}")
