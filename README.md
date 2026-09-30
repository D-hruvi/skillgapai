# SkillGapAI

Compares a student's skills with an internship job description using classical NLP (no LLM, no external API).

**Pipeline:** tokenize → find skills from `data/skills.json` (exact, alias, typo) → spaCy word-vector similarity → gap report + suggestions.

## Run locally
```
pip install -r requirements.txt
python -m spacy download en_core_web_md
python app.py            # http://localhost:5000
python -m pytest         # tests
```
Without the spaCy model the app still runs (exact, alias and typo matching); `/api/health` shows `embeddings: false`.

## Deploy on Render (free)
1. Push this folder to a GitHub repo.
2. Render dashboard → New → Blueprint → pick the repo (it reads `render.yaml`).
3. Wait for the Docker build. First visit after idle takes ~30s on the free plan.

## Extend
Add skills, aliases and suggestions in `data/skills.json`. No code change needed.
## API
`GET /api/skills` · `GET /api/health` · `POST /api/analyze {skills_text, skills_list, job_description}`
