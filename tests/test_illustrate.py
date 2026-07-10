"""`qf illustrate` (mini-ADR A18): prompt assembly from art direction +
entity visual fragments, deterministic render planning (skip-if-exists,
priority floor, budget), the sample-first gate, content-policy
reformulation, and the hermetic placeholder path CI exercises end-to-end.
"""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from questfoundry.cli import app
from questfoundry.illustrate import (
    IllustrateError,
    assemble_prompt,
    build_service,
    image_path,
    plan_renders,
    render_briefs,
)
from questfoundry.models.enrichment import (
    ArtDirection,
    Enrichment,
    IllustrationBrief,
    VisualProfile,
)
from questfoundry.project import load_project

GOLDEN = Path(__file__).parent.parent / "examples" / "keepers-bargain"


@pytest.fixture()
def golden_copy(tmp_path):
    dest = tmp_path / "keepers-bargain"
    shutil.copytree(GOLDEN, dest)
    return dest


def _enrichment(**overrides) -> Enrichment:
    base = dict(
        direction=ArtDirection(style="scratchboard", palette="grey and gold"),
        profiles=[
            VisualProfile(
                entity="character:keeper",
                appearance="a weathered woman in an oilskin coat",
                iconography=["brass trimming-knife"],
            )
        ],
        briefs=[
            IllustrationBrief(
                passage="passage:p-arrival",
                priority=1,
                caption="Arrival.",
                prompt="a lighthouse on iron stilts",
                entities=["character:keeper"],
            )
        ],
    )
    base.update(overrides)
    return Enrichment(**base)


# -- prompt assembly ---------------------------------------------------------


def test_assemble_prompt_carries_direction_fragments_and_scene():
    enrichment = _enrichment(
        direction=ArtDirection(
            style="scratchboard",
            palette="grey and gold",
            influences=["scrimshaw"],
            notes="the lamp is the only light",
        )
    )
    prompt = assemble_prompt(enrichment.briefs[0], enrichment)
    assert "Style: scratchboard." in prompt
    assert "Palette: grey and gold." in prompt
    assert "Influences: scrimshaw." in prompt
    assert "the lamp is the only light" in prompt
    assert "keeper: a weathered woman in an oilskin coat (brass trimming-knife)." in prompt
    assert prompt.endswith("Scene: a lighthouse on iron stilts")


def test_assemble_prompt_requires_direction():
    enrichment = _enrichment(direction=None)
    with pytest.raises(IllustrateError, match="no art direction"):
        assemble_prompt(enrichment.briefs[0], enrichment)


def test_assemble_prompt_rejects_unprofiled_entity():
    enrichment = _enrichment(profiles=[])
    with pytest.raises(IllustrateError, match="no visual profile"):
        assemble_prompt(enrichment.briefs[0], enrichment)


# -- render planning ---------------------------------------------------------


def test_plan_orders_by_priority_then_slug(golden_copy):
    project = load_project(golden_copy)
    plan = plan_renders(project)
    slugs = [b.passage for b in plan.to_render]
    assert slugs == ["passage:p-arrival", "passage:p-lamp-room", "passage:p-tremor"]


def test_plan_skips_existing_unless_forced(golden_copy):
    project = load_project(golden_copy)
    existing = image_path(golden_copy, project.enrichment.briefs[0])
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"png")
    plan = plan_renders(project)
    assert len(plan.to_render) == 2
    assert [b.passage for b in plan.skipped_existing] == ["passage:p-arrival"]
    forced = plan_renders(project, force=True)
    assert len(forced.to_render) == 3


def test_plan_priority_floor_and_budget(golden_copy):
    project = load_project(golden_copy)
    plan = plan_renders(project, priority_floor=2)
    assert [b.priority for b in plan.to_render] == [1, 2]
    assert [b.priority for b in plan.skipped_priority] == [3]
    capped = plan_renders(project, budget=1)
    assert len(capped.to_render) == 1
    assert len(capped.skipped_budget) == 2


# -- provider construction ---------------------------------------------------


def test_build_service_requires_configuration(golden_copy):
    project = load_project(golden_copy)
    with pytest.raises(IllustrateError, match="no image provider configured"):
        build_service(project)
    with pytest.raises(IllustrateError, match="unknown provider"):
        build_service(project, "dall-e")


