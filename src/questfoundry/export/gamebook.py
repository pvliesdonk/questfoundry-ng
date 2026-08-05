"""Print gamebook pipeline (design doc 04 §4) — the most format-specific
export. Five deterministic steps take the canonical runtime JSON to a
Typst source and a PDF:

1. codeword projection — decide which flags the paper reader must track;
2. residue-variant lowering — fold hidden-choice semantics into explicit
   "if you have X" instructions, since paper cannot hide a choice;
3. numbering & shuffling — seeded section numbers with anti-spoiler
   adjacency constraints;
4. layout — a restrained, consistent Typst template;
5. lint — the paper-specific completeness checks digital reachability
   alone does not cover (codeword-before-test, no dead ends).

Consumes the runtime document only (design doc 04 §1) — no graph access,
so this module works identically pre- and post-DRESS.
"""

from __future__ import annotations

import random
import re
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import typst

from questfoundry.export.style import (
    COVER_RATIO,
    DEFAULT_PRINT_STYLE,
    FULL_BLEED_MIN_PIXELS,
    RATIOS,
    PrintStyle,
    full_bleed_ok,
    image_width,
    print_style,
)

# PDF/UA-1 is the accessibility contract made mechanical: the Typst compiler
# itself refuses a build whose image has no alt text or whose document has no
# title, so a page that would fail a screen reader fails the export instead
# (design doc 04 §7).
PDF_STANDARD = "ua-1"

_ESCAPE_RE = re.compile(r"([\\#$%&~^@*_<>\[\]`])")
_EMPHASIS_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|_(.+?)_")
_LOSSY_RE = re.compile(r"(^#{1,6}\s)|\[[^\]]*\]\([^)]*\)|<[a-zA-Z/][^>]*>", re.MULTILINE)


@dataclass(frozen=True)
class ChoiceLine:
    """One rendered instruction. `text` runs up to and including its final
    "turn to"; `number` is the section it names, which the paperback sets
    bold at the right margin. A group lowered to several codeword clauses
    names several sections, so it keeps them inline and `number` is None."""

    text: str
    number: int | str | None

    @property
    def sentence(self) -> str:
        """The whole instruction as one sentence — the form a style without
        margin numbers sets, and the form the lint and the tests read."""
        return self.text if self.number is None else f"{self.text} {self.number}."


@dataclass(frozen=True)
class Plate:
    """A placed illustration: a typst-root-anchored path, the caption beside
    it, the alt text standing in for it, and the ratio that decides its
    frame (design doc 04 §7)."""

    path: str
    caption: str
    alt: str
    ratio: str


@dataclass(frozen=True)
class Section:
    number: int
    passage: str  # slug
    ending_id: str | None
    ending_title: str | None
    choices: tuple[dict, ...]  # raw {label,to,requires,grants}: structural, for lint & rendering
    prose_typst: str
    hoisted_lines: tuple[str, ...]  # bold write-down lines, rendered
    choice_lines: tuple[ChoiceLine, ...]  # one instruction per label group, display order
    illustration: Plate | None


@dataclass
class Gamebook:
    sections: list[Section]
    codewords: dict[str, str]  # flag id -> codeword, projected flags only
    fallback_flags: list[str]  # flag ids whose codeword was derived, not DRESS-authored
    warnings: list[str]
    typst: str
    style: PrintStyle
    cover: Plate | None = None


# -- text helpers -----------------------------------------------------------


def _flag_slug(flag_id: str) -> str:
    return flag_id.split(":", 1)[1]


def _escape_typst(text: str) -> str:
    return _ESCAPE_RE.sub(r"\\\1", text)


def _convert_paragraph(text: str, warnings: list[str], where: str) -> str:
    if _LOSSY_RE.search(text):
        warnings.append(f"{where}: a markdown construct did not survive the print mapping")
    out: list[str] = []
    last = 0
    for m in _EMPHASIS_RE.finditer(text):
        out.append(_escape_typst(text[last : m.start()]))
        if m.group(1) is not None:
            out.append(f"#strong[{_escape_typst(m.group(1))}]")
        elif m.group(2) is not None:
            out.append(f"#emph[{_escape_typst(m.group(2))}]")
        else:
            out.append(f"#emph[{_escape_typst(m.group(3))}]")
        last = m.end()
    out.append(_escape_typst(text[last:]))
    return "".join(out)


