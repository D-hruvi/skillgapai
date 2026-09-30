import pytest
from app import app

JD = "We need an intern with JavaScript, React, SQL and Docker. Git and teamwork are a plus."


@pytest.fixture
def client():
    return app.test_client()


def post(client, **body):
    return client.post("/api/analyze", json=body)


def test_synonym_match(client):
    r = post(client, skills_text="I know JS and py", job_description=JD).get_json()
    assert "JavaScript" in [m["skill"] for m in r["matched"]]
    assert "Docker" in [m["skill"] for m in r["missing"]]


def test_checklist_and_suggestions(client):
    r = post(client, skills_list=["SQL", "Git"], job_description=JD).get_json()
    assert {m["skill"] for m in r["matched"]} == {"SQL", "Git"}
    assert all(m["suggestion"] for m in r["missing"])


def test_health(client):
    assert client.get("/api/health").get_json()["status"] == "ok"


@pytest.mark.parametrize("body", [
    {"skills_text": "", "job_description": JD},
    {"skills_text": "python", "job_description": ""},
    {"skills_text": "python", "job_description": "we hire people who enjoy doing many different things"},
])
def test_bad_input(client, body):
    assert client.post("/api/analyze", json=body).status_code in (400, 422)
