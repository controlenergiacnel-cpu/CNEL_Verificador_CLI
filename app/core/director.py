from __future__ import annotations
import re, json, os
from difflib import SequenceMatcher
from typing import Dict, Any, List, Tuple, Optional

# Defaults (se pueden sobrescribir desde config.json)
CANONICAL = "RICARDO DANIEL VERA MERCHANCANO"
ALIASES = [
    "RICARDO VERA MERCHANCANO",
    "R D VERA MERCHANCANO",
    "R VERA MERCHANCANO",
    "RICARDO D VERA MERCHANCANO",
    "RICARDO VERA M",
    "ING RICARDO VERA",
]
ROLE_HINTS = [
    "DIRECTOR COMERCIAL",
    "DIRECTOR",
    "DIRECCION COMERCIAL",
    "DIR. COMERCIAL",
]
CFG_MIN_SCORE = 63.0

def _load_cfg():
    p = os.path.join("config","config.json")
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:
        return {}

_cfg = _load_cfg()
try:
    d = _cfg.get("director", {})
    CANONICAL = d.get("canonical", CANONICAL) or CANONICAL
    ALIASES = d.get("aliases", ALIASES) or ALIASES
    CFG_MIN_SCORE = float(d.get("min_score", CFG_MIN_SCORE))
except Exception:
    pass

def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9 ]+", " ", s.upper()).strip()

def _token_set_ratio(a: str, b: str) -> float:
    sa = set(_norm(a).split())
    sb = set(_norm(b).split())
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    return 100.0 * (2 * len(inter)) / (len(sa) + len(sb))

def _similar(a: str, b: str) -> float:
    return 100.0 * SequenceMatcher(a=_norm(a), b=_norm(b)).ratio()

def find_director_mentions(text: str, min_score: Optional[float] = None) -> Dict[str, Any]:
    if min_score is None:
        min_score = CFG_MIN_SCORE
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    best: Tuple[float, str, str] = (0.0, "", "")
    role_context = None

    for ln in lines:
        if any(h in _norm(ln) for h in [_norm(hh) for hh in ROLE_HINTS]):
            role_context = ln
            break

    candidates = [CANONICAL] + ALIASES
    for ln in lines:
        for cand in candidates:
            score = max(_token_set_ratio(ln, cand), _similar(ln, cand))
            if role_context and ln in role_context:
                score += 5.0
            if score > best[0]:
                best = (score, cand, ln)

    found = best[0] >= float(min_score)
    return {
        "found": found,
        "best_match": best[1] if found else None,
        "score": round(best[0], 2),
        "line": best[2] if found else None,
        "role_context": role_context,
    }

if __name__ == "__main__":
    import sys, json
    p = sys.argv[1] if len(sys.argv) > 1 else None
    if not p:
        print("Uso: python -m app.core.director <archivo.txt>")
        raise SystemExit(1)
    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
        t = fh.read()
    print(json.dumps(find_director_mentions(t), ensure_ascii=False, indent=2))
