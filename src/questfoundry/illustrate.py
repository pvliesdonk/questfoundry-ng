"""Illustration rendering for DRESS briefs (`qf illustrate`, mini-ADR A18).

Deliberately a command, not a pipeline stage: cloud image generation
exposes no seeds, so rendered bytes can never join checkpoint
byte-stability or A16 fingerprint replay. Idempotence is by file
presence instead — a brief whose `art/images/<slug>.png` exists is
skipped, and re-running the command costs zero API calls.

The provider seam is `image-generation-mcp` consumed as a library
(`ImageService` + `register_provider`, no fastmcp code — design doc 03
§9). Everything the library deliberately lacks is owned here: prompt
assembly from art direction + entity visual fragments, priority/budget
filtering, ledger entries, and one reformulation attempt on a typed
content-policy refusal. Generation errors are never retried
automatically (renders are paid); already-rendered files survive a
mid-batch failure, so a rerun resumes where the batch stopped.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from questfoundry.llm import ledger
from questfoundry.models.enrichment import Enrichment, IllustrationBrief
from questfoundry.project.io import Project

PROVIDERS = ("placeholder", "openai", "gemini")

# Landscape suits an illustration sitting above prose in both the HTML
# player and the print page; overridable via the `images:` block.
DEFAULT_ASPECT_RATIO = "3:2"

REFORMULATE_SYSTEM = (
    "You rewrite image-generation prompts that a provider's content policy"
    " refused. Preserve the scene, subjects, and art direction; remove or"
    " soften only what plausibly triggered the refusal (violence, gore,"
    " likeness, unsafe content). Return JSON only."
)


class IllustrateError(Exception):
    pass


def passage_slug(brief: IllustrationBrief) -> str:
    return brief.passage.split(":", 1)[1]


def image_path(root: Path, brief: IllustrationBrief) -> Path:
    return root / "art" / "images" / f"{passage_slug(brief)}.png"


def assemble_prompt(brief: IllustrationBrief, enrichment: Enrichment) -> str:
    """One prompt per brief: art direction first (the global contract),
    then the visual profile fragment of every depicted entity (the
    heritage consistency device — canonical appearance in every prompt
    that names the entity), then the brief's own scene."""
    direction = enrichment.direction
    if direction is None:
        raise IllustrateError("no art direction — run DRESS before qf illustrate")
    parts = [f"Style: {direction.style}.", f"Palette: {direction.palette}."]
    if direction.influences:
        parts.append(f"Influences: {', '.join(direction.influences)}.")
    if direction.notes:
        parts.append(direction.notes)
    profiles = {p.entity: p for p in enrichment.profiles}
    for entity_id in brief.entities:
        profile = profiles.get(entity_id)
        if profile is None:
            # G6 checks cited entities are profiled; a hand-edited brief
            # can still drift, and a missing fragment silently breaks
            # the consistency device — fail loud instead
            raise IllustrateError(
                f"brief for {brief.passage} depicts {entity_id} which has no visual profile"
            )
        name = entity_id.split(":", 1)[1].replace("-", " ")
        fragment = f"{name}: {profile.appearance}"
        if profile.iconography:
            fragment += f" ({', '.join(profile.iconography)})"
        parts.append(fragment + ".")
    parts.append(f"Scene: {brief.prompt}")
    return "\n".join(parts)


@dataclass
class RenderPlan:
    to_render: list[IllustrationBrief]
    skipped_existing: list[IllustrationBrief] = field(default_factory=list)
    skipped_priority: list[IllustrationBrief] = field(default_factory=list)
    skipped_budget: list[IllustrationBrief] = field(default_factory=list)


def plan_renders(
    project: Project,
    *,
    force: bool = False,
    priority_floor: int | None = None,
    budget: int | None = None,
) -> RenderPlan:
    """Deterministic selection: briefs ordered by (priority, slug);
    existing files skip unless --force; the priority floor drops briefs
    below it (priority > floor); the budget caps renders per invocation."""
    plan = RenderPlan(to_render=[])
    ordered = sorted(project.enrichment.briefs, key=lambda b: (b.priority, passage_slug(b)))
    for brief in ordered:
        if priority_floor is not None and brief.priority > priority_floor:
            plan.skipped_priority.append(brief)
        elif not force and image_path(project.root, brief).exists():
            plan.skipped_existing.append(brief)
        elif budget is not None and len(plan.to_render) >= budget:
            plan.skipped_budget.append(brief)
        else:
            plan.to_render.append(brief)
    return plan


