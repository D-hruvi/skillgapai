"""Skill extraction against the editable skill dictionary."""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "skills.json"


def load_skills(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_terms(skills):
    """Map every lowercase name/alias to its canonical skill."""
    return {t.lower(): n for n, i in skills.items()
            for t in [*([] if i.get("no_name") else [n]), *i.get("aliases", [])]}


class Extractor:
    def __init__(self, skills, terms, sim):
        self.skills, self.terms, self.sim = skills, terms, sim
        self.regex = {t: re.compile(r"(?<![\w+#.])" + re.escape(t) + r"(?![\w+#])") for t in terms}
        self.known_words = {w for t in terms for w in re.findall(r"\w+", t)}
        # cues describe the work without naming the skill, e.g. "write query" -> SQL
        self.cues = [(n, sim.cue_keys(c)) for n, i in skills.items() for c in i.get("cues", [])]

    def extract(self, text):
        return self.analyse(text)[0]

    def analyse(self, text):
        """Return ({skill: {how, matched, score}}, text with dictionary matches blanked out).
        how: exact | synonym (alias) | described (task cue) | typo | similar (embedding, unsure)."""
        low, found, mask = text.lower(), {}, list(text)
        for term, rx in self.regex.items():
            spans = list(rx.finditer(low))
            if spans:
                for m in spans:
                    mask[m.start():m.end()] = " " * (m.end() - m.start())
                skill = self.terms[term]
                how = "exact" if term == skill.lower() else "synonym"
                if skill not in found or how == "exact":
                    found[skill] = {"how": how, "matched": term, "score": 1.0}
        for sentence in re.split(r"[\n.;!?]+", text):
            if len(sentence.strip()) < 8:
                continue
            words = self.sim.word_set(sentence)
            for skill, keys in self.cues:
                if skill not in found and keys and all(k & words for k in keys):
                    found[skill] = {"how": "described", "matched": sentence.strip()[:90], "score": 0.9}
        for cand in self.sim.candidates("".join(mask)):
            if cand in self.terms or set(cand.split()) <= self.known_words:
                continue
            hit = self.sim.nearest(cand)
            if hit and hit[0] not in found:
                kind = "typo" if hit[2] == "typo" else "similar"
                found[hit[0]] = {"how": kind, "matched": cand, "score": round(hit[1], 2)}
        # placeholder marks dictionary hits so open detection never keeps half a phrase
        return found, re.sub(r" {2,}", " zzskill ", "".join(mask))
