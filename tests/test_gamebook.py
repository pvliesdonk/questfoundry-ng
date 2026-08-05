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
from questfoundry.export.style import FULL_BLEED_MIN_PIXELS
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
    # the document title comes first: PDF/UA-1 refuses a build without one
    assert book.typst.startswith("#set document(title:")


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
        assert "GONE" not in line.sentence

    # hub2's incoming choices grant DIFFERENT flags -> nothing common, no hoist
    assert by_passage["hub2"].hoisted_lines == ()
    mid_line = by_passage["mid"].choice_lines[0].sentence
    side_line = by_passage["side"].choice_lines[0].sentence
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
    line = start.choice_lines[0].sentence
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
    line = start.choice_lines[0].sentence
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
    start_lines = [line.sentence for line in by_passage["start"].choice_lines]
    walk_line = next(line for line in start_lines if line.startswith("Walk forward"))
    sneak_line = next(line for line in start_lines if line.startswith("Sneak around"))
    assert walk_line == (
        f"Walk forward: write down the codeword TORCH, then turn to {by_passage['mid'].number}."
    )
    assert sneak_line == f"Sneak around: turn to {by_passage['mid'].number}."
    mid_line = by_passage["mid"].choice_lines[0].sentence
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
    assert "write down" not in start.choice_lines[0].sentence.lower()
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


def _write_cover_png(root: Path, size: tuple[int, int] = FULL_BLEED_MIN_PIXELS) -> None:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, (30, 40, 50)).save(buf, format="PNG")
    (root / "art" / "images").mkdir(parents=True, exist_ok=True)
    (root / "art" / "images" / "cover.png").write_bytes(buf.getvalue())


def test_print_cover_page_when_image_exists(golden_copy):
    _write_cover_png(golden_copy)
    project = load_project(golden_copy)
    runtime = build_runtime(project)  # the golden has a cover brief
    assert runtime.get("cover")  # cover ships now that the image exists
    book = build_gamebook(
        runtime, seed=1, images_dir=golden_copy / "art" / "images", root=golden_copy
    )
    # a full-page cover image renders ahead of the title page; the image itself
    # carries the title (drawn/composited at illustrate time), so the layout
    # places it full-bleed with no title text overlaid
    assert "art/images/cover.png" in book.typst
    assert 'fit: "cover"' in book.typst
    assert "rgb(0, 0, 0, 160)" not in book.typst  # the old title-overlay band is gone
    # the title is set once as document metadata (PDF/UA-1 requires it) and
    # typeset once, on the interior title page — never over the cover art
    body = book.typst.split("\n", 1)[1]
    assert book.typst.startswith("#set document(title:")
    assert body.count(_escape_title(runtime["meta"]["title"])) == 1
    # it compiles
    assert compile_pdf(book.typst, root=golden_copy).startswith(b"%PDF")


def test_cover_below_the_dpi_floor_falls_back_to_inset(golden_copy):
    """Full-bleed at 300dpi is a supported target, not an assumption: a
    render that cannot fill an A5 page at that density is placed inset
    rather than upscaled into softness (design plan, ratified decision 1)."""
    _write_cover_png(golden_copy, size=(600, 900))
    project = load_project(golden_copy)
    book = build_gamebook(
        build_runtime(project),
        seed=1,
        images_dir=golden_copy / "art" / "images",
        root=golden_copy,
    )
    assert 'fit: "cover"' not in book.typst  # not full-bleed
    assert "art/images/cover.png" in book.typst  # still placed
    assert any("600×900px" in w and "inset" in w for w in book.warnings)
    assert compile_pdf(book.typst, root=golden_copy).startswith(b"%PDF")


def _escape_title(title: str) -> str:
    from questfoundry.export.gamebook import _escape_typst

    return _escape_typst(title)


def test_no_cover_page_without_image(golden_copy):
    # the golden has a cover brief but no rendered cover.png -> no cover page
    project = load_project(golden_copy)
    runtime = build_runtime(project)
    assert "cover" not in runtime
    book = build_gamebook(
        runtime, seed=1, images_dir=golden_copy / "art" / "images", root=golden_copy
    )
    assert "art/images/cover.png" not in book.typst


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


