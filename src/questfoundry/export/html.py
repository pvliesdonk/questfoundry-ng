"""Standalone HTML player (design doc 04 §2, §7): one self-contained file —
embedded runtime JSON + a small dependency-free JS player. Works from
file://, no network, no build step.

The style is **1d, "the cover as an object on a shelf"**: a title screen
that sets the cover as an inset object with begin/continue/how-to-read
beside it, then a calm reading view. Everything the shared accessibility
contract asks for is structural rather than styled — choices are real
buttons inside a labelled `nav`, the section is an `article` that takes
focus on every turn, status changes announce through a polite live region,
the measure is in `ch` so it reflows to 320px and survives 200% zoom, and
the turn transition collapses to nothing under `prefers-reduced-motion`.

Unavailable choices are **hidden, never shown disabled** — runtime
semantics (§1 rule 2), which is also why the contract's "locked choices
stay visible with the reason" clause is a print concern: paper cannot hide
a choice, a screen can.
"""

from __future__ import annotations

import base64
import json
import re

from questfoundry.export.runtime_json import build_runtime
from questfoundry.export.style import (
    COVER_RATIO,
    DEFAULT_SCREEN_STYLE,
    ScreenStyle,
    image_width,
    screen_style,
)
from questfoundry.project.io import Project

_PLACEHOLDER_RE = re.compile(r"__[A-Z_]+__")

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    color-scheme: dark;
    --page: __DARK_PAGE__; --ink: __DARK_INK__; --muted: __DARK_MUTED__;
    --accent: __DARK_ACCENT__; --rule: __DARK_RULE__;
    --measure: __MEASURE__ch; --body: __BODY__px; --turn: 180ms;
  }
  :root[data-mode="light"] {
    color-scheme: light;
    --page: __LIGHT_PAGE__; --ink: __LIGHT_INK__; --muted: __LIGHT_MUTED__;
    --accent: __LIGHT_ACCENT__; --rule: __LIGHT_RULE__;
  }
  @media (prefers-reduced-motion: reduce) { :root { --turn: 0ms; } }

  * { box-sizing: border-box; }
  body { margin: 0; font: var(--body)/1.65 Georgia, 'Times New Roman', serif;
         background: var(--page); color: var(--ink); }
  .visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden;
       clip-path: inset(50%); white-space: nowrap; }
  :focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }

  button { font: inherit; background: transparent; color: var(--ink);
       border: 1px solid var(--rule); border-radius: 4px;
       padding: .6rem 1.1rem; cursor: pointer; }
  button:hover { border-color: var(--accent); }

  /* -- title screen: the cover as an object standing on a shelf -- */
  #title-screen { min-height: 100vh; display: flex; flex-direction: column;
       align-items: center; justify-content: center; gap: 1.4rem;
       padding: 2.5rem 1rem 3.5rem; text-align: center; }
  #shelf { display: flex; flex-direction: column; align-items: center; }
  #cover-art { width: min(58vw, 17rem); aspect-ratio: __COVER_RATIO__;
       object-fit: cover; border: 1px solid var(--rule); border-radius: 2px;
       box-shadow: 0 14px 28px rgb(0 0 0 / .38); }
  #shelf-line { width: min(72vw, 22rem); height: 1px; margin-top: .9rem;
       background: var(--rule); }
  #story-title { font-size: clamp(1.6rem, 6vw, 2.3rem); letter-spacing: .1em;
       margin: .4rem 0 0; font-weight: normal; }
  .byline { color: var(--muted); font-style: italic; margin: 0; }
  #start-actions { display: flex; flex-wrap: wrap; gap: .7rem; justify-content: center; }
  #howto { max-width: var(--measure); text-align: left; color: var(--muted);
       border: 1px solid var(--rule); border-radius: 4px; padding: 1rem 1.2rem; }
  #howto p { margin: .6rem 0; }
  #reading-mode { border: 0; padding: 0; margin: .4rem 0 0;
       display: flex; gap: .5rem; align-items: center; justify-content: center; }
  #reading-mode legend { float: left; color: var(--muted); font-size: .85rem;
       padding: 0 .5rem 0 0; }
  #reading-mode button { padding: .35rem .8rem; font-size: .85rem; }
  #reading-mode button[aria-pressed="true"] { border-color: var(--accent);
       color: var(--accent); }

  /* -- reading view -- */
  main { max-width: var(--measure); margin: 0 auto; padding: 3rem 1.1rem 5rem; }
  #section { transition: opacity var(--turn) ease; }
  #section[data-turning="true"] { opacity: 0; }
  #art { margin: 0 0 1.6rem; }
  #art img { width: __PLATE_WIDTH__; max-width: 100%; display: block; margin: 0 auto;
       border-radius: 3px; }
  #art figcaption { text-align: center; font-size: .85rem; color: var(--muted);
       font-style: italic; margin-top: .45rem; }
  #prose p { margin: 1em 0; }
  #choices-nav { margin-top: 2.4rem; }
  #choices { margin: 0; padding: 0; list-style: none; }
  #choices li { margin: .7rem 0; }
  #choices button { width: 100%; text-align: left; }
  #ending { margin-top: 2.5rem; padding: 1.2rem; border: 1px solid var(--accent);
       text-align: center; font-variant: small-caps; font-size: 1.25rem;
       color: var(--accent); }
  footer { margin-top: 3rem; font-size: .85rem; display: flex; flex-wrap: wrap; gap: .6rem; }
  footer button { padding: .4rem .8rem; color: var(--muted); }
  details { margin-top: 1.4rem; font-size: .9rem; color: var(--muted); }
  #codex article { margin-top: .9rem; }
  #codex h3 { margin: 0 0 .3rem; font-size: 1rem; color: var(--accent); font-weight: normal; }
