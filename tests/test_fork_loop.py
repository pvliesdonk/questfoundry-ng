"""PR-5 acceptance (cosmetic-forks §6): an offline fixture drives the whole
finalize loop — residue round 0, engine-planned fork rounds to a terminal
round, per-site wording, minting, one keyword consumption — through POLISH's
real pass specs (skip/expand semantics exactly as the runner applies them),
and the result holds the acceptance criteria: every walk's words-per-choice
in the B6 band, a keyword per non-empty rendering, a consumed keyword behind
an I16-clean gated rendering, and a clean G4 gate."""

from __future__ import annotations

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import B6_WORDS_PER_CHOICE, Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import Vision
from questfoundry.models.drama import DilemmaRole, ResidueWeight
from questfoundry.models.structure import Beat, FlagSource, StateFlag, StructuralPurpose
from questfoundry.models.world import Entity
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from questfoundry.pipeline.stages.polish import POLISH_STAGE, _light_needs
from questfoundry.project.io import Project
from tests.conftest import make_dilemma
from tests.test_weave import scaffold


def _loop_project(tmp_path) -> Project:
    """A frozen, GROW-complete micro story with one long choice-less run
    (fork sites), a light-residue soft convergence (round 0), and enough
    retained cast for the gates."""
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD, residue=ResidueWeight.HEAVY)
    d2, p2a, p2b = make_dilemma(
        g, "sub", role=DilemmaRole.SOFT, residue=ResidueWeight.LIGHT,
        entity="character:main-anchor",
    )
    scaffold(g, "main", d1, p1a, p1b, pre=8)
    scaffold(g, "sub", d2, p2a, p2b, endings=False, pre=4)
    mutations.add_dilemma_relation(g, EdgeKind.WRAPS, d1, d2)
    planned = weave.plan(g)
    weave.realize(g, planned, weave.candidates(planned)[0])
    _derive_flags(g)
    for slug in ("extra", "extra2"):
        mutations.add_entity(
            g,
            Entity(
                id=f"character:{slug}", created_by=Stage.BRAINSTORM,
                name=slug, concept="c", retained=True,
            ),
        )
    mutations.freeze_topology(g)
    vision = Vision(premise="t", genre="t", tone="t", themes=["x"], scope="micro")
    return Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)


def _drive(project: Project, answer) -> list[tuple[str, str]]:
    """The runner's pass algorithm in miniature: skip_if, apply, expand —
    exactly `run_stage`'s loop minus the LLM/ledger plumbing (which
    test_runner covers generically)."""
    passes = list(POLISH_STAGE.passes)
    log: list[tuple[str, str]] = []
    i = 0
    while i < len(passes):
        spec = passes[i]
        reason = spec.skip_if(project) if spec.skip_if else None
        if reason:
            log.append((spec.name, f"skipped: {reason}"))
        else:
            spec.apply(answer(spec, project), project)
            log.append((spec.name, "done"))
        if spec.expand:
            passes[i + 1 : i + 1] = list(spec.expand(project))
        i += 1
    return log