# -- 1a Paperback furniture (design doc 04 §7) --------------------------------


def test_paperback_flows_continuously_and_is_set_at_a5(golden):
    """1a's defining difference from the layout it replaces: sections flow
    into one another instead of taking a page each, at A5 rather than the
    old 130x200 trim."""
    book = build_gamebook(build_runtime(golden), seed=1)
    assert "width: 148.0mm" in book.typst and "height: 210.0mm" in book.typst
    # exactly the deliberate breaks — front matter and the two appendices —
    # never one per section
    assert book.typst.count("#pagebreak()") < len(book.sections)


def test_running_head_reads_the_sections_on_the_spread(golden):
    book = build_gamebook(build_runtime(golden), seed=1)
    # the head is computed from the marks laid down by the sections
    # themselves, not from a counter that guesses
    assert "<qf-section>" in book.typst
    assert "qf-spread-range" in book.typst
    assert "query(<qf-section>)" in book.typst


def test_single_target_instruction_puts_its_number_at_the_margin():
    passages = {
        "start": _passage("Start.", [_choice("Walk on", "end")]),
        "end": _passage("Done.", ending={"id": "e-end", "title": "The End"}),
    }
    book = build_gamebook(_rt(passages, start="start"), seed=1)
    start = next(s for s in book.sections if s.passage == "start")
    (line,) = start.choice_lines
    assert line.text == "Walk on: turn to"
    assert line.number == 2
    assert line.sentence == "Walk on: turn to 2."
    # the number reaches the template as a value, not as literal brackets
    assert "#qf-instruction([Walk on: turn to], [2])" in book.typst


def test_multi_clause_instruction_keeps_every_number_inline():
    """A group lowered to several codeword clauses names several sections,
    so none of them can go to the margin."""
    passages = {
        "start": _passage(
            "Junction.",
            [
                _choice("Proceed", "va", requires=["flag:xflag"]),
                _choice("Proceed", "vb"),
            ],
        ),
        "va": _passage("A.", ending={"id": "e-a", "title": "Ending A"}),
        "vb": _passage("B.", ending={"id": "e-b", "title": "Ending B"}),
    }
    flags = {"flag:xflag": {"description": "d", "codeword": "XCODE"}}
    book = build_gamebook(_rt(passages, start="start", flags=flags), seed=1)
    start = next(s for s in book.sections if s.passage == "start")
    (line,) = start.choice_lines
    assert line.number is None
    assert line.sentence.endswith(".")
    assert "], none)" in book.typst


def test_large_print_scales_the_type_but_keeps_the_page(golden):
    from questfoundry.export.style import print_style

    runtime = build_runtime(golden)
    plain = build_gamebook(runtime, seed=1)
    large = build_gamebook(runtime, seed=1, style=print_style("paperback", large_print=True))
    assert f"size: {plain.style.body_size}pt" in plain.typst
    assert f"size: {large.style.body_size}pt" in large.typst
    assert large.style.body_size > plain.style.body_size
    assert "width: 148.0mm" in large.typst  # same trim, same furniture
    assert compile_pdf(large.typst).startswith(b"%PDF")


# -- alt text and PDF/UA-1 -----------------------------------------------------


def test_plate_carries_alt_and_its_ratio_decides_the_width(golden_copy):
    from questfoundry.export.style import PRINT_PLACEMENT

    _write_plate_pngs(golden_copy)
    project = load_project(golden_copy)
    book = build_gamebook(
        build_runtime(project),
        seed=1,
        images_dir=golden_copy / "art" / "images",
        root=golden_copy,
    )
    plates = {s.passage: s.illustration for s in book.sections if s.illustration}
    # the golden's lamp-room brief is a square study, the others landscape
    assert plates["p-lamp-room"].ratio == "1:1"
    assert plates["p-arrival"].ratio == "3:2"
    for plate in plates.values():
        assert plate.alt.strip()
        assert f'"{plate.alt}"' in book.typst  # reaches the template verbatim
        assert f", {PRINT_PLACEMENT[plate.ratio].width})" in book.typst


