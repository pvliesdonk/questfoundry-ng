"""Pin proposal-schema id-reference fields to per-project enums (#40,
generalized across every stage).

A proposal field whose value must name an id that *already exists* — an
entity, dilemma, answer, beat, path, world, flag, or passage — is a
reference, and a model that invents a readable-but-dangling value for one
exhausts repairs (Ollama live validation, 2026-07-11: two strong families
converged on the same triage dangling-reference; a later gpt-oss:120b
cloud run repeated it one field over). #40 pinned SEED triage's `explores`
and `locked[].dilemma`; the same discipline generalizes here.

Pinning rebuilds the Pydantic model with each reference field typed as a
`Literal` enum of the real ids (graph order — an ordered enum a model
could read as ranked must at least not be *our* ranking, and only answers
carry the strict-equality marker iron rule 3 protects; every other id
kind orders freely). Under grammar-constrained decoding (A20) a dangling
reference then cannot be emitted at all; every other provider sees the
constraint in the schema and the correction brief names the valid ids on
a miss. The apply-layer guards stay the contract — the enums narrow the
space, the guards still enforce the joint constraints an independent enum
cannot express (e.g. finalize's (dilemma, world, path) triple).

`pin` handles leaf `str` and `list[str]` fields. Nested spec lists (e.g.
`paths: list[PathSpec] = Field(min_length=2)`) rebuild the inner spec with
`pin`, then re-attach the list explicitly so the outer field's constraints
survive — `enum_type` is exposed for that and other bespoke wiring.
"""

from __future__ import annotations

from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, create_model

from questfoundry.models.world import Entity


def enum_type(ids: list[str]) -> Any:
    """`Literal[id0, id1, ...]` for the given ids, in the order supplied."""
    return Literal[tuple(ids)]  # type: ignore[valid-type]


def _nested_model(anno: Any) -> tuple[type[BaseModel] | None, Any]:
    """If `anno` wraps a BaseModel (bare, `list[M]`, or `M | None`), return
    (M, rebuild) where rebuild(new_M) reconstructs the wrapper; else
    (None, None)."""
    origin = get_origin(anno)
    if origin is list:
        (arg,) = get_args(anno)
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg, lambda new: list[new]  # type: ignore[valid-type]
    elif origin in (Union, UnionType):
        rest = [a for a in get_args(anno) if a is not type(None)]
        if len(rest) == 1 and isinstance(rest[0], type) and issubclass(rest[0], BaseModel):
            return rest[0], lambda new: new | None
    elif isinstance(anno, type) and issubclass(anno, BaseModel):
        return anno, lambda new: new
    return None, None


def pin(
    model: type[BaseModel],
    name: str,
    resolvers: dict[tuple[str, str], list[str]],
    _cache: dict[type[BaseModel], type[BaseModel]] | None = None,
) -> type[BaseModel]:
    """Rebuild `model` as `name`, recursively rebuilding every nested spec,
    pinning each leaf `str` / `list[str]` field named in `resolvers` to a
    `Literal` enum of its ids.

    `resolvers` maps `(spec_class_name, field_name)` to the valid id list
    (graph order) — so the same nested spec (e.g. `BeatSpec.entities`) is
    pinned identically everywhere it appears. A field with an empty id list
    is left unpinned. Each field's `FieldInfo` (default, `min_length`, …)
    is preserved; a subtree with nothing to pin returns unchanged, so
    `$defs` stay minimal and callers stay total.
    """
    cache: dict[type[BaseModel], type[BaseModel]] = {} if _cache is None else _cache
    if model in cache:
        return cache[model]
    overrides: dict[str, Any] = {}
    for fname, f in model.model_fields.items():
        inner, rebuild = _nested_model(f.annotation)
        if inner is not None:
            rebuilt = pin(inner, inner.__name__, resolvers, cache)
            if rebuilt is not inner:
                overrides[fname] = (rebuild(rebuilt), f)
            continue
        ids = resolvers.get((model.__name__, fname))
        if not ids:
            continue
        origin = get_origin(f.annotation)
        # Only plain `str` / `list[str]` reference fields are pinnable. A
        # future `str | None` would land here as a Union and silently lose
        # its `| None` (the enum would force a value) — fail loud instead so
        # whoever adds that field pins it deliberately (e.g. include "" in
        # the ids, as intersection `location` does).
        if not (f.annotation is str or (origin is list and get_args(f.annotation) == (str,))):
            raise TypeError(
                f"cannot pin {model.__name__}.{fname}: only str / list[str] reference "
                f"fields are pinnable, got {f.annotation!r}"
            )
        lit = enum_type(ids)
        typ = list[lit] if origin is list else lit  # type: ignore[valid-type]
        overrides[fname] = (typ, f)
    result = model if not overrides else create_model(name, __base__=model, **overrides)
    cache[model] = result
    return result


def retained_entity_ids(g: Any) -> list[str]:
    """Every retained entity's exact `kind:slug` id — the valid set for a
    field validated by *exact* membership (`g.get(id)` / `id in retained`),
    which does not accept the bare slug."""
    return [e.id for e in g.nodes_of(Entity) if e.retained]


def entity_ref_ids(g: Any) -> list[str]:
    """Valid values for a proposal field routed through `resolve_entity_ref`
    (pipeline/types.py): every retained entity's exact `kind:slug` id, plus
    each provably-unambiguous bare slug that resolver also accepts — so
    pinning to this set makes dangling refs unrepresentable without
    regressing the bare-slug affordance (mini-ADR A11). For exact-membership
    fields use `retained_entity_ids` instead — a slug the enum allowed but
    the apply rejects would just trade one dangling failure for another."""
    ids = retained_entity_ids(g)
    slugs = [i.split(":", 1)[1] for i in ids]
    unambiguous = [s for s in slugs if slugs.count(s) == 1]
    return ids + unambiguous
