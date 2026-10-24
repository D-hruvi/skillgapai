"""Open-vocabulary detection: finds skill-like phrases that are NOT in the dictionary,
so jobs from any tech field still get analysed. Lower confidence than dictionary matches."""
import re
from difflib import SequenceMatcher

GENERIC = set("""experience experiences knowledge understanding skills skill ability abilities years year team teams company role roles
candidate candidates requirement requirements responsibility responsibilities environment environments business solutions solution
strong good excellent proven demonstrable demonstrated relevant related similar desirable preferred required essential plus bonus
degree bachelor bachelors master masters qualification qualifications background proficiency expertise familiarity level levels
work working ways way time projects project people customers customer clients client industry standards range variety advantage advantageous benefit module modules""".split())
LEAD = {"strong", "good", "excellent", "solid", "hands-on", "basic", "advanced", "practical", "proven", "deep",
        "extensive", "some", "sound", "general", "previous", "professional", "in-depth", "working"}
TRAIL = {"skills", "technologies", "technology", "principles", "tools", "tooling", "frameworks", "framework", "concepts",
         "platforms", "experience", "knowledge", "practices", "environments", "programmes", "programs"}
ACR_STOP = {"HR", "UK", "US", "USA", "EU", "CEO", "CTO", "CV", "PM", "AM", "OK", "FAQ", "PDF", "ID", "IT", "KPI", "NHS",
            "MBA", "BSC", "MSC", "PHD", "AND", "THE", "FOR", "EOE", "DEI", "FTE", "LLC", "INC", "LTD", "ASAP", "TBD", "ETC", "STEM"}
TRIGGER = re.compile(r"(?:experience|experienced|knowledge|proficien\w*|familiar\w*|understanding|expertise|skilled|background|"
                     r"exposure|competen\w*)\s+(?:with|in|of|on|using|across)\s+|(?:such as|including|includes|e\.g\.?|for example|like|"
                     r"tools?|technologies|stack|frameworks?)\s*[:\-]?\s+|:\s*", re.I)
SPLIT = re.compile(r"[,;/&|()•]| and | or | - |\band/or\b", re.I)


def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


class OpenVocab:
    def __init__(self, nlp, terms):
        self.nlp, self.terms = nlp, terms

    def clean(self, s):
        s = re.sub(r"^[\s\-–•*·\d.)]+(?=[A-Za-z])|[\s.:]+$", "", s.strip())
        toks = list(self.nlp(s))
        while toks and (toks[0].is_stop or toks[0].is_punct or toks[0].is_space or toks[0].lower_ in LEAD | GENERIC):
            toks.pop(0)
        while toks and (toks[-1].is_stop or toks[-1].is_punct or toks[-1].is_space or toks[-1].lower_ in TRAIL | GENERIC):
            toks.pop()
        if not toks or len(toks) > 4 or toks[0].pos_ == "VERB" or any(t.pos_ == "AUX" for t in toks):
            return None
        out = " ".join(t.text for t in toks)
        if "zzskill" in out.lower():
            return None
        if len(out) < 2 or not re.search(r"[A-Za-z]", out) or norm(out) in GENERIC or norm(out) in self.terms:
            return None
        return out

    def from_job(self, text, cap=25):
        found = {}

        def add(s):
            c = self.clean(s) if s else None
            if c:
                found.setdefault(norm(c), c)

        for line in text.split("\n"):
            line = line.strip()
            if not line or line.isupper():
                continue
            if len(line.split()) <= 5 and not line.endswith("."):
                add(line)
            for m in TRIGGER.finditer(line):
                for part in SPLIT.split(re.split(r"[.;]", line[m.end():])[0]):
                    add(part)
            for a in re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", line):
                if a not in ACR_STOP:
                    add(a)
        keys = sorted(found, key=len)
        drop = {k for k in keys for o in keys if k != o and re.search(rf"\b{re.escape(k)}\b", o)}
        return [found[k] for k in found if k not in drop][:cap]

    def student_items(self, text):
        return [norm(c) for p in SPLIT.split(text.replace("\n", ",")) if (c := self.clean(p))]

    def match(self, name, items, raw_text):
        n = norm(name)
        if re.search(rf"(?<![\w+#]){re.escape(n)}(?![\w+#])", raw_text.lower()):
            return n
        for it in items:
            if SequenceMatcher(None, it, n).ratio() >= 0.88:
                return it
        return None
