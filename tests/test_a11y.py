"""axe-core over the exported HTML players (design doc 04 §7, gamebook layouts).

The layouts contract requires an axe-core pass over exported HTML for a
handful of sections per screen style. The scan is WCAG-scoped (2.0/2.1
A+AA tags) so a failure cites the accessibility contract, not axe's
best-practice opinions.

Needs a Playwright Chromium. Without one the module skips — except under
QF_A11Y_STRICT=1 (set by the CI a11y job, which installs the browser
first), where an unavailable browser is a failure, never a silent pass.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from questfoundry.export.html import build_html
from questfoundry.export.style import SCREEN_STYLES, screen_style

pytestmark = pytest.mark.a11y

WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
AXE_OPTIONS = {"runOnly": {"type": "tag", "values": WCAG_TAGS}}
TURNS = 3  # choice clicks after the opening section — "a handful of sections"
FADE_MS = 400  # past the player's 180ms cross-fade before scanning


def _unavailable(reason: str):
    if os.environ.get("QF_A11Y_STRICT"):
        pytest.fail(f"QF_A11Y_STRICT is set but {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        _unavailable("playwright is not installed")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Error:
            # the environment may carry a system chromium instead of a
            # playwright-managed download (e.g. an agent sandbox)
            system = Path(os.environ.get("QF_CHROMIUM", "/opt/pw-browsers/chromium"))
            if not system.exists():
                _unavailable("no chromium available for playwright")
            browser = p.chromium.launch(executable_path=str(system))
        yield browser
        browser.close()


def _scan(axe, page, state: str, violations: list[str]) -> None:
    response = axe.run(page, options=AXE_OPTIONS).response
    for violation in response["violations"]:
        targets = ", ".join(str(node["target"]) for node in violation["nodes"][:5])
        violations.append(
            f"[{state}] {violation['id']} ({violation['impact']}): "
            f"{violation['help']} — {targets}"
        )


def _player_page(browser, tmp_path: Path, style_name: str, *, large_print: bool = False):
    from questfoundry.project import load_project
    from tests.conftest import GOLDEN

    html = build_html(
        load_project(GOLDEN), style=screen_style(style_name, large_print=large_print)
    )
    suffix = "-lp" if large_print else ""
    path = tmp_path / f"{style_name}{suffix}.html"
    path.write_text(html, encoding="utf-8")
    page = browser.new_page()
    page.goto(path.as_uri())
    return page


@pytest.mark.parametrize("style_name", sorted(SCREEN_STYLES))
def test_exported_player_passes_axe(browser, tmp_path, style_name):
    from axe_playwright_python.sync_playwright import Axe

    axe = Axe()
    page = _player_page(browser, tmp_path, style_name)
    violations: list[str] = []

    _scan(axe, page, "title screen", violations)
    page.click("#begin")
    page.wait_for_selector("#choices button")
    _scan(axe, page, "opening section", violations)

    for turn in range(1, TURNS + 1):
        choices = page.locator("#choices button")
        if choices.count() == 0:  # reached an ending
            break
        choices.first.click()
        page.wait_for_timeout(FADE_MS)
        _scan(axe, page, f"turn {turn}", violations)

    page.close()
    assert not violations, "axe (WCAG A/AA) violations:\n" + "\n".join(violations)


def test_the_scan_detects_a_planted_violation(browser, tmp_path):
    # violating construction for the harness itself: a page with a known
    # WCAG failure (img without alt) must produce a finding, proving the
    # green runs above are scans, not vacuous passes
    from axe_playwright_python.sync_playwright import Axe

    axe = Axe()
    path = tmp_path / "planted.html"
    path.write_text(
        "<!doctype html><html lang='en'><head><title>planted</title></head>"
        "<body><main><h1>planted</h1><img src='x.png'></main></body></html>",
        encoding="utf-8",
    )
    page = browser.new_page()
    page.goto(path.as_uri())
    violations: list[str] = []
    _scan(axe, page, "planted", violations)
    page.close()
    assert any("image-alt" in v for v in violations)


@pytest.mark.parametrize("style_name", sorted(SCREEN_STYLES))
def test_large_print_modifier_passes_axe(browser, tmp_path, style_name):
    from axe_playwright_python.sync_playwright import Axe

    axe = Axe()
    page = _player_page(browser, tmp_path, style_name, large_print=True)
    violations: list[str] = []

    _scan(axe, page, "title screen", violations)
    page.click("#begin")
    page.wait_for_selector("#choices button")
    _scan(axe, page, "opening section", violations)

    page.close()
    assert not violations, "axe (WCAG A/AA) violations:\n" + "\n".join(violations)
