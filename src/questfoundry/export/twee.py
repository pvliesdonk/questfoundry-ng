"""Twee 3 / SugarCube 2 export (design doc 04 §3) — the escape hatch
into the Twine ecosystem.

Grants are uniform per *target* passage (they derive from the commit
beats it contains), so each passage sets its granted flags in a header
<<silently>> block on entry, and `requires` become <<if>> guards around
links. Prose markdown passes through with a bounded mapping (paragraphs
survive; anything fancier is flagged to the author by the lint step,
which arrives with SHIP).
"""

from __future__ import annotations

import re

from questfoundry.export.runtime_json import build_runtime
from questfoundry.project.io import Project


def _var(flag_id: str) -> str:
    return "$f_" + re.sub(r"[^a-z0-9]+", "_", flag_id.split(":", 1)[1])


def build_twee(project: Project, ifid: str) -> str:
    data = build_runtime(project)
    lines = [
        ":: StoryTitle",
        data["meta"]["title"],
        "",
        ":: StoryData",
        "{",
        f'  "ifid": "{ifid}",',
        '  "format": "SugarCube",',
        '  "format-version": "2.37.3",',
        f'  "start": "{data["start"]}"',
        "}",
        "",
    ]
    # flags granted on entering a passage (uniform across its incoming choices)
    granted_on_entry: dict[str, set[str]] = {pid: set() for pid in data["passages"]}
    for p in data["passages"].values():
        for c in p["choices"]:
            granted_on_entry[c["to"]].update(c["grants"])

    for pid, p in data["passages"].items():
        lines.append(f":: {pid}")
        grants = sorted(granted_on_entry[pid])
        if grants:
            sets = "".join(f"<<set {_var(f)} to true>>" for f in grants)
            lines.append(f"<<silently>>{sets}<</silently>>")
        lines.append(p["prose"].strip())
        lines.append("")
        if p["ending"]:
            lines.append(f"''{p['ending']['title']}''")
        for c in p["choices"]:
            link = f"[[{c['label']}->{c['to']}]]"
            if c["requires"]:
                condition = " and ".join(_var(f) for f in c["requires"])
                link = f"<<if {condition}>>{link}<</if>>"
            lines.append(link)
        lines.append("")
    return "\n".join(lines)
