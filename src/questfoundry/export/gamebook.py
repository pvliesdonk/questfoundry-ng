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

_ESCAPE_RE = re.compile(r"([\\#$%&~^@*_<>\[\]`])")
_EMPHASIS_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|_(.+?)_")
_LOSSY_RE = re.compile(r"(^#{1,6}\s)|\[[^\]]*\]\([^)]*\)|<[a-zA-Z/][^>]*>", re.MULTILINE)

_PAGE_SETUP = """#set page(width: 130mm, height: 200mm, margin: (x: 16mm, y: 18mm))
#set text(size: 10.5pt)
#set par(justify: true, leading: 0.65em)
"""


@dataclass(frozen=True)
class Section:
    number: int
    passage: str  # slug
    ending_id: str | None
    ending_title: str | None
    choices: tuple[dict, ...]  # raw {label,to,requires,grants}: structural, for lint & rendering
    prose_typst: str
    hoisted_lines: tuple[str, ...]  # bold write-down lines, rendered
    choice_lines: tuple[str, ...]  # one rendered instruction per label group, display order
    illustration: tuple[str, str] | None  # (typst-root-anchored "/…" image path, caption)


@dataclass
class Gamebook:
    sections: list[Section]
    codewords: dict[str, str]  # flag id -> codeword, projected flags only
    fallback_flags: list[str]  # flag ids whose codeword was derived, not DRESS-authored
    warnings: list[str]
    typst: str


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
    if grant_words:
        noun = "codeword" if len(grant_words) == 1 else "codewords"
        return f"write down the {noun} {_join_and(grant_words)}, then turn to {number}"
    return f"turn to {number}"


def _render_choice_group(
    label: str,
    group: list[dict],
    numbers: dict[str, int],
    hoisted: dict[str, set[str]],
    codewords: dict[str, str],
    projected: set[str],
) -> str:
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
        tail = _tail(inline_grants(c), number_of(c))
        if c["requires"]:
            reqs = _join_and(sorted(codewords[f] for f in c["requires"]))
            return f"If you have {reqs}, you may {_lower_first(label)}: {tail}."
        return f"{label}: {tail}."

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
    return f"{label}: " + "; ".join(clauses) + "."


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


def _codeword_log(n: int) -> str:
    rows = max(16, n * 2)
    lines = "\n".join("#v(1.4em)#line(length: 100%)" for _ in range(rows))
    return f"= Codeword Log\n{lines}\n"


def _render_section(s: Section) -> str:
    parts = [f'#align(center)[#text(size: 13pt, weight: "bold")[--- {s.number} ---]]', ""]
    if s.illustration:
        path, caption = s.illustration
        parts.append(f'#align(center)[#image("{path}", width: 80%)]')
        if caption:
            cap = _escape_typst(caption)
            parts.append(f'#align(center)[#text(size: 9pt, style: "italic")[{cap}]]')
        parts.append("")
    parts.append(s.prose_typst)
    parts.append("")
    if s.ending_id:
        title = _escape_typst(s.ending_title or "")
        parts.append(f'#align(center)[#text(style: "italic", size: 12pt)[THE END --- {title}]]')
        parts.append("#align(center)[See the Ending Index.]")
    else:
        if s.hoisted_lines:
            parts.append("\n\n".join(s.hoisted_lines))
            parts.append("")
        if s.choice_lines:
            parts.append(" \\\n".join(s.choice_lines))
    parts.append("#pagebreak()")
    return "\n".join(parts) + "\n"


def _layout(
    runtime: dict,
    sections: list[Section],
    projected: set[str],
    warnings: list[str],
) -> str:
    title = runtime["meta"]["title"]
    parts: list[str] = [_PAGE_SETUP]

    parts.append(
        "#align(center + horizon)[\n"
        f'  #text(size: 24pt, weight: "bold")[{_escape_typst(title)}]\n'
        "  #v(1em)\n"
        '  #text(size: 12pt, style: "italic")[a QuestFoundry gamebook]\n'
        "]\n#pagebreak()\n"
    )

    howto = [
        "= How to Play",
        "",
        "This book is made of numbered sections, not pages: when an",
        "instruction tells you to turn to a section, find that number,",
        "not the next page. Begin at section 1.",
        "",
        "Each section ends with one or more instructions. Follow the one",
        "that matches your situation and turn to the section it names.",
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
        parts.append(_render_section(s))

    codex = runtime.get("codex") or []
    if codex:
        parts.append("= Codex\n")
        for entry in codex:
            title_t = _escape_typst(entry["title"])
            body_t = _convert_prose(entry["body"], warnings, f"codex entry {entry['entity']!r}")
            parts.append(f"== {title_t}\n{body_t}\n")
        parts.append("#pagebreak()\n")

    parts.append("= Ending Index\n")
    for s in sorted((s for s in sections if s.ending_id), key=lambda s: s.ending_id or ""):
        parts.append(f"- {_escape_typst(s.ending_title or '')}")

    return "\n".join(parts) + "\n"


# -- public entry points ------------------------------------------------------


def build_gamebook(
    runtime: dict, *, seed: int, images_dir: Path | None = None, root: Path | None = None
) -> Gamebook:
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
        choice_lines: tuple[str, ...] = ()
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
                # typst resolves a leading-slash path from its compilation
                # root, never the OS filesystem root — an absolute OS path
                # here fails compilation (found live, M7 exit run)
                if root is None:
                    raise ValueError("images_dir requires root (the typst compilation root)")
                relative = image_path.resolve().relative_to(root.resolve()).as_posix()
                illustration = (f"/{relative}", entry.get("caption", ""))
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

    typst_source = _layout(runtime, sections, projected, warnings)

    return Gamebook(
        sections=sections,
        codewords=codewords,
        fallback_flags=sorted(fallback_flags),
        warnings=warnings,
        typst=typst_source,
    )


def lint_gamebook(book: Gamebook) -> list[str]:
    """Paper-specific completeness checks the digital runtime validator
    does not cover: every 'turn to' resolves, every gate is satisfiable
    by the time a reader can test it, no section is orphaned or dead."""
    errors: list[str] = []
    by_passage = {s.passage: s for s in book.sections}

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
        return typst.compile(str(path), root=str(root) if root is not None else None)
