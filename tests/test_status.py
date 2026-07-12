"""`qf status` live-run state and spend (roadmap §M10 progress
reporting): the command reads the cost ledger and the A16 in-flight
ledger it already has — no new artifacts."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from questfoundry.cli import app
from questfoundry.project import scaffold_project


def test_status_reports_spend_and_inflight_run(tmp_path):
    scaffold_project(tmp_path, "probe", "micro")
    reports = tmp_path / "reports"
    reports.mkdir()
    entries = [
        {
            "ts": "2026-07-12T10:00:00+00:00",
            "role": "architect",
            "model": "m",
            "input_tokens": 1000,
            "output_tokens": 200,
            "cached": False,
            "retries": 0,
        },
        {
            "ts": "2026-07-12T10:01:00+00:00",
            "role": "utility",
            "model": "m",
            "input_tokens": 0,
            "output_tokens": 0,
            "cached": True,
            "retries": 0,
        },
    ]
    (reports / "ledger.jsonl").write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )
    proposals = tmp_path / "inflight" / "seed" / "proposals"
    proposals.mkdir(parents=True)
    (proposals / "triage.json").write_text(
        json.dumps({"pass": "triage", "proposal": {}}), encoding="utf-8"
    )

    result = CliRunner().invoke(app, ["status", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "llm spend: 2 calls (1 cached)" in result.output
    assert "in-flight: seed" in result.output
    assert "'triage'" in result.output


def test_status_stays_quiet_without_run_artifacts(tmp_path):
    scaffold_project(tmp_path, "probe", "micro")

    result = CliRunner().invoke(app, ["status", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "llm spend" not in result.output
    assert "in-flight" not in result.output