</style>
</head>
<body>
<div id="title-screen">
  <div id="shelf">
    __COVER_IMG__
    <div id="shelf-line"></div>
  </div>
  <h1 id="story-title">__TITLE__</h1>
  <p class="byline">a QuestFoundry gamebook</p>
  <nav id="start-actions" aria-label="Start reading">
    <button id="begin">Begin</button>
    <button id="continue" hidden>Continue</button>
    <button id="howto-open" aria-expanded="false" aria-controls="howto">How to read</button>
  </nav>
  <div id="howto" hidden>
    <p>Each screen gives you a piece of the story and the moves open to you.
       Choose one and the story turns to what follows.</p>
    <p>Only the moves you can actually make are shown, so what you have done
       earlier changes what you are offered later. There is nothing to track
       yourself.</p>
    <p>Your place is kept with <em>Save</em> and picked up again with
       <em>Continue</em>. <em>Restart</em> begins the story over.</p>
  </div>
  <fieldset id="reading-mode">
    <legend>Reading mode</legend>
    <button data-mode="dark" aria-pressed="true">Dark</button>
    <button data-mode="light" aria-pressed="false">Light</button>
  </fieldset>
</div>

<main id="reader" hidden>
  <article id="section" tabindex="-1" aria-labelledby="section-heading">
    <h2 id="section-heading" class="visually-hidden"></h2>
    <figure id="art" hidden><img alt=""><figcaption></figcaption></figure>
    <div id="prose"></div>
  </article>
  <nav id="choices-nav" aria-label="Choices"><ul id="choices"></ul></nav>
  <div id="ending" hidden></div>
  __CODEX__
  <details id="recap"><summary>The journey so far</summary><ol id="trail"></ol></details>
  <footer>
    <button id="restart">Restart</button>
    <button id="save">Save</button>
    <button id="load">Load</button>
  </footer>
</main>
<p id="announce" class="visually-hidden" role="status" aria-live="polite"></p>

<script>
const STORY = __STORY__;
const KEY = "questfoundry:" + STORY.meta.title;
const MODE_KEY = KEY + ":mode";
const ART = Object.fromEntries((STORY.art || []).map(a => [a.passage, a]));
const RATIO_WIDTH = __RATIO_WIDTH__;
let state = { at: STORY.start, flags: [], trail: [] };

function el(id) { return document.getElementById(id); }
function has(req) { return req.every(f => state.flags.includes(f)); }
function escapeText(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function announce(message) { el("announce").textContent = message; }

function setMode(mode) {
  document.documentElement.dataset.mode = mode;
  for (const b of document.querySelectorAll("#reading-mode button")) {
    b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
  }
  try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* file:// with no storage */ }
}

function paint() {
  const p = STORY.passages[state.at];
  el("section-heading").textContent = "Section " + (state.trail.length + 1);

  const art = ART[state.at], fig = el("art"), img = fig.querySelector("img");
  fig.hidden = !art;
  if (art) {
    img.src = art.image;
    // alt stands in for the picture; the caption sits beside it for everyone
    img.alt = art.alt || "";
    // the ratio is reserved before the image loads, so nothing shifts under
    // the reader mid-turn
    img.style.aspectRatio = (art.ratio || "3:2").replace(":", " / ");
    img.style.width = RATIO_WIDTH[art.ratio] || RATIO_WIDTH["3:2"];
    fig.querySelector("figcaption").textContent = art.caption || "";
  }

  el("prose").innerHTML = p.prose.trim().split(/\\n\\s*\\n/)
    .map(par => "<p>" + escapeText(par) + "</p>").join("");

  const ul = el("choices"); ul.innerHTML = "";
  const end = el("ending");
  if (p.ending) {
    end.hidden = false; end.textContent = p.ending.title;
    el("choices-nav").hidden = true;
  } else {
    end.hidden = true;
    el("choices-nav").hidden = false;
    // choices whose requires are unmet are omitted, never disabled: the
    // reader must not see the machinery (design doc 04 §1)
    p.choices.filter(c => has(c.requires)).forEach(c => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = c.label;
      b.onclick = () => turn(c);
      li.appendChild(b); ul.appendChild(li);
    });
  }

  el("trail").innerHTML = state.trail.map(t => "<li>" + escapeText(t) + "</li>").join("");
  window.scrollTo(0, 0);
  // focus lands on the new section, so a keyboard or screen-reader user
  // starts reading at the top of what just changed
  el("section").focus();
}

