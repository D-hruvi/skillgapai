"""Skill extraction against the editable skill dictionary."""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "skills.json"


def load_skills(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_terms(skills):
    """Map every lowercase name/alias to its canonical skill."""
    return {t.lower(): n for n, i in skills.items() for t in [n, *i.get("aliases", [])]}


class Extractor:
    def __init__(self, skills, terms, sim):
        self.skills, self.terms, self.sim = skills, terms, sim
        self.regex = {t: re.compile(r"(?<![\w+#.])" + re.escape(t) + r"(?![\w+#])") for t in terms}
        self.known_words = {w for t in terms for w in re.findall(r"\w+", t)}

    def extract(self, text):
        """Return {skill: {how, matched, score}}. how = exact | synonym | similar."""
        low, found = text.lower(), {}
        for term, rx in self.regex.items():
            if rx.search(low):
                skill = self.terms[term]
                how = "exact" if term == skill.lower() else "synonym"
                if skill not in found or how == "exact":
                    found[skill] = {"how": how, "matched": term, "score": 1.0}
        for cand in self.sim.candidates(text):
            if cand in self.terms or set(cand.split()) <= self.known_words:
                continue
            hit = self.sim.nearest(cand)
            if hit and hit[0] not in found:
                found[hit[0]] = {"how": "similar", "matched": cand, "score": round(hit[1], 2)}
        return found
