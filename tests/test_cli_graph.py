"""`qf graph` Mermaid output: node ids must survive the renderer. A
world-suffixed beat id carries the `--` world separator, which Mermaid's
flowchart parser reads as the start of an edge — the raw slug broke the
diagram on the first per-world beat (live closed-circle-medium,
2026-07-14)."""

from __future__ import annotations

from typer.testing import CliRunner

from questfoundry.cli import app
from questfoundry.graph import mutations
from questfoundry.project import scaffold_project
from questfoundry.project.io import save_project
from tests.conftest import make_dilemma, narrative_beat

runner = CliRunner()


def test_graph_beats_mermaid_has_no_double_dash_ids(tmp_path):
    project = scaffold_project(tmp_path, "probe", "micro")
    g = project.graph
    dilemma, path_a, _ = make_dilemma(g, "core")
    for slug in ("opening--world-a", "closing--world-a"):
        mutations.add_beat(g, narrative_beat(slug, dilemma), [path_a])
    mutations.add_ordering(g, "beat:opening--world-a", "beat:closing--world-a")
    save_project(project)

    result = runner.invoke(app, ["graph", str(tmp_path), "--layer", "beats"])
    assert result.exit_code == 0
    body = result.stdout
    assert "opening__world-a" in body and "closing__world-a" in body
    # no node id or edge endpoint keeps the raw separator — quoted label
    # text may (Mermaid allows it there); ids are what the parser trips on
    import re

    for line in body.splitlines():
        ids_only = re.sub(r'"[^"]*"', "", line).replace("-->", "")
        assert "--" not in ids_only, line
