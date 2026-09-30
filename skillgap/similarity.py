"""Tokenization and similarity: spaCy word vectors plus typo matching."""
import difflib
import numpy as np
import spacy


class Similarity:
    def __init__(self, terms, threshold=0.85):
        self.terms, self.threshold = terms, threshold
        try:
            self.nlp = spacy.load("en_core_web_md", disable=["parser", "ner", "lemmatizer"])
            self.has_vectors = True
        except OSError:  # model missing: exact + typo matching still work
            self.nlp, self.has_vectors = spacy.blank("en"), False
        self.names, self.matrix = [], None
        if self.has_vectors:
            vecs = []
            for t in terms:
                if len(t) < 4:
                    continue
                d = self.nlp(t)
                if d.vector_norm:
                    self.names.append(t)
                    vecs.append(d.vector / d.vector_norm)
            self.matrix = np.array(vecs)

    def tokenize(self, text):
        return [t.text for t in self.nlp.make_doc(text) if not t.is_space and not t.is_punct]

    def candidates(self, text):
        """Single words and word pairs that could be skill mentions."""
        doc, out, prev = self.nlp.make_doc(text.lower()), [], None
        for t in doc:
            ok = t.is_alpha and not t.is_stop and len(t) > 2
            if ok:
                out.append(t.text)
                if prev is not None and prev.i == t.i - 1:
                    out.append(f"{prev.text} {t.text}")
            prev = t if ok else None
        return list(dict.fromkeys(out))

    def nearest(self, phrase):
        """Return (skill, score) for the closest known skill term, or None."""
        if " " not in phrase and len(phrase) >= 5:  # typos like "javascipt"
            m = difflib.get_close_matches(phrase, list(self.terms), n=1, cutoff=0.88)
            if m:
                return self.terms[m[0]], 0.9
        if self.has_vectors:
            d = self.nlp(phrase)
            if d.vector_norm:
                scores = self.matrix @ (d.vector / d.vector_norm)
                i = int(scores.argmax())
                if scores[i] >= self.threshold:
                    return self.terms[self.names[i]], float(scores[i])
        return None
