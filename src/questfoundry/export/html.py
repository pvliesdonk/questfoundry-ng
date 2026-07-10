"""Standalone HTML player (design doc 04 §2): one self-contained file —
embedded runtime JSON + a small dependency-free JS player. Works from
file://, no network, no build step. Deliberately minimal: passage
rendering, hidden-gated choices, a journey recap, one localStorage save
slot, restart.
"""

from __future__ import annotations

import base64
import json

from questfoundry.export.runtime_json import build_runtime
from questfoundry.project.io import Project

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font: 18px/1.65 Georgia, 'Times New Roman', serif;
         background: #14171a; color: #d8d4c8; }
  main { max-width: 42rem; margin: 0 auto; padding: 3rem 1.2rem 6rem; }
  h1 { font-size: 1.4rem; letter-spacing: .12em; text-transform: uppercase;
       color: #9db4c0; font-weight: normal; }
  #art { margin: 1.5rem 0; }
  #art img { max-width: 100%; border-radius: 4px; display: block; margin: 0 auto; }
  #art figcaption { text-align: center; font-size: .85rem; color: #78909c;
       font-style: italic; margin-top: .4rem; }
  #prose p { margin: 1em 0; }
  #choices { margin-top: 2.2rem; padding: 0; list-style: none; }
  #choices li { margin: .7rem 0; }
  #choices button { font: inherit; width: 100%; text-align: left;
       background: #1d2226; color: #cfd8dc; border: 1px solid #37474f;
       border-radius: 4px; padding: .65rem .9rem; cursor: pointer; }
  #choices button:hover { background: #263238; border-color: #90a4ae; }
  #ending { margin-top: 2.5rem; padding: 1.2rem; border: 1px solid #9db4c0;
       text-align: center; font-variant: small-caps; font-size: 1.3rem; }
  footer { margin-top: 3rem; font-size: .8rem; color: #607d8b; }
  footer a { color: #90a4ae; cursor: pointer; margin-right: 1rem; }
  details { margin-top: 1rem; font-size: .85rem; color: #78909c; }
  #codex article { margin-top: .8rem; }
  #codex h3 { margin: 0 0 .3rem; font-size: 1rem; color: #9db4c0; font-weight: normal; }
</style>
</head>
<body>
<main>
  <h1 id="title"></h1>
  <figure id="art" hidden><img alt=""><figcaption></figcaption></figure>
  <div id="prose"></div>
  <ul id="choices"></ul>
  <div id="ending" hidden></div>
  __CODEX__
  <details id="recap"><summary>The journey so far</summary><ol id="trail"></ol></details>
  <footer>
    <a id="restart">restart</a><a id="save">save</a><a id="load">load</a>
  </footer>
</main>
<script>
const STORY = __STORY__;
const KEY = "questfoundry:" + STORY.meta.title;
const ART = Object.fromEntries((STORY.art || []).map(a => [a.passage, a]));
let state = { at: STORY.start, flags: [], trail: [] };

function el(id) { return document.getElementById(id); }
function has(req) { return req.every(f => state.flags.includes(f)); }

function render() {
  const p = STORY.passages[state.at];
  el("title").textContent = STORY.meta.title;
  const art = ART[state.at], fig = el("art");
  fig.hidden = !art;
  if (art) {
    fig.querySelector("img").src = art.image;
    fig.querySelector("figcaption").textContent = art.caption || "";
  }
  el("prose").innerHTML = p.prose.trim().split(/\\n\\s*\\n/)
    .map(par => "<p>" + par.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</p>").join("");
  const ul = el("choices"); ul.innerHTML = "";
  const end = el("ending");
  if (p.ending) {
    end.hidden = false; end.textContent = p.ending.title;
  } else {
    end.hidden = true;
    p.choices.filter(c => has(c.requires)).forEach(c => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.textContent = c.label;
      b.onclick = () => {
        state.flags = [...new Set([...state.flags, ...c.grants])];
        state.trail.push(c.label);
        state.at = c.to;
        render();
      };
      li.appendChild(b); ul.appendChild(li);
    });
  }
  el("trail").innerHTML = state.trail
    .map(t => "<li>" + t.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</li>").join("");
  window.scrollTo(0, 0);
}

el("restart").onclick = () => { state = { at: STORY.start, flags: [], trail: [] }; render(); };
el("save").onclick = () => localStorage.setItem(KEY, JSON.stringify(state));
el("load").onclick = () => {
  const s = localStorage.getItem(KEY);
  if (s) { state = JSON.parse(s); render(); }
};
render();
</script>
</body>
</html>
"""


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;")


def _codex_panel(codex: list[dict]) -> str:
    """A <details> panel of codex entries (design doc 04 §2), rendered
    server-side like the rest of this dependency-free player. Omitted
    entirely — not just hidden — when there is no codex to show."""
    if not codex:
        return ""
    articles = []
    for entry in codex:
        paragraphs = "".join(
            f"<p>{_escape(par)}</p>"
            for par in entry["body"].strip().split("\n\n")
            if par.strip()
        )
        articles.append(f"<article><h3>{_escape(entry['title'])}</h3>{paragraphs}</article>")
    return (
        '<details id="codex"><summary>The Codex</summary>' + "".join(articles) + "</details>"
    )


def build_html(project: Project) -> str:
    data = build_runtime(project)
    # the player is one self-contained file, so rendered images inline as
    # data URIs here; the canonical runtime JSON keeps project-root paths
    for entry in data["art"]:
        image_bytes = (project.root / entry["image"]).read_bytes()
        entry["image"] = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    story = json.dumps(data, ensure_ascii=False)
    # a literal "</script>" inside the JSON would end the script element
    story = story.replace("</", "<\\/")
    title = project.name.replace("<", "&lt;")
    return (
        _TEMPLATE.replace("__TITLE__", title)
        .replace("__STORY__", story)
        .replace("__CODEX__", _codex_panel(data["codex"]))
    )