def test_lint_names_the_section_whose_illustration_has_no_alt(golden_copy):
    _write_plate_pngs(golden_copy)
    project = load_project(golden_copy)
    runtime = build_runtime(project)
    for entry in runtime["art"]:
        entry["alt"] = ""
    book = build_gamebook(
        runtime, seed=1, images_dir=golden_copy / "art" / "images", root=golden_copy
    )
    errors = lint_gamebook(book)
    assert errors, "a plate with no alt text must block the export"
    assert all("no alt text" in e and "PDF/UA-1" in e for e in errors)
    # the message names a section and a passage, so the brief is findable
    assert any("p-arrival" in e for e in errors)


def test_the_compiler_itself_refuses_a_build_with_no_alt_text(golden_copy):
    """The contract is mechanical, not merely checked by us: `compile_pdf`
    passes pdf_standards=ua-1, so Typst rejects an image with no alt — the
    backstop behind the lint above, and the reason alt is not optional."""
    _write_plate_pngs(golden_copy)
    source = (
        '#set document(title: "Probe")\n'
        "= A section\n"
        '#image("/art/images/p-arrival.png", width: 40%)\n'
    )
    with pytest.raises(Exception, match="alt text"):
        compile_pdf(source, root=golden_copy)
    # the same document with alt compiles
    with_alt = source.replace('width: 40%', 'width: 40%, alt: "a grey plate"')
    assert compile_pdf(with_alt, root=golden_copy).startswith(b"%PDF")


def test_the_compiler_itself_refuses_a_build_with_no_document_title(golden):
    book = build_gamebook(build_runtime(golden), seed=1)
    titleless = book.typst.split("\n", 1)[1]
    with pytest.raises(Exception, match="document title"):
        compile_pdf(titleless)


def _write_plate_pngs(root: Path) -> None:
    import io

    from PIL import Image

    (root / "art" / "images").mkdir(parents=True, exist_ok=True)
    for slug in ("p-arrival", "p-lamp-room", "p-tremor"):
        buf = io.BytesIO()
        Image.new("RGB", (60, 40), (90, 90, 80)).save(buf, format="PNG")
        (root / "art" / "images" / f"{slug}.png").write_bytes(buf.getvalue())


# -- style selection through the CLI -------------------------------------------


def test_cli_rejects_an_unknown_style_and_lists_the_built_ones(golden_copy):
    runner = CliRunner()
    result = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy), "--style", "bound"])
    assert result.exit_code == 2
    assert "unknown print style" in result.output and "paperback" in result.output


def test_cli_style_only_applies_to_the_styled_formats(golden_copy):
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", "json", "--dir", str(golden_copy), "--style", "paperback"]
    )
    assert result.exit_code == 2
    assert "--style applies to" in result.output


def test_cli_large_print_writes_its_own_edition(golden_copy):
    """A modifier produces a second edition of the same book, so it gets its
    own filename instead of overwriting the plain one."""
    runner = CliRunner()
    assert runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy)]).exit_code == 0
    result = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy), "--large-print"])
    assert result.exit_code == 0, result.output

    exports = golden_copy / "exports"
    assert (exports / "the-keepers-bargain.pdf").exists()
    large = exports / "the-keepers-bargain-paperback-large-print.typ"
    assert large.exists()
    assert large.with_suffix(".pdf").read_bytes().startswith(b"%PDF")
    assert "size: 14.2pt" in large.read_text(encoding="utf-8")


def test_cli_html_large_print_writes_its_own_edition(golden_copy):
    runner = CliRunner()
    result = runner.invoke(app, ["export", "html", "--dir", str(golden_copy), "--large-print"])
    assert result.exit_code == 0, result.output
    page = golden_copy / "exports" / "the-keepers-bargain-screen-large-print.html"
    assert "--measure: 54ch;" in page.read_text(encoding="utf-8")
