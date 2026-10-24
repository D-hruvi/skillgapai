"""Gap report: compare required skills with the student's skills."""


def tip(skills, plan, s):
    t = skills[s].get("tip") or plan["category_tips"].get(skills[s]["category"], plan["default_tip"])
    return t.format(skill=s)


def build_report(required, have, skills, plan):
    """Embedding-only guesses ("similar") are unsure, so they are listed but never counted."""
    possible = [{"skill": s, "heard": v["matched"]} for s, v in required.items()
                if v["how"] == "similar" and s not in have]
    required = {s: v for s, v in required.items() if v["how"] != "similar"}
    have = {s: v for s, v in have.items() if v["how"] != "similar"}
    matched, missing = [], []
    for s, req in required.items():
        cat = skills[s]["category"]
        if s in have:
            a, b = have[s]["matched"], req["matched"]
            if req["how"] == "described":
                note = f'The job describes it: "{b}"'
            elif have[s]["how"] == "described":
                note = f'You described it: "{a}"'
            elif req["how"] == "detected":
                note = f'You wrote "{a}"'
            else:
                note = "" if a == b else f'You wrote "{a}", the job says "{b}"'
            matched.append({"skill": s, "category": cat, "note": note})
        else:
            ev = req["matched"] if req["how"] in ("described", "typo") else ""
            if req["how"] == "detected":
                ev = "Not in our skill list. Read from the job text, so check it is a real skill."
            missing.append({"skill": s, "category": cat, "suggestion": tip(skills, plan, s), "evidence": ev})
    extra = [{"skill": s, "category": skills[s]["category"]} for s in have if s not in required]
    return {
        "coverage": round(100 * len(matched) / len(required)) if required else 0,
        "matched": matched, "missing": missing, "extra": extra, "possible": possible,
    }


import json
import math
from pathlib import Path

PLAN_FILE = Path(__file__).resolve().parent.parent / "data" / "plan.json"


def load_plan(path=PLAN_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_plan(missing, have, skills, plan, hours_per_week=10):
    """Order the missing skills (plus any prerequisites you lack) into a week-by-week study plan."""
    hpw = max(1, min(40, int(hours_per_week)))
    wanted = {m["skill"] for m in missing}
    evidence = {m["skill"]: m.get("evidence", "") for m in missing}
    requires = plan["requires"]
    needed = {}  # skill -> set of skills that depend on it

    def add(s, dependent=None):
        if s in have:
            return
        first = s not in needed
        needed.setdefault(s, set())
        if dependent:
            needed[s].add(dependent)
        if first:
            for p in requires.get(s, []):
                add(p, s)

    for s in wanted:
        add(s)

    def hours(s):
        return plan["hours"].get(s, plan["default_hours"].get(skills[s]["category"], 15))

    done, order = set(), []
    while len(order) < len(needed):
        ready = [s for s in needed if s not in done
                 and all(p in done for p in requires.get(s, []) if p in needed)]
        s = min(ready, key=lambda x: (-len(needed[x]), x not in wanted, hours(x), x))
        done.add(s)
        order.append(s)

    steps, total = [], 0
    for s in order:
        start = total // hpw + 1
        total += hours(s)
        steps.append({"skill": s, "hours": hours(s), "week_start": start,
                      "week_end": max(start, math.ceil(total / hpw)), "required": s in wanted,
                      "unlocks": sorted(needed[s]), "tip": tip(skills, plan, s),
                      "evidence": evidence.get(s, "")})
    return {"steps": steps, "total_hours": total, "total_weeks": math.ceil(total / hpw),
            "hours_per_week": hpw}