def _scripted_answer():
    """Schema-valid proposals per pass, synthesized from each pass's own
    context — the fixture 'model'. Consumes the first offered keyword once."""
    state = {"n": 0, "consumed": False, "renderings": 0}

    def answer(spec, project):
        schema = spec.schema_for(project)
        ctx = spec.build_context(project)
        name = spec.name
        if name == "finalize:0":
            data = {
                "residue": [
                    {
                        "dilemma": n.dilemma,
                        "path": path,
                        "id": f"beat:res-{path.split(':')[1]}",
                        "summary": "the memory lingers",
                        **({"world": n.world} if n.world else {}),
                    }
                    for n in _light_needs(project)
                    for path in sorted(n.path_flags)
                ]
            }
        elif name.startswith("fork:"):
            seg = ctx["segment"]
            rends = []
            for _ in range(ctx["arms"]):
                state["n"] += 1
                rends.append(
                    {
                        "premise": f"the way of lantern {state['n']}",
                        "beats": [
                            {"id": f"beat:fk{state['n']}-{i}", "summary": f"moment {i}"}
                            for i in range(len(seg) or 1)
                        ],
                    }
                )
            state["renderings"] += len(rends) + (1 if seg else 0)
            data = {"renderings": rends}
            if seg:
                data["trunk_premise"] = "the road the beats already walk"
            if ctx["keywords"] and not seg and not state["consumed"]:
                state["n"] += 1
                data["gated"] = {
                    "keyword": ctx["keywords"][0][0],
                    "premise": "an echo for those who remember",
                    "beats": [{"id": f"beat:fk{state['n']}-g", "summary": "the mark returns"}],
                }
                state["consumed"] = True
                state["renderings"] += 1
        elif name.startswith("summary:"):
            i = int(name.split(":")[1])
            data = {
                "id": f"passage:p{i}",
                "summary": f"scene {i}",
                "ending_title": "An End" if ctx["is_ending"] else "",
                "variants": [],
            }
        elif name.startswith("labels:"):
            a = int(name.split(":")[1])
            data = {
                "labels": [
                    {"to": d["index"], "label": f"onward {a}-{d['index']}"}
                    for d in ctx["dests"]
                ]
            }
        elif name.startswith("audit:"):
            data = {
                "audit": [
                    {"passage": p["passage"].id, "irrelevant": []}
                    for p in ctx["passages"]
                ]
            }
        elif name == "arcs":
            data = {"arcs": [{"entity": e.id, "begins": "steady"} for e in ctx["entities"]]}
        else:
            raise AssertionError(f"unexpected live pass {name}")
        return schema.model_validate(data)

    return answer, state


def test_loop_runs_to_terminal_round_and_meets_the_acceptance_criteria(tmp_path):
    project = _loop_project(tmp_path)
    g = project.graph
    answer, state = _scripted_answer()
    log = _drive(project, answer)

    # the loop reached a terminal round, and the passage passes ran after it
    terminal = [n for n, s in log if n.startswith("finalize:") and "terminal" in s]
    assert terminal, log
    fork_passes = [n for n, s in log if n.startswith("fork:") and s == "done"]
    assert fork_passes  # at least one budget round did real work
    last_round = max(int(n.split(":")[1]) for n in fork_passes)
    assert last_round >= 2  # recursion: later rounds forked inside earlier renderings
    assert log.index((terminal[0], next(s for n, s in log if n == terminal[0]))) < len(log) - 1

    # every projected walk's words-per-choice lands in the B6 band
    lo, hi = B6_WORDS_PER_CHOICE
    for words, decisions in pc.projected_walks(g, project.vision.preset):
        assert lo <= words / max(decisions, 1) <= hi

    # every non-empty rendering minted exactly one keyword, granted on its head
    minted = [f for f in g.nodes_of(StateFlag) if f.source == FlagSource.COSMETIC]
    assert len(minted) == state["renderings"]
    for flag in minted:
        assert len(queries.grant_beats(g, flag.id)) == 1

    # exactly one keyword was consumed, by a gated rendering (I16's shape)
    consumed = sorted(
        f
        for b in g.nodes_of(Beat)
        for f in b.requires_flags
        if f.startswith("flag:cw-")
    )
    assert len(consumed) == 1
    (gated_beat,) = [
        b for b in g.nodes_of(Beat) if consumed[0] in b.requires_flags
    ]
    assert gated_beat.purpose == StructuralPurpose.FALSE_BRANCH
    # a consumed keyword is never offered again (one consumer per keyword)
    assert consumed[0] not in pc.offered_keywords(g, gated_beat.id)

    # the full POLISH gate set — I10-I16, G4 coverage, I13 — is clean
    issues = run_checks(g, project.vision, Stage.POLISH)
    assert [str(i) for i in issues if i.severity == Severity.ERROR] == []

    # expansion determinism (ledger resume): the terminal decision and the
    # final plan are pure functions of the graph
    assert pc.fork_plan(g, project.vision.preset) == []


def test_loop_expansion_names_are_deterministic(tmp_path):
    """The `finalize:<n>` chain resumes from the ledger iff the expansion is
    a pure function of the checkpointed graph (open question 4): the same
    graph must yield the same pass names, twice."""
    from questfoundry.pipeline.stages.polish import _round_spec

    project = _loop_project(tmp_path)
    expand = _round_spec(1).expand
    assert expand is not None
    names = [s.name for s in expand(project)]
    assert names == [s.name for s in expand(project)]
    assert names[-1] == "finalize:2" and names[0] == "fork:1:0"
