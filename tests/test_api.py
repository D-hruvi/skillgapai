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


def test_plan_puts_prerequisites_first(client):
    r = post(client, skills_text="html", job_description="We need React skills for this role.").get_json()
    names = [s["skill"] for s in r["plan"]["steps"]]
    assert names.index("JavaScript") < names.index("React")
    assert "HTML" not in names
    by = {s["skill"]: s for s in r["plan"]["steps"]}
    assert by["React"]["required"] and not by["JavaScript"]["required"]


def test_plan_weeks_depend_on_hours_per_week(client):
    body = dict(skills_text="git", job_description="We need Python and SQL skills for this role.")
    slow = post(client, hours_per_week=5, **body).get_json()["plan"]
    fast = post(client, hours_per_week=40, **body).get_json()["plan"]
    assert slow["total_weeks"] > fast["total_weeks"] and slow["total_hours"] == fast["total_hours"]


def test_matched_words_do_not_trigger_false_similarity(client):
    r = post(client, skills_text="python", job_description="Intern: React, Docker and teamwork required.").get_json()
    assert "Problem Solving" not in [m["skill"] for m in r["matched"] + r["missing"]]


NET_JD = """Strong experience in enterprise routing and switching design.
Experience of software-defined networking technologies and load balancers.
Understanding of Data Centre networking. Large-scale network transformation and implementation programmes.
Experience with network segmentation and secure architecture principles."""


def test_networking_synonyms_and_spelling(client):
    r = post(client, skills_text="SDWAN, Load balancer, datacenter", job_description=NET_JD).get_json()
    got = {m["skill"] for m in r["matched"]}
    assert {"SD-WAN", "Load Balancing", "Data Center Networking"} <= got


def test_embedding_guesses_are_not_counted(client):
    r = post(client, skills_text="cisco", job_description=NET_JD).get_json()
    listed = {m["skill"] for m in r["matched"] + r["missing"]}
    assert not listed & {"Docker", "CI/CD", "Deep Learning", "Data Structures", "Teamwork"}


def test_task_description_without_keywords(client):
    jd = "You will write queries against a relational database and build a dashboard for the team."
    r = post(client, skills_text="sql", job_description=jd).get_json()
    by = {m["skill"]: m for m in r["matched"] + r["missing"]}
    assert "SQL" in by and "Data Visualization" in by
    assert "describes" in by["SQL"].get("note", "")


SEC_JD = """SOC Analyst intern. Monitor alerts in Splunk and triage phishing incidents.
Requirements:
Understanding of TCP/IP and firewalls
Experience with Nmap, Wireshark and Burp Suite
Scripting in Python or Bash
Knowledge of MITRE ATT&CK framework"""


def test_skills_outside_dictionary_are_detected(client):
    r = post(client, skills_text="I use nmap daily, python", job_description=SEC_JD).get_json()
    assert "Nmap" in [m["skill"] for m in r["matched"]]
    assert {"Burp Suite", "MITRE ATT&CK"} <= {m["skill"] for m in r["missing"]}


def test_detected_items_are_clean(client):
    r = post(client, skills_text="python", job_description=SEC_JD).get_json()
    for m in r["matched"] + r["missing"]:
        assert m["skill"] == m["skill"].strip() and " is " not in m["skill"] and len(m["skill"]) < 40


def test_other_fields_are_covered(client):
    jd = "Firmware engineer. Experience with RTOS, I2C, SPI and UART on ARM microcontrollers. Knowledge of Bluetooth Low Energy."
    r = post(client, skills_text="python", job_description=jd).get_json()
    names = {m["skill"] for m in r["missing"]}
    assert {"RTOS", "Communication Protocols", "Embedded Systems"} <= names