def build_service(project: Project, provider_override: str | None = None):
    """Construct the library's ImageService with exactly one registered
    provider, resolved from --provider or the project's `images:` block.
    Returns (service, provider_name, generate_kwargs)."""
    from image_generation_mcp.domain import ImageService

    config = project.images
    name = provider_override or config.get("provider", "")
    if name not in PROVIDERS:
        hint = f"unknown provider {name!r}" if name else "no image provider configured"
        raise IllustrateError(
            f"{hint} — set images.provider in project.yaml or pass --provider; "
            f"one of {', '.join(PROVIDERS)}"
        )

    if name == "placeholder":
        from image_generation_mcp.providers.placeholder import PlaceholderImageProvider

        provider = PlaceholderImageProvider()
    elif name == "openai":
        from image_generation_mcp.providers.openai import OpenAIImageProvider

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise IllustrateError("images.provider is 'openai' but OPENAI_API_KEY is not set")
        provider = OpenAIImageProvider(api_key=api_key)
    else:
        from image_generation_mcp.providers.gemini import GeminiImageProvider

        api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise IllustrateError(
                "images.provider is 'gemini' but neither GEMINI_API_KEY nor "
                "GOOGLE_API_KEY is set"
            )
        provider = GeminiImageProvider(api_key=api_key)

    scratch = project.root / "cache" / "images"
    scratch.mkdir(parents=True, exist_ok=True)
    service = ImageService(scratch_dir=scratch, default_provider=name)
    service.register_provider(name, provider)

    kwargs: dict = {"aspect_ratio": config.get("aspect_ratio", DEFAULT_ASPECT_RATIO)}
    if config.get("quality"):
        kwargs["quality"] = config["quality"]
    if config.get("model"):
        kwargs["model"] = config["model"]
    return service, name, kwargs


@dataclass
class RenderOutcome:
    brief: IllustrationBrief
    path: Path | None  # None = refused by content policy
    reformulated: bool = False
    refusal: str = ""


def render_briefs(
    project: Project,
    service,
    provider_name: str,
    briefs: list[IllustrationBrief],
    *,
    generate_kwargs: dict | None = None,
    reformulate: Callable[[str, str], str] | None = None,
    on_rendered: Callable[[RenderOutcome], None] | None = None,
    confirm_batch: Callable[[RenderOutcome], bool] | None = None,
) -> list[RenderOutcome]:
    """Render each brief to art/images/<slug>.png, ledger every paid
    call. `confirm_batch` is the sample-first gate: called once after the
    first render lands; returning False stops the batch (the sample stays
    on disk). A content-policy refusal gets one reformulation attempt
    (when a reformulator is wired) and otherwise records the refusal and
    moves on — refusals are content-specific, not systemic. Any other
    provider error propagates: no automatic retry on paid generation, and
    the files already written make the rerun free."""
    from image_generation_mcp.providers.types import ImageContentPolicyError

    kwargs = generate_kwargs or {}

    async def _run() -> list[RenderOutcome]:
        # one event loop for the whole batch: async provider clients are
        # loop-bound, so per-brief asyncio.run would break the second call
        outcomes: list[RenderOutcome] = []
        confirmed = confirm_batch is None
        for brief in briefs:
            prompt = assemble_prompt(brief, project.enrichment)
            outcome = RenderOutcome(brief=brief, path=None)
            try:
                _, result = await service.generate(prompt, provider=provider_name, **kwargs)
            except ImageContentPolicyError as refusal:
                _log_image(project, provider_name, brief, kwargs, refused=True)
                if reformulate is None:
                    outcome.refusal = str(refusal)
                    outcomes.append(outcome)
                    continue
                outcome.reformulated = True
                prompt = reformulate(prompt, str(refusal))
                try:
                    _, result = await service.generate(prompt, provider=provider_name, **kwargs)
                except ImageContentPolicyError as second:
                    _log_image(project, provider_name, brief, kwargs, refused=True)
                    outcome.refusal = str(second)
                    outcomes.append(outcome)
                    continue
            target = image_path(project.root, brief)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_as_png(result.image_data))
            _log_image(project, provider_name, brief, kwargs, refused=False)
            outcome.path = target
            outcomes.append(outcome)
            if on_rendered is not None:
                on_rendered(outcome)
            if not confirmed:
                if not confirm_batch(outcome):
                    break
                confirmed = True
        return outcomes

    return asyncio.run(_run())


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _as_png(data: bytes) -> bytes:
    """Everything downstream keys on `art/images/<slug>.png` — presence
    skip, runtime JSON, data-URI mime, typst decode — but providers
    return what they like (Gemini hands back JPEG; found live, M7 exit
    run). Normalize at the only write site. PIL ships with the image
    library's core."""
    if data.startswith(_PNG_MAGIC):
        return data
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buffer, format="PNG")
    return buffer.getvalue()


def _log_image(
    project: Project, provider: str, brief: IllustrationBrief, kwargs: dict, *, refused: bool
) -> None:
    ledger.append(
        project.root / "reports" / "ledger.jsonl",
        {
            "ts": datetime.now(UTC).isoformat(),
            "kind": "image",
            "provider": provider,
            "model": kwargs.get("model", ""),
            "passage": passage_slug(brief),
            "priority": brief.priority,
            "refused": refused,
        },
    )


def reformulate_prompt_text(prompt: str, refusal: str) -> str:
    """The user prompt for the one LLM reformulation attempt."""
    return (
        "This image prompt was refused by the image provider's content"
        f" policy:\n\n{prompt}\n\nRefusal: {refusal}\n\n"
        "Rewrite the prompt so it will pass, changing as little as possible."
    )