def test_build_service_cloud_providers_need_keys(golden_copy, monkeypatch):
    project = load_project(golden_copy)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(IllustrateError, match="OPENAI_API_KEY"):
        build_service(project, "openai")
    with pytest.raises(IllustrateError, match="GEMINI_API_KEY"):
        build_service(project, "gemini")


# -- content-policy reformulation --------------------------------------------


def _tiny_png() -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (88, 101, 130)).save(buffer, format="PNG")
    return buffer.getvalue()


class _RefusingProvider:
    """Refuses any prompt containing 'forbidden'; renders otherwise."""

    def __init__(self):
        self.calls: list[str] = []

    async def generate(self, prompt, **kwargs):
        from image_generation_mcp.providers.types import (
            ImageContentPolicyError,
            ImageResult,
        )

        self.calls.append(prompt)
        if "forbidden" in prompt:
            raise ImageContentPolicyError("stub", "policy says no")
        return ImageResult(image_data=_tiny_png())

    async def discover_capabilities(self):  # pragma: no cover - unused
        raise NotImplementedError


def _stub_service(project, provider):
    from image_generation_mcp.domain import ImageService

    service = ImageService(scratch_dir=project.root / "cache" / "images")
    service.register_provider("stub", provider)
    return service


def _forbidden_project(golden_copy):
    project = load_project(golden_copy)
    project.enrichment.briefs[0].prompt = "a forbidden lighthouse"
    return project


def test_refusal_without_reformulator_records_and_continues(golden_copy):
    project = _forbidden_project(golden_copy)
    provider = _RefusingProvider()
    outcomes = render_briefs(project, _stub_service(project, provider), "stub",
                             project.enrichment.briefs)
    assert outcomes[0].path is None
    assert "policy says no" in outcomes[0].refusal
    # the batch continued: the other two briefs rendered
    assert [o.path is not None for o in outcomes[1:]] == [True, True]


def test_refusal_gets_exactly_one_reformulation(golden_copy):
    project = _forbidden_project(golden_copy)
    provider = _RefusingProvider()
    rewrites = []

    def reformulate(prompt, refusal):
        rewrites.append((prompt, refusal))
        return prompt.replace("forbidden", "weathered")

    outcomes = render_briefs(
        project,
        _stub_service(project, provider),
        "stub",
        project.enrichment.briefs[:1],
        reformulate=reformulate,
    )
    assert len(rewrites) == 1
    assert outcomes[0].path is not None
    assert outcomes[0].reformulated
    assert image_path(golden_copy, project.enrichment.briefs[0]).exists()


def test_non_png_provider_bytes_are_normalized(golden_copy):
    """Gemini returns JPEG bytes no matter the .png contract (found live,
    M7 exit run) — the write site must normalize."""
    import io

    from PIL import Image

    jpeg = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(jpeg, format="JPEG")

    class _JpegProvider:
        async def generate(self, prompt, **kwargs):
            from image_generation_mcp.providers.types import ImageResult

            return ImageResult(image_data=jpeg.getvalue(), content_type="image/jpeg")

        async def discover_capabilities(self):  # pragma: no cover - unused
            raise NotImplementedError

    project = load_project(golden_copy)
    outcomes = render_briefs(
        project, _stub_service(project, _JpegProvider()), "stub", project.enrichment.briefs[:1]
    )
    assert outcomes[0].path.read_bytes().startswith(b"\x89PNG")


def test_second_refusal_is_final(golden_copy):
    project = _forbidden_project(golden_copy)
    provider = _RefusingProvider()
    outcomes = render_briefs(
        project,
        _stub_service(project, provider),
        "stub",
        project.enrichment.briefs[:1],
        reformulate=lambda prompt, refusal: prompt,  # unhelpful rewrite
    )
    assert len(provider.calls) == 2  # one attempt + one reformulated attempt, never more
    assert outcomes[0].path is None


# -- the hermetic CLI path (what CI exercises) --------------------------------


