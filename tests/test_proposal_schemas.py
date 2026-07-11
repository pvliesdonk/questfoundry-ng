"""Every proposal schema must stay inside the JSON-Schema subset that
grammar-constrained decoding (the Ollama provider's `format`) and the
cloud providers' native structured-output modes handle. The adapter's
Pydantic validation is the contract either way, but a schema feature a
constrained decoder mishandles would over-constrain or fail on exactly
one provider — this lint catches that at commit time, not live.
"""

from __future__ import annotations

import importlib
import pkgutil

from pydantic import BaseModel

import questfoundry.pipeline.stages as stages_pkg

# JSON-Schema keywords pydantic v2 emits for the shapes the proposals
# use, all of them handled by llama.cpp's schema-to-grammar conversion.
# Growing this set is fine when the keyword is grammar-safe; anything
# else (pattern, oneOf, not, if/then, patternProperties, ...) needs a
# schema redesign, not an allowlist edit.
ALLOWED_KEYWORDS = {
    "title",
    "description",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "const",
    "anyOf",
    "$defs",
    "$ref",
    "default",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
}


def _proposal_models() -> list[type[BaseModel]]:
    modules = [
        importlib.import_module(f"{stages_pkg.__name__}.{info.name}")
        for info in pkgutil.iter_modules(stages_pkg.__path__)
    ]
    modules.append(importlib.import_module("questfoundry.pipeline.research"))
    models = []
    for mod in modules:
        for obj in vars(mod).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == mod.__name__
            ):
                models.append(obj)
    assert len(models) >= 30, "walker lost the stage modules"
    return models


def _check(schema: object, where: str, bad: list[str]) -> None:
    if not isinstance(schema, dict):
        return
    for key, value in schema.items():
        if key not in ALLOWED_KEYWORDS:
            bad.append(f"{where}: unsupported keyword {key!r}")
            continue
        if key in ("properties", "$defs"):
            for name, sub in value.items():
                _check(sub, f"{where}.{key}.{name}", bad)
        elif key in ("items", "additionalProperties"):
            _check(value, f"{where}.{key}", bad)
        elif key == "anyOf":
            for i, sub in enumerate(value):
                _check(sub, f"{where}.anyOf[{i}]", bad)


def test_proposal_schemas_stay_inside_the_constrained_decoding_subset() -> None:
    bad: list[str] = []
    for model in _proposal_models():
        _check(model.model_json_schema(), model.__name__, bad)
    assert not bad, "schemas outside the grammar-safe subset:\n" + "\n".join(bad)


def test_dynamic_triage_schema_stays_inside_the_subset() -> None:
    """Dynamically built schemas (SEED triage's per-project answer enum,
    issue #40) face the same grammar; the walker only sees module-level
    classes, so exercise the builder explicitly."""
    from questfoundry.pipeline.stages.seed import triage_proposal_schema

    schema = triage_proposal_schema(["answer:one-a", "answer:one-b"])
    bad: list[str] = []
    _check(schema.model_json_schema(), schema.__name__, bad)
    assert not bad, "schemas outside the grammar-safe subset:\n" + "\n".join(bad)


def test_every_stage_reference_pinned_schema_stays_inside_the_subset() -> None:
    """Every stage now builds per-project schemas that pin id-reference
    fields to `Literal` enums (pipeline/refpin.py). The walker can't see
    them (they're built at pass-run), so exercise each builder against the
    golden story and re-lint — an enum/const is grammar-safe, but a future
    builder that reached for `pattern` or `oneOf` would be caught here."""
    from questfoundry.pipeline.stages import dress, fill, polish, seed
    from questfoundry.project import load_project
    from tests.conftest import GOLDEN

    project = load_project(GOLDEN)
    schemas = [
        seed.scaffold_proposal_schema(project),
        seed.order_proposal_schema(project),
        polish.finalize_proposal_schema(project),
        polish.passages_proposal_schema(project),
        polish.audit_proposal_schema(project),
        *(spec.schema for spec in dress._passes(project)),
        *(
            spec.schema
            for spec in fill._passes(project)
            if spec.name.startswith("write:")
        ),
    ]
    bad: list[str] = []
    for schema in schemas:
        _check(schema.model_json_schema(), schema.__name__, bad)
    assert not bad, "schemas outside the grammar-safe subset:\n" + "\n".join(bad)
