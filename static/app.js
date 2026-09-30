const $ = (id) => document.getElementById(id);
const KEY = "skillgapai-session";
const state = Object.assign({ tab: "skills", text: "", picked: [], jd: "", report: null },
  JSON.parse(localStorage.getItem(KEY) || "{}"));
const save = () => localStorage.setItem(KEY, JSON.stringify(state));

function show(tab) {
  state.tab = tab;
  for (const s of ["skills", "job", "report"]) $(s).hidden = s !== tab;
  document.querySelectorAll("nav button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  save();
}

function list(id, items, render) {
  const ul = $(id);
  ul.replaceChildren();
  if (!items.length) { const li = document.createElement("li"); li.textContent = "None"; ul.append(li); return; }
  for (const it of items) { const li = document.createElement("li"); render(li, it); ul.append(li); }
}

function draw(r) {
  $("empty").hidden = !!r;
  $("result").hidden = !r;
  if (!r) return;
  $("meter").replaceChildren(...[...r.matched.map(() => "y"), ...r.missing.map(() => "n")].map((c) => {
    const i = document.createElement("i"); i.className = c; return i;
  }));
  $("summary").textContent = `You cover ${r.matched.length} of ${r.matched.length + r.missing.length} required skills (${r.coverage}%).`;
  list("matched", r.matched, (li, m) => {
    li.textContent = m.skill;
    if (m.note) { const s = document.createElement("small"); s.textContent = m.note; li.append(s); }
  });
  list("missing", r.missing, (li, m) => {
    const b = document.createElement("b"); b.textContent = m.skill;
    li.append(b, document.createTextNode(m.suggestion));
  });
  list("extra", r.extra, (li, m) => (li.textContent = m.skill));
}

async function run() {
  const btn = $("run"), err = $("error");
  err.textContent = "";
  btn.disabled = true; btn.textContent = "Analysing...";
  try {
    const res = await fetch("/api/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills_text: state.text, skills_list: state.picked, job_description: state.jd }),
    });
    const data = await res.json();
    if (!res.ok) { err.textContent = data.error || "Something went wrong. Try again."; return; }
    state.report = data; draw(data); show("report");
  } catch { err.textContent = "Cannot reach the server. Check your connection and try again."; }
  finally { btn.disabled = false; btn.textContent = "Find my gaps"; }
}

async function init() {
  $("skillsText").value = state.text; $("jobText").value = state.jd;
  $("skillsText").oninput = (e) => { state.text = e.target.value; save(); };
  $("jobText").oninput = (e) => { state.jd = e.target.value; save(); };
  document.querySelectorAll("nav button").forEach((b) => (b.onclick = () => show(b.dataset.tab)));
  document.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => show(b.dataset.go)));
  $("again").onclick = () => { state.jd = ""; $("jobText").value = ""; show("job"); };
  $("run").onclick = run;
  try {
    const groups = await (await fetch("/api/skills")).json();
    for (const [cat, names] of Object.entries(groups)) {
      const h = document.createElement("h3"); h.textContent = cat; $("checklist").append(h);
      for (const n of names) {
        const l = document.createElement("label"); l.className = "pick";
        const c = document.createElement("input"); c.type = "checkbox"; c.checked = state.picked.includes(n);
        c.onchange = () => { state.picked = c.checked ? [...state.picked, n] : state.picked.filter((x) => x !== n); save(); };
        const s = document.createElement("span"); s.textContent = n;
        l.append(c, s); $("checklist").append(l);
      }
    }
  } catch { $("checklist").textContent = "Could not load the checklist. You can still type your skills."; }
  draw(state.report); show(state.tab);
}
init();