def _convert_prose(text: str, warnings: list[str], where: str) -> str:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n\n".join(_convert_paragraph(p, warnings, where) for p in paragraphs)


def _join_and(words: list[str]) -> str:
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + " and " + words[-1]


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _group_by_label(choices: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for c in choices:
        groups.setdefault(c["label"], []).append(c)
    return groups


# -- step 1: codeword projection --------------------------------------------


def _projected_flags(passages: dict) -> set[str]:
    tested: set[str] = set()
    for p in passages.values():
        for c in p["choices"]:
            tested.update(c["requires"])
    return tested


def _derive_codeword(slug: str, used: set[str]) -> str:
    tokens = slug.split("-")
    idx = len(tokens) - 1
    word = tokens[idx].upper()
    while (len(word) < 3 or word[:12] in used) and idx > 0:
        idx -= 1
        word = tokens[idx].upper() + word
    return word[:12]


def _assign_codewords(projected: set[str], flags: dict) -> tuple[dict[str, str], list[str]]:
    codewords: dict[str, str] = {}
    used: set[str] = set()
    # stored codewords win outright and reserve their word first, so
    # fallback derivation for everyone else never collides with them.
    for fid in sorted(projected):
        stored = flags.get(fid, {}).get("codeword")
        if stored:
            codewords[fid] = stored
            used.add(stored)
    fallback: list[str] = []
    for fid in sorted(projected):
        if fid in codewords:
            continue
        word = _derive_codeword(_flag_slug(fid), used)
        codewords[fid] = word
        used.add(word)
        fallback.append(fid)
    return codewords, fallback


def _hoisted_grants(passages: dict, projected: set[str]) -> dict[str, set[str]]:
    """Flag ids whose write-down instruction is common to every incoming
    choice of a passage, and therefore hoisted onto that section instead
    of repeated inline on each choice line."""
    incoming: dict[str, list[dict]] = {}
    for p in passages.values():
        for c in p["choices"]:
            incoming.setdefault(c["to"], []).append(c)
    hoisted: dict[str, set[str]] = {}
    for pid, choices in incoming.items():
        common = set(choices[0]["grants"])
        for c in choices[1:]:
            common &= set(c["grants"])
        hoisted[pid] = common & projected
    return hoisted


# -- step 2: residue-variant lowering ----------------------------------------


def _tail(grant_words: list[str], number: int | str) -> str:
    return f"{_tail_prefix(grant_words)} {number}"


def _tail_prefix(grant_words: list[str]) -> str:
    """The instruction up to but not including the section it names — the
    split the paperback needs, which sets that number bold at the right
    margin instead of inline (design doc 04 §7)."""
    if grant_words:
        noun = "codeword" if len(grant_words) == 1 else "codewords"
        return f"write down the {noun} {_join_and(grant_words)}, then turn to"
    return "turn to"


def _render_choice_group(
    label: str,
    group: list[dict],
    numbers: dict[str, int],
    hoisted: dict[str, set[str]],
    codewords: dict[str, str],
    projected: set[str],
) -> ChoiceLine:
    def inline_grants(c: dict) -> list[str]:
        common = hoisted.get(c["to"], set())
        return sorted(codewords[f] for f in c["grants"] if f in projected and f not in common)

    # a dangling target (choice.to not a real passage) has no section
    # number to print; fall back to the raw slug so layout never crashes
    # on a malformed document — lint_gamebook is what rejects it.
    def number_of(c: dict) -> int | str:
        return numbers.get(c["to"], c["to"])

    if len(group) == 1:
        c = group[0]
        prefix = _tail_prefix(inline_grants(c))
        if c["requires"]:
            reqs = _join_and(sorted(codewords[f] for f in c["requires"]))
            text = f"If you have {reqs}, you may {_lower_first(label)}: {prefix}"
        else:
            text = f"{label}: {prefix}"
        return ChoiceLine(text=text, number=number_of(c))

    gated = sorted(
        (c for c in group if c["requires"]),
        key=lambda c: tuple(sorted(codewords[f] for f in c["requires"])),
    )
    ungated = [c for c in group if not c["requires"]]
    clauses = []
    for c in gated:
        reqs = _join_and(sorted(codewords[f] for f in c["requires"]))
        clauses.append(f"if you have {reqs}, {_tail(inline_grants(c), number_of(c))}")
    for c in ungated:
        clauses.append(f"otherwise, {_tail(inline_grants(c), number_of(c))}")
    # several clauses name several sections, so none of them can go to the
    # margin; the group keeps every number inline
    return ChoiceLine(text=f"{label}: " + "; ".join(clauses) + ".", number=None)


# -- step 3: numbering & shuffling -------------------------------------------


def _assign_numbers(passages: dict, start: str, seed: int) -> tuple[dict[str, int], list[str]]:
    others = sorted(pid for pid in passages if pid != start)
    rng = random.Random(seed)
    endings = sorted(pid for pid, p in passages.items() if p.get("ending"))
    # a dangling "turn to" (choice.to not a real passage) is a lint error,
    # not a numbering concern — skip it here so a broken document can still
    # be laid out and then rejected with a precise lint message.
    edges = [
        (pid, c["to"]) for pid, p in passages.items() for c in p["choices"] if c["to"] in passages
    ]
    sibling_groups: list[list[str]] = []
    for p in passages.values():
        for group in _group_by_label(p["choices"]).values():
            targets = [c["to"] for c in group if c["to"] in passages]
            if len(targets) > 1:
                sibling_groups.append(targets)

    def score(assignment: dict[str, int]) -> list[str]:
        violations = []
        for src, dst in edges:
            if abs(assignment[src] - assignment[dst]) < 2:
                violations.append(
                    f"choice edge {src}->{dst}: sections "
                    f"{assignment[src]} and {assignment[dst]} are adjacent"
                )
        for group in sibling_groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = assignment[group[i]], assignment[group[j]]
                    if abs(a - b) < 2:
                        violations.append(
                            f"variant siblings {group[i]}/{group[j]}: "
                            f"sections {a} and {b} are adjacent"
                        )
        for i in range(len(endings)):
            for j in range(i + 1, len(endings)):
                a, b = assignment[endings[i]], assignment[endings[j]]
                if abs(a - b) < 2:
                    violations.append(
                        f"endings {endings[i]}/{endings[j]}: sections {a} and {b} are adjacent"
                    )
        return violations

    best_assignment: dict[str, int] | None = None
    best_violations: list[str] | None = None
    for _ in range(10_000):
        order = list(others)
        rng.shuffle(order)
        assignment = {start: 1, **{pid: i + 2 for i, pid in enumerate(order)}}
        violations = score(assignment)
        if not violations:
            return assignment, []
        if best_violations is None or len(violations) < len(best_violations):
            best_assignment, best_violations = assignment, violations
    assert best_assignment is not None and best_violations is not None
    return best_assignment, [f"numbering: {v}" for v in best_violations]


# -- step 4: layout -----------------------------------------------------------


def _typst_string(text: str) -> str:
    """A Typst string literal — quotes and backslashes only. Distinct from
    `_escape_typst`, which escapes *markup*: putting markup escapes inside a
    string literal would print the backslashes."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _codeword_log(n: int) -> str:
    rows = max(16, n * 2)
    lines = "\n".join("#v(1.4em)#line(length: 100%, stroke: 0.4pt + qf-rule)" for _ in range(rows))
    return f"= Codeword Log\n{lines}\n"


def _preamble(style: PrintStyle, title: str) -> str:
    """Page geometry, type, colour roles and the reusable furniture, all
    read off the style record. The running head is a `context` block: it
    queries the section marks laid down on the current spread, so the head
    reports what the reader can actually see rather than a counter that
    guesses (design doc 04 §7)."""
    ramp = style.ramp
    head = (
        """
#let qf-spread-range() = context {
  // the facing pages a reader has open; the head names the sections across both
  let p = here().page()
  let spread = if calc.even(p) { (p, p + 1) } else { (p - 1, p) }
  let marks = query(<qf-section>)
  let here-marks = marks.filter(m => m.location().page() in spread)
  let before = marks.filter(m => m.location().page() < spread.at(0))
  let lo = if here-marks.len() > 0 {
    here-marks.first().value
  } else if before.len() > 0 { before.last().value } else { none }
  let hi = if here-marks.len() > 0 { here-marks.last().value } else { lo }
  if lo == none { none } else if lo == hi { [#lo] } else { [#lo#sym.dash.en#hi] }
}

#set page(header: context {
  let range = qf-spread-range()
  if range != none and here().page() > 1 {
    set text(size: 8pt, fill: qf-muted, tracking: 0.06em)
    let folio = counter(page).display()
    if calc.even(here().page()) {
      grid(columns: (auto, 1fr), align(left)[#folio], align(right)[#range])
    } else {
      grid(columns: (1fr, auto), align(left)[#range], align(right)[#folio])
    }
  }
})
"""
        if style.running_heads
        else ""
    )
    return f"""#set document(title: {_typst_string(title)}, author: "QuestFoundry")

#let qf-page = rgb({_typst_string(ramp.page)})
#let qf-ink = rgb({_typst_string(ramp.ink)})
#let qf-muted = rgb({_typst_string(ramp.muted)})
#let qf-accent = rgb({_typst_string(ramp.accent)})
#let qf-rule = rgb({_typst_string(ramp.rule)})

#set page(
  width: {style.page_width}mm,
  height: {style.page_height}mm,
  margin: (
    inside: {style.margin_inside}mm, outside: {style.margin_outside}mm,
    top: {style.margin_top}mm, bottom: {style.margin_bottom}mm,
  ),
  binding: left,
  fill: qf-page,
)
#set text(size: {style.body_size}pt, fill: qf-ink, lang: "en")
#set par(justify: true, leading: {style.leading}em)
{head}
// A section head is a real heading, so the PDF outline is the book's own
// numbering and a screen reader can jump section to section.
#show heading.where(level: 1): it => block(above: 1.5em, below: 0.85em)[
  #set text(size: {style.section_size}pt, weight: "bold", fill: qf-accent, tracking: 0.08em)
  #it.body
]

#let qf-section(n, body) = {{
  [#metadata(n)<qf-section>]
  heading(level: 1)[#n]
  body
}}

// Hanging indent, and the section named at the right margin in bold: the
// reader's eye finds the number without reading the sentence again.
#let qf-instruction(body, number) = block(width: 100%, above: 1.15em, breakable: false)[
  #set par(hanging-indent: 1.4em, justify: false)
  #body#if number != none [ #box(width: 1fr) #text(weight: "bold", fill: qf-accent)[#number]]
]

// A plate sits at the measure (or a fraction of it for a tall frame); the
// height always follows the ratio, so nothing is ever letterboxed.
#let qf-plate(path, alt, caption, fraction) = block(
  width: 100%, above: 1.1em, below: 1.1em, breakable: false,
)[
  #align(center)[
    #image(path, width: fraction * 100%, alt: alt)
    #if caption != "" [
      #v(0.35em)
      #text(size: 8.5pt, style: "italic", fill: qf-muted)[#caption]
    ]
  ]
]
"""


def _render_plate(plate: Plate, style: PrintStyle) -> str:
    fraction = image_width(style.placement, plate.ratio)
    return (
        f"#qf-plate({_typst_string(plate.path)}, {_typst_string(plate.alt)}, "
        f"{_typst_string(plate.caption)}, {fraction})"
    )


def _render_section(s: Section, style: PrintStyle) -> str:
    body: list[str] = []
    if s.illustration:
        body.append(_render_plate(s.illustration, style))
        body.append("")
    body.append(s.prose_typst)
    body.append("")
    if s.ending_id:
        title = _escape_typst(s.ending_title or "")
        body.append(
            '#align(center)[#text(style: "italic", size: 12pt, fill: qf-accent)'
            f"[THE END --- {title}]]"
        )
        body.append("#align(center)[See the Ending Index.]")
    else:
        if s.hoisted_lines:
            body.append("\n\n".join(s.hoisted_lines))
            body.append("")
        for line in s.choice_lines:
            # the parenthesised call form: inside a markup content block a
            # bare `[7]` is the literal characters, not a nested block
            number = "none" if line.number is None else f"[{line.number}]"
            body.append(f"#qf-instruction([{line.text}], {number})")
    rendered = "\n".join(body)
    out = f"#qf-section({s.number})[\n{rendered}\n]\n"
    return out + "#pagebreak()\n" if style.section_per_page else out


def _cover_block(cover: Plate, style: PrintStyle, *, full_bleed: bool) -> str:
    """Full-bleed when the rendered file clears the 300dpi floor for this
    trim; otherwise the honest fallback — the same art inset on its own
    page, never upscaled into softness (design plan, ratified decision 1)."""
    path, alt = _typst_string(cover.path), _typst_string(cover.alt)
    if full_bleed:
        return (
            "#page(margin: 0pt, header: none)[\n"
            f'  #image({path}, width: 100%, height: 100%, fit: "cover", alt: {alt})\n'
            "]\n"
        )
    fraction = image_width(style.placement, cover.ratio)
    return (
        "#page(header: none)[\n"
        "  #align(center + horizon)[\n"
        f"    #image({path}, width: {fraction * 100}%, alt: {alt})\n"
        "  ]\n"
        "]\n"
    )


def _layout(
    runtime: dict,
    sections: list[Section],
    projected: set[str],
    warnings: list[str],
    *,
    style: PrintStyle,
    cover: Plate | None = None,
    cover_full_bleed: bool = True,
) -> str:
    title = runtime["meta"]["title"]
    parts: list[str] = [_preamble(style, title)]

    if cover is not None:
        # the image already carries the title (drawn by the image backend or
        # composited at illustrate time), so the layout only places the art
        parts.append(_cover_block(cover, style, full_bleed=cover_full_bleed))

    parts.append(
        "#page(header: none)[\n"
        "#align(center + horizon)[\n"
        f'  #text(size: 24pt, weight: "bold")[{_escape_typst(title)}]\n'
        "  #v(1em)\n"
        '  #text(size: 12pt, style: "italic", fill: qf-muted)[a QuestFoundry gamebook]\n'
        "]\n]\n"
    )

    howto = [
        "= How to Play",
        "",
        "This book is made of numbered sections, not pages: when an",
        "instruction tells you to turn to a section, find that number,",
        "not the next page. Begin at section 1. The running head on each",
        "page names the sections printed across that spread.",
        "",
        "Each section ends with one or more instructions. Follow the one",
        "that matches your situation and turn to the section it names —",
        "the number is set in bold at the right-hand margin.",
    ]
    if projected:
        howto += [
            "",
            "Some sections tell you to write a codeword down in the",
            "Codeword Log. Some instructions only apply if you have",
            "written down a particular codeword — you may only follow",
            "those once you have recorded the word.",
        ]
    parts.append("\n".join(howto) + "\n#pagebreak()\n")

    if projected:
        parts.append(_codeword_log(len(projected)))
        parts.append("#pagebreak()\n")

    for s in sections:
        parts.append(_render_section(s, style))

    codex = runtime.get("codex") or []
    if codex:
        parts.append("#pagebreak()\n= Codex\n")
        for entry in codex:
            title_t = _escape_typst(entry["title"])
            body_t = _convert_prose(entry["body"], warnings, f"codex entry {entry['entity']!r}")
            parts.append(f"== {title_t}\n{body_t}\n")

    parts.append("#pagebreak()\n= Ending Index\n")
    for s in sorted((s for s in sections if s.ending_id), key=lambda s: s.ending_id or ""):
        parts.append(f"- {_escape_typst(s.ending_title or '')}")

    return "\n".join(parts) + "\n"


# -- public entry points ------------------------------------------------------


def _relative_to_root(path: Path, root: Path | None) -> str:
    # typst resolves a leading-slash path from its compilation root, never
    # the OS filesystem root — an absolute OS path here fails compilation
    # (found live, M7 exit run)
    if root is None:
        raise ValueError("images_dir requires root (the typst compilation root)")
    return "/" + path.resolve().relative_to(root.resolve()).as_posix()


def _image_size(path: Path) -> tuple[int, int] | None:
    from PIL import Image

    try:
        with Image.open(path) as img:
            return img.size
    except OSError:
        return None


def build_gamebook(
    runtime: dict,
    *,
    seed: int,
    images_dir: Path | None = None,
    root: Path | None = None,
    style: PrintStyle | None = None,
) -> Gamebook:
    style = style or print_style(DEFAULT_PRINT_STYLE)
    warnings: list[str] = []
    passages: dict = runtime["passages"]
    flags: dict = runtime.get("flags", {})
    start = runtime["start"]

    projected = _projected_flags(passages)
    codewords, fallback_flags = _assign_codewords(projected, flags)
    hoisted = _hoisted_grants(passages, projected)
    numbers, numbering_warnings = _assign_numbers(passages, start, seed)
    warnings.extend(numbering_warnings)

    art_by_passage = {a["passage"]: a for a in runtime.get("art", [])}

    sections: list[Section] = []
    for pid, p in passages.items():
        ending = p.get("ending")
        prose_typst = _convert_prose(p["prose"], warnings, f"passage {pid!r}")
        hoisted_ids = sorted(hoisted.get(pid, set()), key=lambda f: codewords[f])
        hoisted_lines = tuple(
            f"#strong[Write down the codeword {codewords[f]}.]" for f in hoisted_ids
        )
        choice_lines: tuple[ChoiceLine, ...] = ()
        if not ending:
            choice_lines = tuple(
                _render_choice_group(label, group, numbers, hoisted, codewords, projected)
                for label, group in _group_by_label(p["choices"]).items()
            )
        illustration = None
        if images_dir is not None:
            entry = art_by_passage.get(pid)
            image_path = images_dir / f"{pid}.png"
            if entry is not None and image_path.exists():
                illustration = Plate(
                    path=_relative_to_root(image_path, root),
                    caption=entry.get("caption", ""),
                    alt=entry.get("alt", ""),
                    ratio=entry.get("ratio", "3:2"),
                )
                warnings.extend(_plate_warnings(illustration, f"passage {pid!r}"))
        sections.append(
            Section(
                number=numbers[pid],
                passage=pid,
                ending_id=ending["id"] if ending else None,
                ending_title=ending["title"] if ending else None,
                choices=tuple(p["choices"]),
                prose_typst=prose_typst,
                hoisted_lines=hoisted_lines,
                choice_lines=choice_lines,
                illustration=illustration,
            )
        )
    sections.sort(key=lambda s: s.number)

    cover_plate: Plate | None = None
    cover_full_bleed = True
    cover_entry = runtime.get("cover")
    if cover_entry is not None and images_dir is not None:
        cover_file = images_dir / "cover.png"
        if cover_file.exists():
            cover_plate = Plate(
                path=_relative_to_root(cover_file, root),
                caption="",
                alt=cover_entry.get("alt", ""),
                ratio=cover_entry.get("ratio", COVER_RATIO),
            )
            warnings.extend(_plate_warnings(cover_plate, "the cover"))
            size = _image_size(cover_file)
            cover_full_bleed = size is None or full_bleed_ok(size)
            if not cover_full_bleed:
                warnings.append(
                    f"cover: the rendered image is {size[0]}×{size[1]}px, below the "  # type: ignore[index]
                    f"{FULL_BLEED_MIN_PIXELS[0]}×{FULL_BLEED_MIN_PIXELS[1]}px needed for "
                    "a 300dpi full-bleed page — placed inset instead; re-render the cover "
                    "at a higher resolution for a full-bleed front"
                )

    typst_source = _layout(
        runtime,
        sections,
        projected,
        warnings,
        style=style,
        cover=cover_plate,
        cover_full_bleed=cover_full_bleed,
    )

    return Gamebook(
        sections=sections,
        codewords=codewords,
        fallback_flags=sorted(fallback_flags),
        warnings=warnings,
        typst=typst_source,
        style=style,
        cover=cover_plate,
    )


def _plate_warnings(plate: Plate, where: str) -> list[str]:
    if plate.ratio in RATIOS:
        return []
    return [
        f"{where}: unknown image ratio {plate.ratio!r}; placed as landscape. Use one of "
        f"{', '.join(RATIOS)} in the brief"
    ]


def lint_gamebook(book: Gamebook) -> list[str]:
    """Paper-specific completeness checks the digital runtime validator
    does not cover: every 'turn to' resolves, every gate is satisfiable
    by the time a reader can test it, no section is orphaned or dead."""
    errors: list[str] = []
    by_passage = {s.passage: s for s in book.sections}

    # Alt text is checked here rather than left to the compiler: PDF/UA-1
    # rejects the build either way, but "missing alt text" from Typst names
    # no passage and no file to fix.
    for placed, where in [
        *((s.illustration, f"section {s.number} ({s.passage})") for s in book.sections),
        (book.cover, "the cover"),
    ]:
        if placed is not None and not placed.alt.strip():
            errors.append(
                f"{where}: the illustration has no alt text — add `alt:` to its brief in "
                "art/ (one sentence describing the picture) or rerun DRESS; a PDF/UA-1 "
                "build is refused without it"
            )

    if len(by_passage) != len(book.sections):
        errors.append("duplicate section: a passage was laid out more than once")
    if len({s.number for s in book.sections}) != len(book.sections):
        errors.append("duplicate section number")

    starts = [s for s in book.sections if s.number == 1]
    if not starts:
        errors.append("no section is numbered 1 (start)")
        return errors
    start = starts[0]

    for s in book.sections:
        for c in s.choices:
            if c["to"] not in by_passage:
                errors.append(
                    f"section {s.number} ({s.passage}): 'turn to' target {c['to']!r} "
                    "does not resolve to a section"
                )

    # Only gate-relevant flags (those some choice tests) belong in the walk
    # state key; an unconsumed grant cannot change a takeable choice, and
    # tracking it makes the state a powerset over grants (the cosmetic-keyword
    # OOM — see runtime_json.validate_runtime and I13). `reachable[pid]` is read
    # below for the codeword-before-test lint; projecting to gate-relevant keeps
    # every flag a `requires` could test, so that check is unchanged.
    gate_relevant = frozenset(
        f for sec in by_passage.values() for c in sec.choices for f in c["requires"]
    )
    reachable: dict[str, set[frozenset]] = {}
    endings_reached: set[str] = set()
    took_any: set[str] = set()
    frontier: deque[tuple[str, frozenset]] = deque([(start.passage, frozenset())])
    seen: set[tuple[str, frozenset]] = set()
    while frontier:
        pid, held = frontier.popleft()
        if (pid, held) in seen or pid not in by_passage:
            continue
        seen.add((pid, held))
        reachable.setdefault(pid, set()).add(held)
        sec = by_passage[pid]
        if sec.ending_id:
            endings_reached.add(sec.ending_id)
            continue
        for c in sec.choices:
            if set(c["requires"]) <= held:
                took_any.add(pid)
                if c["to"] in by_passage:
                    frontier.append((c["to"], (held | set(c["grants"])) & gate_relevant))

    for s in book.sections:
        if s.passage not in reachable:
            errors.append(f"section {s.number} ({s.passage}) is not reachable from section 1")
            continue
        if s.ending_id:
            if s.ending_id not in endings_reached:
                errors.append(f"ending {s.ending_id} (section {s.number}) is never reached")
            continue
        if not s.choices:
            errors.append(f"section {s.number} ({s.passage}) has no choices and is not an ending")
        elif s.passage not in took_any:
            errors.append(
                f"section {s.number} ({s.passage}) has no takeable instruction on any "
                "reachable route (a paper dead end)"
            )
        for c in s.choices:
            if c["requires"] and not any(
                set(c["requires"]) <= held for held in reachable[s.passage]
            ):
                words = _join_and(sorted(book.codewords.get(f, f) for f in c["requires"]))
                errors.append(
                    f"section {s.number} ({s.passage}): instruction to {c['to']!r} tests "
                    f"codeword(s) {words} that are never granted before reaching this section"
                )

    return errors


def compile_pdf(typst_source: str, *, root: Path | None = None) -> bytes:
    # the temp file must live inside `root` (typst refuses input outside
    # its project root), and stay cleaned up after compilation.
    with tempfile.TemporaryDirectory(dir=root) as d:
        path = Path(d) / "book.typ"
        path.write_text(typst_source, encoding="utf-8")
        return typst.compile(
            str(path),
            root=str(root) if root is not None else None,
            pdf_standards=PDF_STANDARD,
        )
