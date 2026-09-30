import os
from flask import Flask, jsonify, request

from skillgap.extract import Extractor, build_terms, load_skills
from skillgap.report import build_report
from skillgap.similarity import Similarity

app = Flask(__name__, static_folder="static", static_url_path="")
SKILLS = load_skills()
TERMS = build_terms(SKILLS)
SIM = Similarity(TERMS)
EXTRACTOR = Extractor(SKILLS, TERMS, SIM)


def bad(msg, code=400):
    return jsonify(error=msg), code


@app.get("/")
def home():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", embeddings=SIM.has_vectors, skills=len(SKILLS))


@app.get("/api/skills")
def skills():
    groups = {}
    for name, info in SKILLS.items():
        groups.setdefault(info["category"], []).append(name)
    return jsonify(groups)


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return bad("Send a JSON body.")
    text = str(data.get("skills_text") or "").strip()
    picked = [s for s in (data.get("skills_list") or []) if s in SKILLS]
    jd = str(data.get("job_description") or "").strip()
    if len(text) > 5000 or len(jd) > 20000:
        return bad("Input is too long. Trim it and try again.")
    if not text and not picked:
        return bad("Add your skills first: type them or tick some in the checklist.")
    if len(jd) < 20:
        return bad("Paste the full job description (at least a couple of sentences).")

    required = EXTRACTOR.extract(jd)
    if not required:
        return bad("No known skills found in this job description. Paste the requirements section.", 422)
    have = EXTRACTOR.extract(text) if text else {}
    for s in picked:
        have.setdefault(s, {"how": "exact", "matched": s.lower(), "score": 1.0})
    report = build_report(required, have, SKILLS)
    report["stats"] = {"jd_tokens": len(SIM.tokenize(jd)), "embeddings": SIM.has_vectors}
    return jsonify(report)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
