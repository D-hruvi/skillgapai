import os
from flask import Flask, jsonify, request

from skillgap.extract import Extractor, build_terms, load_skills
from skillgap.openvocab import OpenVocab
from skillgap.report import build_plan, build_report, load_plan
from skillgap.similarity import Similarity

app = Flask(__name__, static_folder="static", static_url_path="")
SKILLS = load_skills()
TERMS = build_terms(SKILLS)
SIM = Similarity(TERMS)
EXTRACTOR = Extractor(SKILLS, TERMS, SIM)
PLAN = load_plan()
OPEN = OpenVocab(SIM.nlp, TERMS)


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

    required, masked = EXTRACTOR.analyse(jd)
    catalog, detected = dict(SKILLS), OPEN.from_job(masked)
    for name in detected:  # skills outside the dictionary, read straight from the text
        catalog[name] = {"category": "Detected in the job", "aliases": []}
        required[name] = {"how": "detected", "matched": name, "score": 0.7}
    if not any(v["how"] != "similar" for v in required.values()):
        return bad("No known skills found in this job description. Paste the requirements section.", 422)
    have = EXTRACTOR.extract(text) if text else {}
    for s in picked:
        have.setdefault(s, {"how": "exact", "matched": s.lower(), "score": 1.0})
    items = OPEN.student_items(text)
    for name in detected:
        hit = OPEN.match(name, items, text)
        if hit:
            have[name] = {"how": "exact", "matched": hit, "score": 0.9}
    report = build_report(required, have, catalog, PLAN)
    try:
        hpw = int(data.get("hours_per_week") or 10)
    except (TypeError, ValueError):
        hpw = 10
    report["plan"] = build_plan(report["missing"], have, catalog, PLAN, hpw)
    report["stats"] = {"jd_tokens": len(SIM.tokenize(jd)), "embeddings": SIM.has_vectors}
    return jsonify(report)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
