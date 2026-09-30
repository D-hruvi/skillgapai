"""Gap report: compare required skills with the student's skills."""


def build_report(required, have, skills):
    matched, missing = [], []
    for s, req in required.items():
        cat = skills[s]["category"]
        if s in have:
            a, b = have[s]["matched"], req["matched"]
            note = "" if a == b else f'You wrote "{a}", the job says "{b}"'
            matched.append({"skill": s, "category": cat, "note": note})
        else:
            missing.append({"skill": s, "category": cat, "suggestion": skills[s]["tip"]})
    extra = [{"skill": s, "category": skills[s]["category"]} for s in have if s not in required]
    return {
        "coverage": round(100 * len(matched) / len(required)),
        "matched": matched, "missing": missing, "extra": extra,
    }