def test_cli_illustrate_placeholder_end_to_end(golden_copy):
    runner = CliRunner()
    result = runner.invoke(
        app, ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "3 image(s) rendered" in result.output

    for slug in ("p-arrival", "p-lamp-room", "p-tremor"):
        png = golden_copy / "art" / "images" / f"{slug}.png"
        assert png.exists()
        assert png.read_bytes().startswith(b"\x89PNG")

    entries = [
        json.loads(line)
        for line in (golden_copy / "reports" / "ledger.jsonl").read_text().splitlines()
    ]
    image_entries = [e for e in entries if e.get("kind") == "image"]
    assert len(image_entries) == 3
    assert all(e["provider"] == "placeholder" and not e["refused"] for e in image_entries)


def test_cli_illustrate_rerun_is_free(golden_copy):
    runner = CliRunner()
    args = ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder", "--yes"]
    assert runner.invoke(app, args).exit_code == 0
    ledger_path = golden_copy / "reports" / "ledger.jsonl"
    before = ledger_path.read_text()

    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "nothing to render" in result.output
    assert ledger_path.read_text() == before  # zero API calls, zero ledger growth

    forced = runner.invoke(app, args + ["--force"])
    assert forced.exit_code == 0, forced.output
    assert "3 image(s) rendered" in forced.output


def test_cli_sample_first_gate_stops_on_decline(golden_copy):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder"],
        input="n\n",
    )
    assert result.exit_code == 0, result.output
    assert "sample rendered" in result.output
    images = list((golden_copy / "art" / "images").glob("*.png"))
    assert len(images) == 1  # the sample stays on disk; nothing else rendered
    assert "not rendered" in result.output


def test_cli_illustrate_needs_briefs(tmp_path):
    from questfoundry.project import scaffold_project

    scaffold_project(tmp_path / "empty", name="Empty", scope="micro")
    runner = CliRunner()
    result = runner.invoke(app, ["illustrate", "--dir", str(tmp_path / "empty")])
    assert result.exit_code == 1
    assert "no illustration briefs" in result.output


def test_cli_illustrate_unconfigured_provider_exits(golden_copy):
    runner = CliRunner()
    result = runner.invoke(app, ["illustrate", "--dir", str(golden_copy), "--yes"])
    assert result.exit_code == 2
    assert "no image provider configured" in result.output


# -- exports pick the images up ----------------------------------------------


def test_html_player_embeds_rendered_art(golden_copy):
    from questfoundry.export.html import build_html
    from questfoundry.export.runtime_json import build_runtime

    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder", "--yes"],
        ).exit_code
        == 0
    )
    project = load_project(golden_copy)
    runtime = build_runtime(project)
    assert [a["passage"] for a in runtime["art"]] == ["p-arrival", "p-lamp-room", "p-tremor"]
    assert all(a["image"].startswith("art/images/") for a in runtime["art"])

    html = build_html(project)
    assert html.count("data:image/png;base64,") == 3
    assert '<figure id="art"' in html


def test_pdf_export_compiles_with_rendered_art(golden_copy):
    """The M5 illustration slot met real image files for the first time in
    M7's live run and failed: typst resolves #image paths from its
    compilation root, so the absolute OS paths gamebook emitted never
    compiled. The whole chain must work through the CLI."""
    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder", "--yes"],
        ).exit_code
        == 0
    )
    result = runner.invoke(app, ["export", "pdf", "--dir", str(golden_copy)])
    assert result.exit_code == 0, result.output

    typ = (golden_copy / "exports" / "the-keepers-bargain.typ").read_text(encoding="utf-8")
    assert '#image("/art/images/p-arrival.png"' in typ
    pdf = golden_copy / "exports" / "the-keepers-bargain.pdf"
    assert pdf.read_bytes().startswith(b"%PDF")


def test_build_gamebook_rejects_images_without_root(golden_copy):
    from questfoundry.export.gamebook import build_gamebook
    from questfoundry.export.runtime_json import build_runtime

    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            ["illustrate", "--dir", str(golden_copy), "--provider", "placeholder", "--yes"],
        ).exit_code
        == 0
    )
    project = load_project(golden_copy)
    with pytest.raises(ValueError, match="requires root"):
        build_gamebook(
            build_runtime(project), seed=1, images_dir=golden_copy / "art" / "images"
        )
