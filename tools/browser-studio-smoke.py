#!/usr/bin/env python3
"""Read-only UI acceptance check; run with the launched native WELD-X preview.

Requires Playwright with a local Chromium browser. No ROS commands are sent,
no engineering approval is attempted and no task is executed.
"""
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("WELDX_UI_URL", "http://127.0.0.1:8765")
OUT = ROOT / ".runtime" / "studio-smoke"
OUT.mkdir(parents=True,exist_ok=True)
result = {"url":URL,"checks":[],"errors":[]}
try:
    with sync_playwright() as playwright:
        options={"headless":True}
        executable=os.environ.get("WELDX_CHROMIUM")
        if executable:options["executable_path"]=executable
        browser=playwright.chromium.launch(**options)
        page=browser.new_page(viewport={"width":1600,"height":1000},device_scale_factor=1)
        page.on("pageerror", lambda error: result["errors"].append(str(error)))
        page.goto(URL,wait_until="domcontentloaded",timeout=30000)
        page.locator("#view-mode").wait_for(timeout=60000)
        page.wait_for_function(
            "() => /STATIC GLB|ROS JOINT MODEL|SCENE UNAVAILABLE|VIEWER OFFLINE/.test(document.getElementById('view-mode').textContent)",
            timeout=80000)
        view=page.locator("#view-mode").inner_text()
        result["view_mode"]=view
        if view not in ("STATIC GLB / CAD PREVIEW", "ROS JOINT MODEL / LIVE"):
            raise AssertionError("Viewer did not initialize: "+page.locator("#scene-status").inner_text())
        page.locator("#cell-view canvas").wait_for(timeout=20000)
        result["checks"].append("WebGL 3D renderer created a canvas")
        for preset in ["view-top","view-side","view-home","view-robot"]:
            page.locator("#"+preset).click()
            assert page.locator("#"+preset).get_attribute("aria-pressed")=="true"
        result["checks"].append("Camera presets respond")
        page.locator("#view-focus").click()
        assert "viewer-expanded" in page.locator("#twin").get_attribute("class")
        page.locator("#view-focus").click()
        assert "viewer-expanded" not in page.locator("#twin").get_attribute("class")
        result["checks"].append("Viewport expand/restore works")
        if view=="STATIC GLB / CAD PREVIEW":
            page.wait_for_function(
                "() => document.getElementById('scene-status').textContent.startsWith('SOURCE GLB PREVIEW')",
                timeout=80000)
            result["checks"].append("Real source GLB mesh load completed")
            assert "STATIC" in page.locator("#inspector-source").inner_text()
            assert page.locator("#execute").is_disabled()
            assert "NOT JOINT SYNCHRONIZED" in page.locator("#view-accuracy").inner_text()
            result["checks"].append("Static visual is clearly distinguished from joint feedback; execution locked")
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        page.wait_for_timeout(750)
        if not page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"):
            raise AssertionError("Mobile page overflows horizontally")
        page.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        result["checks"].append("Mobile width has no page overflow")
        browser.close()
    if result["errors"]:raise AssertionError(str(result["errors"]))
    result["status"]="passed"
except Exception as error:
    result["status"]="failed"
    result["errors"].append(str(error))
finally:
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
sys.exit(0 if result["status"]=="passed" else 1)
