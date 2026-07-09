"""Print gamebook pipeline (design doc 04 §4): codeword projection,
residue-variant lowering, seeded numbering, Typst layout, and lint —
against hand-built runtime documents for the unit cases and the golden
story for the end-to-end ones.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from questfoundry.cli import app
from questfoundry.export.gamebook import build_gamebook, compile_pdf, lint_gamebook
from questfoundry.export.runtime_json import build_runtime
from questfoundry.project import load_project


def _rt(passages: dict, *, start: str, flags: dict | None = None, codex=None, art=None) -> dict:
    return {
        "format": "questfoundry-runtime",
        "version": 1,
        "meta": {"title": "Test Book", "scope": "micro"},
        "start": start,
        "passages": passages,
        "flags": flags or {},
        "entities": {},
        "codex": codex or [],
        "art": art or [],
    }


def _choice(label: str, to: str, *, requires=(), grants=()) -> dict:
    return {"label": label, "to": to, "requires": list(requires), "grants": list(grants)}


def _passage(prose: str, choices: list[dict] | None = None, ending: dict | None = None) -> dict:
    return {"prose": prose, "choices": choices or [], "ending": ending}


# -- golden-story tests -------------------------------------------------------


def test_determinism_same_seed_identical_different_seed_differs(golden):
    runtime = build_runtime(golden)
    a1 = build_gamebook(runtime, seed=7)
    a2 = build_gamebook(runtime, seed=7)
    assert a1.typst == a2.typst
    assert {s.passage: s.number for s in a1.sections} == {s.passage: s.number for s in a2.sections}

    b = build_gamebook(runtime, seed=8)
    assert {s.passage: s.number for s in a1.sections} != {s.passage: s.number for s in b.sections}
    assert a1.typst != b.typst


def test_start_is_section_one(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    start_sections = [s for s in book.sections if s.number == 1]
    assert len(start_sections) == 1
    assert start_sections[0].passage == runtime["start"]


def test_numbering_constraints_scored_correctly_on_golden(golden):
    """Independently recompute all three constraint families against the
    algorithm's own assignment; every counted violation must show up as
    a numbering warning, and if none are counted, none may be reported."""
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    numbers = {s.passage: s.number for s in book.sections}
    passages = runtime["passages"]

    violations = []
    for pid, p in passages.items():
        for c in p["choices"]:
            if abs(numbers[pid] - numbers[c["to"]]) < 2:
                violations.append(("edge", pid, c["to"]))
    groups: dict[tuple[str, str], list[str]] = {}
    for pid, p in passages.items():
        by_label: dict[str, list[str]] = {}
        for c in p["choices"]:
            by_label.setdefault(c["label"], []).append(c["to"])
        for label, targets in by_label.items():
            if len(targets) > 1:
                groups[(pid, label)] = targets
    for targets in groups.values():
        for i in range(len(targets)):
            for j in range(i + 1, len(targets)):
                if abs(numbers[targets[i]] - numbers[targets[j]]) < 2:
                    violations.append(("sibling", targets[i], targets[j]))
    endings = [pid for pid, p in passages.items() if p.get("ending")]
    for i in range(len(endings)):
        for j in range(i + 1, len(endings)):
            if abs(numbers[endings[i]] - numbers[endings[j]]) < 2:
                violations.append(("ending", endings[i], endings[j]))

    numbering_warnings = [w for w in book.warnings if w.startswith("numbering:")]
    assert len(numbering_warnings) == len(violations)
    if not violations:
        assert numbering_warnings == []


def test_compile_pdf_golden_returns_pdf_bytes(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    pdf = compile_pdf(book.typst)
    assert pdf.startswith(b"%PDF")


def test_lint_golden_zero_errors_and_turn_tos_resolve(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    errors = lint_gamebook(book)
    assert errors == []
    numbers = {s.passage for s in book.sections}
    for s in book.sections:
        for c in s.choices:
            assert c["to"] in numbers


def test_ending_index_titles_no_numbers_and_no_choice_lines(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    ending_sections = [s for s in book.sections if s.ending_id]
    assert ending_sections
    for s in ending_sections:
        assert s.choice_lines == ()
    index_block = book.typst.split("= Ending Index")[1]
    for s in ending_sections:
        assert s.ending_title in index_block
        # the title appears as a bare bullet line, not "N Title"
        for line in index_block.splitlines():
            if s.ending_title in line:
                assert line.strip().startswith("-")


def test_codex_presence_matches_runtime(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    assert ("= Codex" in book.typst) == bool(runtime.get("codex"))


def test_gamebook_smoke_shape(golden):
    runtime = build_runtime(golden)
    book = build_gamebook(runtime, seed=1)
    assert len(book.sections) == len(runtime["passages"])
    assert book.typst.startswith("#set page")


# -- hand-built unit tests ----------------------------------------------------


def test_fallback_codeword_derivation_and_stored_wins():
    passages = {
        "start": _passage("Start.", [_choice("Go", "p2", grants=["flag:a-truth"])]),
        "p2": _passage(
            "Two.", [_choice("Go", "p3", requires=["flag:a-truth"], grants=["flag:b-truth"])]
        ),
        "p3": _passage(
            "Three.", [_choice("Go", "p4", requires=["flag:b-truth"], grants=["flag:sees-ok"])]
        ),
        "p4": _passage(
            "Four.",
            [_choice("Go", "p5", requires=["flag:sees-ok"], grants=["flag:custom-one"])],
        ),
        "p5": _passage("Five.", [_choice("Go", "end", requires=["flag:custom-one"])]),
        "end": _passage("The end.", ending={"id": "e-end", "title": "The End"}),
    }
    flags = {
        "flag:a-truth": {"description": "d", "codeword": None},
        "flag:b-truth": {"description": "d", "codeword": None},
        "flag:sees-ok": {"description": "d", "codeword": None},
        "flag:custom-one": {"description": "d", "codeword": "CUSTOM"},
    }
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)

    assert book.codewords["flag:a-truth"] == "TRUTH"  # last token, no collision
    assert book.codewords["flag:b-truth"] == "BTRUTH"  # collides with TRUTH, extends leftward
    assert book.codewords["flag:sees-ok"] == "SEESOK"  # "OK" < 3 letters, extends leftward
    assert book.codewords["flag:custom-one"] == "CUSTOM"  # stored codeword wins, untouched
    assert set(book.fallback_flags) == {"flag:a-truth", "flag:b-truth", "flag:sees-ok"}
    assert "flag:custom-one" not in book.fallback_flags


def test_grant_hoisting_common_vs_asymmetric():
    passages = {
        "start": _passage(
            "Start.",
            [
                _choice("Take path A", "hub1", grants=["flag:g1"]),
                _choice("Take path B", "hub1", grants=["flag:g1"]),
            ],
        ),
        "hub1": _passage(
            "Hub one.",
            [
                _choice("Go via mid", "mid", requires=["flag:g1"]),
                _choice("Go via side", "side", requires=["flag:g1"]),
            ],
        ),
        "mid": _passage("Mid.", [_choice("Onward", "hub2", grants=["flag:g2"])]),
        "side": _passage("Side.", [_choice("Onward", "hub2", grants=["flag:g3"])]),
        "hub2": _passage(
            "Hub two.", [_choice("Finish", "end", requires=["flag:g2", "flag:g3"])]
        ),
        "end": _passage("The end.", ending={"id": "e-end", "title": "The End"}),
    }
    flags = {
        "flag:g1": {"description": "d", "codeword": "GONE"},
        "flag:g2": {"description": "d", "codeword": "GTWO"},
        "flag:g3": {"description": "d", "codeword": "GTHREE"},
    }
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    by_passage = {s.passage: s for s in book.sections}

    # both incoming choices to hub1 grant g1 -> hoisted, not inline
    assert any("GONE" in line for line in by_passage["hub1"].hoisted_lines)
    for line in by_passage["start"].choice_lines:
        assert "GONE" not in line

    # hub2's incoming choices grant DIFFERENT flags -> nothing common, no hoist
    assert by_passage["hub2"].hoisted_lines == ()
    mid_line = by_passage["mid"].choice_lines[0]
    side_line = by_passage["side"].choice_lines[0]
    assert "GTWO" in mid_line and "GTHREE" not in mid_line
    assert "GTHREE" in side_line and "GTWO" not in side_line


def test_variant_lowering_gated_pair_and_ungated_otherwise():
    passages = {
        "start": _passage(
            "Junction.",
            [
                _choice("Proceed", "va", requires=["flag:xflag"]),
                _choice("Proceed", "vb", requires=["flag:yflag"]),
                _choice("Proceed", "vc"),
            ],
        ),
        "va": _passage("A.", ending={"id": "e-a", "title": "Ending A"}),
        "vb": _passage("B.", ending={"id": "e-b", "title": "Ending B"}),
        "vc": _passage("C.", ending={"id": "e-c", "title": "Ending C"}),
    }
    flags = {
        "flag:xflag": {"description": "d", "codeword": "XCODE"},
        "flag:yflag": {"description": "d", "codeword": "YCODE"},
    }
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    start = next(s for s in book.sections if s.passage == "start")
    assert len(start.choice_lines) == 1
    line = start.choice_lines[0]
    assert line.startswith("Proceed: ")
    assert "if you have XCODE" in line
    assert "if you have YCODE" in line
    assert "otherwise," in line
    assert line.index("if you have XCODE") < line.index("if you have YCODE") < line.index(
        "otherwise,"
    )


def test_variant_lowering_two_gated_no_ungated_has_no_otherwise():
    passages = {
        "start": _passage(
            "Junction.",
            [
                _choice("Proceed", "va", requires=["flag:xflag"]),
                _choice("Proceed", "vb", requires=["flag:yflag"]),
            ],
        ),
        "va": _passage("A.", ending={"id": "e-a", "title": "Ending A"}),
        "vb": _passage("B.", ending={"id": "e-b", "title": "Ending B"}),
    }
    flags = {
        "flag:xflag": {"description": "d", "codeword": "XCODE"},
        "flag:yflag": {"description": "d", "codeword": "YCODE"},
    }
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    start = next(s for s in book.sections if s.passage == "start")
    line = start.choice_lines[0]
    assert "otherwise" not in line


def test_singleton_no_requires_and_singleton_with_requires_forms():
    # "mid" has exactly one incoming choice, so its grant is trivially
    # common to "every incoming choice" and hoists rather than staying
    # inline — exercise the inline form with a second, non-unanimous
    # incoming choice into "mid" instead.
    passages = {
        "start": _passage(
            "Start.",
            [
                _choice("Walk forward", "mid", grants=["flag:torch"]),
                _choice("Sneak around", "mid"),
            ],
        ),
        "mid": _passage(
            "Mid.",
            [_choice("Ask the guide what she knows", "end", requires=["flag:torch"])],
        ),
        "end": _passage("The end.", ending={"id": "e-end", "title": "The End"}),
    }
    flags = {"flag:torch": {"description": "d", "codeword": "TORCH"}}
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    by_passage = {s.passage: s for s in book.sections}

    assert by_passage["mid"].hoisted_lines == ()  # not unanimous: "Sneak around" grants nothing
    start_lines = by_passage["start"].choice_lines
    walk_line = next(line for line in start_lines if line.startswith("Walk forward"))
    sneak_line = next(line for line in start_lines if line.startswith("Sneak around"))
    assert walk_line == (
        f"Walk forward: write down the codeword TORCH, then turn to {by_passage['mid'].number}."
    )
    assert sneak_line == f"Sneak around: turn to {by_passage['mid'].number}."
    mid_line = by_passage["mid"].choice_lines[0]
    assert mid_line == (
        f"If you have TORCH, you may ask the guide what she knows: "
        f"turn to {by_passage['end'].number}."
    )


def test_unprojected_grants_render_nowhere():
    passages = {
        "start": _passage(
            "Start.",
            [_choice("Go", "end", grants=["flag:never-tested"])],
        ),
        "end": _passage("The end.", ending={"id": "e-end", "title": "The End"}),
    }
    flags = {"flag:never-tested": {"description": "d", "codeword": None}}
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    assert "flag:never-tested" not in book.codewords
    start = next(s for s in book.sections if s.passage == "start")
    assert start.hoisted_lines == ()
    assert "write down" not in start.choice_lines[0].lower()
    assert "Write down" not in book.typst or "never-tested" not in book.typst


def test_lint_reports_test_before_grant():
    passages = {
        "start": _passage("Start.", [_choice("Go", "end", requires=["flag:ungranted"])]),
        "end": _passage("The end.", ending={"id": "e-end", "title": "The End"}),
    }
    flags = {"flag:ungranted": {"description": "d", "codeword": "NEVER"}}
    runtime = _rt(passages, start="start", flags=flags)
    book = build_gamebook(runtime, seed=1)
    errors = lint_gamebook(book)
    assert any("never granted" in e for e in errors)


def test_lint_reports_unresolved_turn_to():
    passages = {
        "start": _passage("Start.", [_choice("Go", "nowhere")]),
    }
    runtime = _rt(passages, start="start")
    book = build_gamebook(runtime, seed=1)
    errors = lint_gamebook(book)
    assert any("does not resolve" in e for e in errors)


def test_codex_appendix_present_when_entries_exist():
    passages = {
        "start": _passage("Start.", ending={"id": "e-end", "title": "The End"}),
    }
    codex = [{"entity": "character:keeper", "title": "The Keeper", "body": "She tends the light."}]
    runtime = _rt(passages, start="start", codex=codex)
    book = build_gamebook(runtime, seed=1)
    assert "= Codex" in book.typst
    assert "The Keeper" in book.typst
    assert "She tends the light." in book.typst


def test_codex_appendix_absent_when_no_entries():
    passages = {
        "start": _passage("Start.", ending={"id": "e-end", "title": "The End"}),
    }
    runtime = _rt(passages, start="start", codex=[])
    book = build_gamebook(runtime, seed=1)
    assert "= Codex" not in book.typst


def test_markdown_bounded_mapping_and_lossy_warning():
    passages = {
        "start": _passage(
            "This is *italic* and **bold** text.\n\n# A header that will not survive.",
            ending={"id": "e-end", "title": "The End"},
        ),
    }
    runtime = _rt(passages, start="start")
    book = build_gamebook(runtime, seed=1)
    start = next(s for s in book.sections if s.passage == "start")
    assert "#emph[italic]" in start.prose_typst
    assert "#strong[bold]" in start.prose_typst
    assert any("markdown construct" in w for w in book.warnings)


# -- CLI --------------------------------------------------------------------


GOLDEN = Path(__file__).parent.parent / "examples" / "keepers-bargain"


@pytest.fixture()
def golden_copy(tmp_path):
    dest = tmp_path / "keepers-bargain"
    shutil.copytree(GOLDEN, dest)
    return dest


def test_cli_export_pdf_writes_files_and_persists_seed(golden_copy):
    runner = CliRunner()
    result = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy)])
    assert result.exit_code == 0, result.output

    typ_path = golden_copy / "exports" / "the-keepers-bargain.typ"
    pdf_path = golden_copy / "exports" / "the-keepers-bargain.pdf"
    assert typ_path.exists()
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")

    project = load_project(golden_copy)
    assert project.print_seed is not None

    first_typ = typ_path.read_text(encoding="utf-8")

    result2 = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy)])
    assert result2.exit_code == 0, result2.output
    second_typ = typ_path.read_text(encoding="utf-8")
    assert first_typ == second_typ

    reloaded = load_project(golden_copy)
    assert reloaded.print_seed == project.print_seed


def test_cli_export_pdf_explicit_seed_overrides_and_persists_once(golden_copy):
    runner = CliRunner()
    result = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy), "--seed", "42"])
    assert result.exit_code == 0, result.output
    project = load_project(golden_copy)
    assert project.print_seed == 42

    # a later call without --seed reuses the persisted seed, not the default 1
    result2 = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy)])
    assert result2.exit_code == 0, result2.output
    reloaded = load_project(golden_copy)
    assert reloaded.print_seed == 42
