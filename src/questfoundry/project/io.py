"""Project-on-disk: load and save the story project directory.

Everything is a file (design principle 5): YAML for structure, one file
per entity/dilemma/path/beat/passage so diffs stay readable. The loader
builds the graph exclusively through the mutation layer, so a
hand-edited project passes exactly the same wall as pipeline output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path as FSPath

import yaml

from questfoundry.graph import mutations
from questfoundry.graph.store import FreezeRecord, StoryGraph
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import Vision, Voice
from questfoundry.models.drama import Answer, Consequence, Dilemma, Path
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import Beat, IntersectionGroup, StateFlag
from questfoundry.models.world import Entity

# Default provenance per node kind, so hand-authored files stay terse.
DEFAULT_STAGE = {
    "entity": Stage.BRAINSTORM,
    "dilemma": Stage.BRAINSTORM,
    "answer": Stage.BRAINSTORM,
    "path": Stage.SEED,
    "consequence": Stage.SEED,
    "beat": Stage.SEED,
    "flag": Stage.GROW,
    "intersection": Stage.GROW,
    "passage": Stage.POLISH,
}

RELATION_KEYS = {
    "wraps": EdgeKind.WRAPS,
    "serial": EdgeKind.SERIAL,
    "concurrent": EdgeKind.CONCURRENT,
}


DEFAULT_LLM_CONFIG = {
    "provider": "anthropic",
    "models": {
        "architect": "claude-opus-4-8",
        "writer": "claude-opus-4-8",
        "utility": "claude-haiku-4-5-20251001",
    },
}


@dataclass
class Project:
    root: FSPath
    name: str
    stage: Stage
    vision: Vision
    graph: StoryGraph
    # FILL's prose contract; None until FILL locks it
    voice: Voice | None = None
    # Seed for FILL's reference-arc selection (author-overridable)
    fill_seed: int = 0
    # Twine IFID, generated on first Twee export and stable thereafter
    ifid: str = ""
    # LLM configuration: provider name, role -> model map, mock fixture dir
    llm: dict = field(default_factory=lambda: dict(DEFAULT_LLM_CONFIG))
    # Author steering notes per stage, injected into that stage's prompts
    steering: dict[str, str] = field(default_factory=dict)


class ProjectError(Exception):
    pass


def _read(path: FSPath) -> dict:
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ProjectError(f"{path}: expected a YAML mapping")
    return data


def _write(path: FSPath, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=88)


def _files(directory: FSPath) -> list[FSPath]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.yaml"))


def _created_by(raw: dict, kind: str) -> Stage:
    return Stage(raw.pop("created_by", DEFAULT_STAGE[kind]))


def load_project(root: FSPath | str) -> Project:
    root = FSPath(root)
    meta = _read(root / "project.yaml")
    vision = Vision.model_validate(_read(root / "vision.yaml"))
    stage = Stage(meta["stage"])
    g = StoryGraph()

    for f in _files(root / "graph" / "entities"):
        raw = _read(f)
        mutations.add_entity(g, Entity(created_by=_created_by(raw, "entity"), **raw))

    relations: list[tuple[EdgeKind, str, str]] = []
    for f in _files(root / "graph" / "dilemmas"):
        raw = _read(f)
        created = _created_by(raw, "dilemma")
        answers = tuple(
            Answer(created_by=Stage(a.pop("created_by", created)), **a)
            for a in raw.pop("answers")
        )
        anchored = raw.pop("anchored_to")
        for key, kind in RELATION_KEYS.items():
            for other in raw.pop(key, []):
                relations.append((kind, raw["id"], other))
        dilemma = Dilemma(created_by=created, **raw)
        mutations.add_dilemma(g, dilemma, answers, anchored)  # type: ignore[arg-type]
    for kind, a, b in relations:
        mutations.add_dilemma_relation(g, kind, a, b)

    for f in _files(root / "graph" / "paths"):
        raw = _read(f)
        created = _created_by(raw, "path")
        explores = raw.pop("explores")
        consequences = [
            Consequence(created_by=Stage(c.pop("created_by", created)), **c)
            for c in raw.pop("consequences", [])
        ]
        mutations.add_path(g, Path(created_by=created, **raw), explores, consequences)

    for f in _files(root / "graph" / "beats"):
        raw = _read(f)
        belongs_to = raw.pop("belongs_to", [])
        mutations.add_beat(g, Beat(created_by=_created_by(raw, "beat"), **raw), belongs_to)

    for f in _files(root / "graph" / "intersections"):
        raw = _read(f)
        members = raw.pop("members")
        mutations.add_intersection(
            g, IntersectionGroup(created_by=_created_by(raw, "intersection"), **raw), members
        )

    flags_file = root / "graph" / "flags.yaml"
    if flags_file.exists():
        for raw in _read(flags_file).get("flags", []):
            derived = raw.pop("derived_from", [])
            mutations.add_flag(
                g, StateFlag(created_by=_created_by(raw, "flag"), **raw), derived
            )

    edges_file = root / "graph" / "edges.yaml"
    if edges_file.exists():
        for before, after in _read(edges_file).get("ordering", []):
            mutations.add_ordering(g, before, after)

    variant_links: list[tuple[str, str]] = []
    choices: list[tuple[str, str, Choice]] = []
    for f in _files(root / "graph" / "passages"):
        raw = _read(f)
        created = _created_by(raw, "passage")
        beats = raw.pop("beats")
        for c in raw.pop("choices", []):
            choices.append((raw["id"], c.pop("to"), Choice(**c)))
        if base := raw.pop("variant_of", None):
            variant_links.append((raw["id"], base))
        mutations.add_passage(g, Passage(created_by=created, **raw), beats)
    for src, dst, choice in choices:
        mutations.add_choice(g, src, dst, choice)
    for variant, base in variant_links:
        mutations.add_variant(g, variant, base)

    freeze_file = root / "graph" / "freeze.yaml"
    if freeze_file.exists():
        g.frozen = FreezeRecord.model_validate(_read(freeze_file))

    prose_dir = root / "prose"
    if prose_dir.is_dir():
        for f in sorted(prose_dir.glob("*.md")):
            passage_id = f"passage:{f.stem}"
            if passage_id in g:
                mutations.set_passage_prose(g, passage_id, f.read_text(encoding="utf-8"))

    voice_file = root / "voice.yaml"
    voice = Voice.model_validate(_read(voice_file)) if voice_file.exists() else None

    return Project(
        root=root,
        name=meta["name"],
        stage=stage,
        vision=vision,
        graph=g,
        voice=voice,
        fill_seed=int(meta.get("fill_seed", 0)),
        ifid=meta.get("ifid", ""),
        llm=meta.get("llm", dict(DEFAULT_LLM_CONFIG)),
        steering=meta.get("steering", {}),
    )


def _slug(node_id: str) -> str:
    return node_id.split(":", 1)[1]


def _dump_child(node, *, parent_stage: Stage) -> dict:
    """Dump an embedded child node (answer, consequence). The loader
    defaults a child's `created_by` to its parent's, so emit it only
    when it differs — keeping files terse and round-trips lossless."""
    data = {"id": node.id, "text": node.text}
    if node.created_by != parent_stage:
        data["created_by"] = node.created_by.value
    return data


def _dump(model, *, drop: set[str] = frozenset()) -> dict:  # type: ignore[assignment]
    data = model.model_dump(mode="json", exclude_defaults=True)
    data["id"] = model.id  # keep id even when it looks like a default
    kind = model.id.split(":", 1)[0]
    default = DEFAULT_STAGE.get(kind if kind in DEFAULT_STAGE else "entity")
    if model.created_by == default:
        data.pop("created_by", None)
    for key in drop:
        data.pop(key, None)
    return data


def save_project(project: Project) -> None:
    root = project.root
    g = project.graph
    meta: dict = {"name": project.name, "stage": project.stage.value}
    if project.fill_seed:
        meta["fill_seed"] = project.fill_seed
    if project.ifid:
        meta["ifid"] = project.ifid
    if project.llm != DEFAULT_LLM_CONFIG:
        meta["llm"] = project.llm
    if project.steering:
        meta["steering"] = project.steering
    _write(root / "project.yaml", meta)
    _write(root / "vision.yaml", project.vision.model_dump(mode="json", exclude_defaults=True))
    if project.voice is not None:
        _write(root / "voice.yaml", project.voice.model_dump(mode="json", exclude_defaults=True))

    for entity in g.nodes_of(Entity):
        default = DEFAULT_STAGE["entity"]
        data = _dump(entity)
        if entity.created_by == default:
            data.pop("created_by", None)
        _write(root / "graph" / "entities" / f"{_slug(entity.id)}.yaml", data)

    for dilemma in g.nodes_of(Dilemma):
        data = _dump(dilemma)
        data["answers"] = [
            _dump_child(g.node(a), parent_stage=dilemma.created_by)
            for a in g.out_ids(dilemma.id, EdgeKind.HAS_ANSWER)
        ]
        data["anchored_to"] = g.out_ids(dilemma.id, EdgeKind.ANCHORED_TO)
        for key, kind in RELATION_KEYS.items():
            if targets := g.out_ids(dilemma.id, kind):
                data[key] = targets
        _write(root / "graph" / "dilemmas" / f"{_slug(dilemma.id)}.yaml", data)

    for path in g.nodes_of(Path):
        data = _dump(path)
        (data["explores"],) = g.out_ids(path.id, EdgeKind.EXPLORES)
        data["consequences"] = [
            _dump_child(g.node(c), parent_stage=path.created_by)
            for c in g.out_ids(path.id, EdgeKind.HAS_CONSEQUENCE)
        ]
        _write(root / "graph" / "paths" / f"{_slug(path.id)}.yaml", data)

    for group in g.nodes_of(IntersectionGroup):
        data = _dump(group)
        data["members"] = sorted(g.in_ids(group.id, EdgeKind.IN_GROUP))
        _write(root / "graph" / "intersections" / f"{_slug(group.id)}.yaml", data)

    for beat in g.nodes_of(Beat):
        data = _dump(beat)
        if belongs := g.out_ids(beat.id, EdgeKind.BELONGS_TO):
            data["belongs_to"] = sorted(belongs)
        _write(root / "graph" / "beats" / f"{_slug(beat.id)}.yaml", data)

    if flags := g.nodes_of(StateFlag):
        entries = []
        for flag in sorted(flags, key=lambda f: f.id):
            data = _dump(flag)
            if derived := g.out_ids(flag.id, EdgeKind.DERIVED_FROM):
                data["derived_from"] = sorted(derived)
            entries.append(data)
        _write(root / "graph" / "flags.yaml", {"flags": entries})

    ordering = sorted(
        [e.src, e.dst] for e in g.edges if e.kind == EdgeKind.PREDECESSOR
    )
    if ordering:
        _write(root / "graph" / "edges.yaml", {"ordering": ordering})

    for passage in g.nodes_of(Passage):
        data = _dump(passage, drop={"prose"})
        if passage.prose:
            path = root / "prose" / f"{_slug(passage.id)}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(passage.prose, encoding="utf-8")
        data["beats"] = sorted(g.in_ids(passage.id, EdgeKind.GROUPED_IN))
        choices = []
        for e in g.out_edges(passage.id, EdgeKind.CHOICE):
            choice = {k: v for k, v in e.payload.items() if v}
            choice["to"] = e.dst
            choices.append(choice)
        if choices:
            data["choices"] = choices
        if bases := g.out_ids(passage.id, EdgeKind.VARIANT_OF):
            (data["variant_of"],) = bases
        _write(root / "graph" / "passages" / f"{_slug(passage.id)}.yaml", data)

    if g.frozen:
        _write(root / "graph" / "freeze.yaml", g.frozen.model_dump(mode="json"))


def scaffold_project(root: FSPath, name: str, scope: str) -> Project:
    if root.exists() and any(root.iterdir()):
        raise ProjectError(f"{root} already exists and is not empty")
    vision = Vision(
        premise="TODO: one paragraph — what is this story about?",
        genre="TODO",
        tone="TODO",
        scope=scope,
    )
    project = Project(
        root=root, name=name, stage=Stage.NEW, vision=vision, graph=StoryGraph()
    )
    save_project(project)
    for sub in ("entities", "dilemmas", "paths", "beats", "intersections", "passages"):
        (root / "graph" / sub).mkdir(parents=True, exist_ok=True)
    (root / "prose").mkdir(exist_ok=True)
    return project
