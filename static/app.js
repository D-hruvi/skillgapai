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

const RM = matchMedia("(prefers-reduced-motion: reduce)").matches, R = 110;
let vid = 0;
const ease = (p) => 1 - Math.pow(1 - p, 3);

function venn(el, c) {
  if (!el.firstChild) {
    const id = "lens" + vid++;
    el.innerHTML = `<svg viewBox="0 0 480 310" role="img" aria-label="Overlap between your skills and the role"><defs><clipPath id="${id}"><circle class="r" cy="150" r="${R}"/></clipPath></defs>
<circle class="y" cy="150" r="${R}" fill="#ffb454" fill-opacity=".9"/><circle class="r" cy="150" r="${R}" fill="#5b8cff" fill-opacity=".9"/>
<circle class="y" cy="150" r="${R}" fill="#43e8b0" clip-path="url(#${id})"/><text x="120" y="300">Your skills</text><text x="360" y="300">The role</text></svg>`;
  }
  const from = el._c ?? 0, t0 = performance.now();
  el._c = c;
  const step = (now) => {
    const p = RM ? 1 : Math.min((now - t0) / 1400, 1), d = (2 * R + 16) * (1 - (from + (c - from) * ease(p)));
    el.querySelectorAll(".y").forEach((n) => n.setAttribute("cx", 240 - d / 2));
    el.querySelectorAll(".r").forEach((n) => n.setAttribute("cx", 240 + d / 2));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function countUp(n, to) {
  const t0 = performance.now();
  const step = (now) => {
    const p = RM ? 1 : Math.min((now - t0) / 1400, 1);
    n.textContent = Math.round(to * ease(p)) + "%";
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function draw(r) {
  $("empty").hidden = !!r;
  $("result").hidden = !r;
  if (!r) return;
  const total = r.matched.length + r.missing.length;
  $("vennBig")._c = 0;
  venn($("vennBig"), r.coverage / 100);
  countUp($("pct"), r.coverage);
  $("summary").textContent = `You cover ${r.matched.length} of ${total} required skills. ${r.missing.length} left to learn.`;
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
  venn($("vennHero"), 0.4);
  draw(state.report); show(state.tab);
}
init();