function turn(choice) {
  const section = el("section");
  const fade = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 180;
  const advance = () => {
    state.flags = [...new Set([...state.flags, ...choice.grants])];
    state.trail.push(choice.label);
    state.at = choice.to;
    section.dataset.turning = "false";
    paint();
  };
  if (fade === 0) { advance(); return; }
  section.dataset.turning = "true";
  setTimeout(advance, fade);
}

function saved() {
  try { return localStorage.getItem(KEY); } catch (e) { return null; }
}

function openReader() {
  el("title-screen").hidden = true;
  el("reader").hidden = false;
  paint();
}

el("begin").onclick = () => { state = { at: STORY.start, flags: [], trail: [] }; openReader(); };
el("continue").onclick = () => {
  const s = saved();
  if (s) { state = JSON.parse(s); }
  openReader();
};
el("howto-open").onclick = (e) => {
  const panel = el("howto"), open = panel.hidden;
  panel.hidden = !open;
  e.currentTarget.setAttribute("aria-expanded", String(open));
};
for (const b of document.querySelectorAll("#reading-mode button")) {
  b.onclick = () => { setMode(b.dataset.mode); announce(b.dataset.mode + " reading mode"); };
}
el("restart").onclick = () => {
  state = { at: STORY.start, flags: [], trail: [] };
  announce("Restarted."); paint();
};
el("save").onclick = () => {
  try { localStorage.setItem(KEY, JSON.stringify(state)); announce("Place saved."); }
  catch (e) { announce("This browser would not keep your place."); }
};
el("load").onclick = () => {
  const s = saved();
  if (s) { state = JSON.parse(s); announce("Place restored."); paint(); }
  else { announce("No saved place yet."); }
};

function start() {
  if (STORY.cover) { el("cover-art").src = STORY.cover.image; }
  let mode = null;
  try { mode = localStorage.getItem(MODE_KEY); } catch (e) { /* no storage */ }
  if (!mode) { mode = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"; }
  setMode(mode);
  el("continue").hidden = !saved();
}
start();
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


def _cover_img(cover: dict | None) -> str:
    """The cover as an inset object on the shelf. Absent, the title screen
    still stands — type carries it, which is also the honest fallback for a
    story whose cover has not been rendered yet."""
    if not cover:
        return ""
    return f'<img id="cover-art" src="" alt="{_escape(cover.get("alt", ""))}">'


def build_html(project: Project, *, style: ScreenStyle | None = None) -> str:
    style = style or screen_style(DEFAULT_SCREEN_STYLE)
    data = build_runtime(project)
    # the player is one self-contained file, so rendered images inline as
    # data URIs here; the canonical runtime JSON keeps project-root paths
    for entry in data["art"]:
        image_bytes = (project.root / entry["image"]).read_bytes()
        entry["image"] = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    if data.get("cover"):
        cover_bytes = (project.root / data["cover"]["image"]).read_bytes()
        data["cover"]["image"] = (
            "data:image/png;base64," + base64.b64encode(cover_bytes).decode("ascii")
        )
    story = json.dumps(data, ensure_ascii=False)
    # a literal "</script>" inside the JSON would end the script element
    story = story.replace("</", "<\\/")
    title = project.name.replace("<", "&lt;")

    cover = data.get("cover")
    ratio_widths = {
        ratio: f"{round(image_width(style.placement, ratio) * 100)}%"
        for ratio in style.placement
    }
    replacements = {
        "__TITLE__": title,
        "__STORY__": story,
        "__CODEX__": _codex_panel(data["codex"]),
        "__COVER_IMG__": _cover_img(cover),
        "__COVER_RATIO__": (cover["ratio"] if cover else COVER_RATIO).replace(":", " / "),
        "__RATIO_WIDTH__": json.dumps(ratio_widths),
        "__PLATE_WIDTH__": ratio_widths["3:2"],
        "__MEASURE__": str(style.measure_ch),
        "__BODY__": str(style.body_px),
        "__DARK_PAGE__": style.ramp.page,
        "__DARK_INK__": style.ramp.ink,
        "__DARK_MUTED__": style.ramp.muted,
        "__DARK_ACCENT__": style.ramp.accent,
        "__DARK_RULE__": style.ramp.rule,
        "__LIGHT_PAGE__": style.light_ramp.page,
        "__LIGHT_INK__": style.light_ramp.ink,
        "__LIGHT_MUTED__": style.light_ramp.muted,
        "__LIGHT_ACCENT__": style.light_ramp.accent,
        "__LIGHT_RULE__": style.light_ramp.rule,
    }
    # one pass over the template: substituting in sequence would let story
    # prose that happens to contain a later placeholder be rewritten by it
    return _PLACEHOLDER_RE.sub(lambda m: replacements.get(m.group(0), m.group(0)), _TEMPLATE)
