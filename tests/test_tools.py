"""Comprehensive pytest tests for all panel-viz-mcp tools."""

import ast
import json

import pytest
from fastmcp import Client

from panel_viz_mcp.server import (
    _generate_panel_code,
    _generate_geo_panel_code,
    _generate_multi_panel_code,
    _viz_store,
    mcp,
)


@pytest.fixture
async def client():
    """Create a FastMCP test client."""
    c = Client(mcp)
    async with c:
        yield c


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_discovery(client):
    tools = await client.list_tools()
    names = {t.name for t in tools}
    expected = {
        "create_viz", "update_viz", "load_data", "handle_click", "list_vizs",
        "create_dashboard", "apply_filter", "set_theme", "stream_data",
        "create_multi_chart", "annotate_viz", "export_data",
        "launch_panel", "stop_panel", "create_panel_app",
    }
    assert expected.issubset(names), f"Missing tools: {expected - names}"


# ---------------------------------------------------------------------------
# create_viz - basic chart types
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["bar", "line", "scatter", "area", "pie", "histogram"])
async def test_create_viz_basic(client, kind):
    r = await client.call_tool("create_viz", {
        "kind": kind, "title": f"Test {kind}",
        "data": {"x": ["A", "B", "C"], "y": [10, 20, 15]},
        "x": "x", "y": "y",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "create"
    assert "figure" in result


@pytest.mark.asyncio
async def test_create_viz_step(client):
    r = await client.call_tool("create_viz", {
        "kind": "step", "title": "Test step",
        "data": {"x": [1, 2, 3, 4, 5], "y": [10, 20, 15, 25, 18]},
        "x": "x", "y": "y",
    })
    assert json.loads(r.content[0].text)["action"] == "create"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["box", "violin"])
async def test_create_viz_statistical(client, kind):
    r = await client.call_tool("create_viz", {
        "kind": kind, "title": f"Test {kind}",
        "data": {"group": ["A"] * 10 + ["B"] * 10, "value": list(range(20))},
        "x": "group", "y": "value",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "create"


@pytest.mark.asyncio
async def test_create_viz_kde(client):
    r = await client.call_tool("create_viz", {
        "kind": "kde", "title": "Test KDE",
        "data": {"x": list(range(50)), "value": [i ** 0.5 for i in range(50)]},
        "x": "x", "y": "value",
    })
    assert json.loads(r.content[0].text)["action"] == "create"


@pytest.mark.asyncio
async def test_create_viz_heatmap(client):
    r = await client.call_tool("create_viz", {
        "kind": "heatmap", "title": "Test Heatmap",
        "data": {"day": ["Mon", "Mon", "Tue"], "hour": ["9am", "2pm", "9am"], "val": [10, 20, 30]},
        "x": "day", "y": "hour", "color": "val",
    })
    assert json.loads(r.content[0].text)["action"] == "create"


@pytest.mark.asyncio
async def test_create_viz_hexbin(client):
    r = await client.call_tool("create_viz", {
        "kind": "hexbin", "title": "Test Hexbin",
        "data": {"x": list(range(100)), "y": [i * 1.5 + (i % 13) for i in range(100)]},
        "x": "x", "y": "y",
    })
    assert json.loads(r.content[0].text)["action"] == "create"


@pytest.mark.asyncio
async def test_create_viz_points(client):
    r = await client.call_tool("create_viz", {
        "kind": "points", "title": "Test Geo",
        "data": {"lon": [-73.9, -118.2], "lat": [40.7, 34.1], "city": ["NYC", "LA"]},
        "x": "lon", "y": "lat", "color": "city",
    })
    assert json.loads(r.content[0].text)["action"] == "create"


# ---------------------------------------------------------------------------
# create_viz - error cases
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_viz_bad_column(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Bad",
        "data": {"a": [1, 2], "b": [3, 4]},
        "x": "nonexistent", "y": "b",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "not found" in result["message"]


@pytest.mark.asyncio
async def test_create_viz_empty_data(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Empty",
        "data": {"x": [], "y": []},
        "x": "x", "y": "y",
    })
    result = json.loads(r.content[0].text)
    # Should either create successfully (empty chart) or return error
    assert result["action"] in ("create", "error")


# ---------------------------------------------------------------------------
# update_viz
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_viz(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Original",
        "data": {"x": ["A", "B"], "y": [10, 20]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("update_viz", {
        "viz_id": viz_id, "kind": "line", "title": "Updated",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "update"
    assert "figure" in result


@pytest.mark.asyncio
async def test_update_viz_bad_column(client):
    """Updating data without updating x/y should error if columns don't match."""
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Test",
        "data": {"x": ["A", "B"], "y": [10, 20]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("update_viz", {
        "viz_id": viz_id,
        "data": {"a": [1, 2], "b": [3, 4]},  # x/y columns don't exist here
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "not found" in result["message"]


@pytest.mark.asyncio
async def test_update_viz_nonexistent(client):
    r = await client.call_tool("update_viz", {"viz_id": "nope", "kind": "line"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"


# ---------------------------------------------------------------------------
# load_data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_load_data_csv(client):
    r = await client.call_tool("load_data", {
        "file_path": "examples/sample_data.csv",
        "kind": "bar", "x": "region", "y": "sales",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "create"
    assert "info" in result
    assert result["info"]["rows"] > 0


@pytest.mark.asyncio
async def test_load_data_missing_file(client):
    r = await client.call_tool("load_data", {
        "file_path": "nonexistent.csv", "kind": "bar", "x": "a", "y": "b",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"


# ---------------------------------------------------------------------------
# handle_click, list_vizs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_click(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Click Test",
        "data": {"x": ["A", "B"], "y": [100, 200]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("handle_click", {
        "viz_id": viz_id, "point_index": 0, "x_value": "A", "y_value": 100.0,
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "insight"
    assert "average" in result["message"].lower() or "above" in result["message"].lower()


@pytest.mark.asyncio
async def test_list_vizs(client):
    r = await client.call_tool("list_vizs", {})
    result = json.loads(r.content[0].text)
    assert result["action"] == "list"
    assert isinstance(result["visualizations"], list)


# ---------------------------------------------------------------------------
# create_dashboard + apply_filter + set_theme
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dashboard_flow(client):
    # Create
    r = await client.call_tool("create_dashboard", {
        "title": "Dash Test",
        "data": {"city": ["NYC", "LA", "CHI"], "pop": [8, 4, 3], "state": ["NY", "CA", "IL"]},
        "x": "city", "y": "pop",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "dashboard"
    assert all(k in result for k in ("figure", "stats", "table", "widget_config"))
    dash_id = result["id"]

    # Filter - categorical
    r = await client.call_tool("apply_filter", {
        "viz_id": dash_id, "filters": {"state": "NY"},
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "filter_result"
    assert result["filtered_rows"] == 1

    # Filter - clear
    r = await client.call_tool("apply_filter", {
        "viz_id": dash_id, "filters": {"state": "__all__"},
    })
    result = json.loads(r.content[0].text)
    assert result["filtered_rows"] == 3

    # Theme
    r = await client.call_tool("set_theme", {"viz_id": dash_id, "theme": "light"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "theme_change"
    assert result["theme"] == "light"


# ---------------------------------------------------------------------------
# stream_data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stream_data(client):
    r = await client.call_tool("stream_data", {
        "title": "Test Stream", "metric_name": "price", "initial_value": 100.0,
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "stream"
    assert result["config"]["initial_value"] == 100.0
    assert result["config"]["metric_name"] == "price"


# ---------------------------------------------------------------------------
# create_multi_chart
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_chart(client):
    r = await client.call_tool("create_multi_chart", {
        "title": "Multi Test",
        "data": {"x": [1, 2, 3], "y": [10, 20, 15], "cat": ["A", "B", "A"]},
        "charts": [
            {"kind": "bar", "x": "cat", "y": "y", "title": "Bar"},
            {"kind": "line", "x": "x", "y": "y", "title": "Line"},
        ],
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "multi_chart"
    assert result["chart_count"] == 2


# ---------------------------------------------------------------------------
# annotate_viz
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_annotate_viz(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Annotate Test",
        "data": {"x": ["A", "B"], "y": [10, 20]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("annotate_viz", {
        "viz_id": viz_id, "annotation_type": "hline",
        "config": {"y_value": 15, "color": "#ef4444", "label": "Target"},
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "update"
    assert "figure" in result


@pytest.mark.asyncio
async def test_annotate_stream_rejected(client):
    r = await client.call_tool("stream_data", {"title": "S"})
    stream_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("annotate_viz", {
        "viz_id": stream_id, "annotation_type": "hline",
        "config": {"y_value": 100},
    })
    assert json.loads(r.content[0].text)["action"] == "error"


# ---------------------------------------------------------------------------
# export_data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ["csv", "json"])
async def test_export_data(client, fmt):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Export Test",
        "data": {"x": ["A", "B"], "y": [10, 20]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("export_data", {"viz_id": viz_id, "format": fmt})
    result = json.loads(r.content[0].text)
    assert result["action"] == "export"
    assert result["format"] == fmt
    assert len(result["data"]) > 0


# ---------------------------------------------------------------------------
# launch_panel / stop_panel
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_launch_panel_stream_rejected(client):
    r = await client.call_tool("stream_data", {"title": "S"})
    stream_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("launch_panel", {"viz_id": stream_id})
    assert json.loads(r.content[0].text)["action"] == "error"


@pytest.mark.asyncio
async def test_stop_panel_nonexistent(client):
    r = await client.call_tool("stop_panel", {"viz_id": "nope"})
    assert json.loads(r.content[0].text)["action"] == "error"


@pytest.mark.asyncio
async def test_launch_and_stop_panel(client):
    r = await client.call_tool("create_multi_chart", {
        "title": "Launch Test",
        "data": {"x": [1, 2, 3], "y": [4, 5, 6], "cat": ["A", "B", "A"]},
        "charts": [{"kind": "bar", "x": "cat", "y": "y"}],
    })
    viz_id = json.loads(r.content[0].text)["id"]

    r = await client.call_tool("launch_panel", {"viz_id": viz_id})
    result = json.loads(r.content[0].text)
    assert result["action"] == "panel_launched"
    assert "url" in result

    # Cleanup
    await client.call_tool("stop_panel", {"viz_id": viz_id})


# ---------------------------------------------------------------------------
# create_panel_app
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_panel_app_basic(client):
    code = """
import panel as pn
pn.extension()
pn.pane.Markdown("# Hello from create_panel_app").servable()
"""
    r = await client.call_tool("create_panel_app", {"code": code, "title": "Test App"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "custom_app_launched"
    assert "url" in result
    assert result["title"] == "Test App"

    # Cleanup - stop the launched app
    from panel_viz_mcp.app import _panel_servers
    app_id = result["id"]
    if app_id in _panel_servers:
        import subprocess, sys
        info = _panel_servers[app_id]
        pid = info.get("panel_pid")
        if pid:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
                else:
                    import os
                    os.kill(pid, 9)
            except Exception:
                pass
        del _panel_servers[app_id]


@pytest.mark.asyncio
async def test_create_panel_app_syntax_error(client):
    r = await client.call_tool("create_panel_app", {
        "code": "def broken(:\n  pass", "title": "Bad Syntax",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "Syntax error" in result["message"]


@pytest.mark.asyncio
async def test_create_panel_app_missing_servable(client):
    r = await client.call_tool("create_panel_app", {
        "code": "import panel as pn\npn.pane.Markdown('hi')", "title": "No Servable",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "servable" in result["message"].lower()


# ---------------------------------------------------------------------------
# Code generation - syntax validity + key components
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_codegen_standard(client):
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "CodeGen Test",
        "data": {"region": ["East", "West"], "sales": [100, 200]},
        "x": "region", "y": "sales",
    })
    viz_id = json.loads(r.content[0].text)["id"]
    code = _generate_panel_code(_viz_store[viz_id])
    ast.parse(code)

    for comp in ["Tabulator", "indicators.Number", "FastListTemplate",
                 "hvplot", "pn.widgets.Select", "pn.pane.Alert"]:
        assert comp in code, f"Missing: {comp}"


@pytest.mark.asyncio
async def test_codegen_geo(client):
    r = await client.call_tool("create_viz", {
        "kind": "points", "title": "Geo CodeGen",
        "data": {"lon": [-74, -73.9], "lat": [40.7, 40.8], "city": ["NYC", "BK"]},
        "x": "lon", "y": "lat",
    })
    viz_id = json.loads(r.content[0].text)["id"]
    code = _generate_panel_code(_viz_store[viz_id])
    ast.parse(code)
    assert "DeckGL" in code
    assert "FastListTemplate" in code


@pytest.mark.asyncio
async def test_codegen_multi(client):
    r = await client.call_tool("create_multi_chart", {
        "title": "Multi CodeGen",
        "data": {"x": [1, 2, 3], "y": [4, 5, 6], "cat": ["A", "B", "A"]},
        "charts": [{"kind": "bar", "x": "cat", "y": "y"}],
    })
    viz_id = json.loads(r.content[0].text)["id"]
    code = _generate_panel_code(_viz_store[viz_id])
    ast.parse(code)
    assert "link_selections" in code
    assert "FastListTemplate" in code


@pytest.mark.asyncio
async def test_codegen_no_triple_quote_injection(client):
    """Data containing triple quotes should not break generated code."""
    r = await client.call_tool("create_viz", {
        "kind": "bar", "title": "Injection Test",
        "data": {"x": ['He said """hello"""', "normal"], "y": [10, 20]},
        "x": "x", "y": "y",
    })
    viz_id = json.loads(r.content[0].text)["id"]
    code = _generate_panel_code(_viz_store[viz_id])
    # Must be valid Python despite triple quotes in data
    ast.parse(code)


# ---------------------------------------------------------------------------
# Step chart with categorical X (was a bug - now auto-converts)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_viz_step_categorical(client):
    """Step chart with categorical X should work (auto-converts to numeric)."""
    r = await client.call_tool("create_viz", {
        "kind": "step", "title": "Step Categorical",
        "data": {"x": ["Mon", "Tue", "Wed", "Thu", "Fri"], "y": [10, 20, 15, 25, 18]},
        "x": "x", "y": "y",
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "create"
    assert "figure" in result


# ---------------------------------------------------------------------------
# stream_data input validation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stream_data_negative_volatility(client):
    r = await client.call_tool("stream_data", {
        "title": "Bad", "volatility": -1.0,
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "volatility" in result["message"]


@pytest.mark.asyncio
async def test_stream_data_bad_points(client):
    r = await client.call_tool("stream_data", {
        "title": "Bad", "points": 0,
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "points" in result["message"]


@pytest.mark.asyncio
async def test_stream_data_bad_interval(client):
    r = await client.call_tool("stream_data", {
        "title": "Bad", "interval_ms": 10,
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "interval_ms" in result["message"]


# ---------------------------------------------------------------------------
# create_panel_app sandboxing
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_panel_app_blocked_import_os(client):
    code = "import os\nimport panel as pn\npn.pane.Markdown('hi').servable()"
    r = await client.call_tool("create_panel_app", {"code": code, "title": "Bad"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "Blocked" in result["message"]


@pytest.mark.asyncio
async def test_create_panel_app_blocked_import_subprocess(client):
    code = "import subprocess\nimport panel as pn\npn.pane.Markdown('hi').servable()"
    r = await client.call_tool("create_panel_app", {"code": code, "title": "Bad"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "Blocked" in result["message"]


@pytest.mark.asyncio
async def test_create_panel_app_blocked_from_import(client):
    code = "from os import system\nimport panel as pn\npn.pane.Markdown('hi').servable()"
    r = await client.call_tool("create_panel_app", {"code": code, "title": "Bad"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "Blocked" in result["message"]


@pytest.mark.asyncio
async def test_create_panel_app_blocked_eval(client):
    code = "import panel as pn\neval('1+1')\npn.pane.Markdown('hi').servable()"
    r = await client.call_tool("create_panel_app", {"code": code, "title": "Bad"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "error"
    assert "Blocked" in result["message"]


@pytest.mark.asyncio
async def test_create_panel_app_allowed_imports(client):
    """Allowed imports (numpy, pandas, math) should not be blocked."""
    code = """
import panel as pn
import numpy as np
import pandas as pd
import math
pn.pane.Markdown(f"pi = {math.pi}").servable()
"""
    r = await client.call_tool("create_panel_app", {"code": code, "title": "OK"})
    result = json.loads(r.content[0].text)
    assert result["action"] == "custom_app_launched"

    # Cleanup
    from panel_viz_mcp.app import _panel_servers
    import subprocess as _sp
    app_id = result["id"]
    if app_id in _panel_servers:
        pid = _panel_servers[app_id].get("panel_pid")
        if pid:
            try:
                _sp.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
            except Exception:
                pass
        del _panel_servers[app_id]


# ---------------------------------------------------------------------------
# MCP SDK URL centralized in constants
# ---------------------------------------------------------------------------
def test_mcp_sdk_url_centralized():
    """All HTML resources should use the same SDK URL from constants."""
    from panel_viz_mcp.constants import MCP_APPS_SDK_URL
    from panel_viz_mcp.resources.viz_html import viz_view
    from panel_viz_mcp.resources.dashboard_html import dashboard_view
    from panel_viz_mcp.resources.stream_html import stream_view
    from panel_viz_mcp.resources.multi_html import multi_view

    for view_fn in (viz_view, dashboard_view, stream_view, multi_view):
        html = view_fn()
        assert MCP_APPS_SDK_URL in html, f"{view_fn.__name__} missing SDK URL"


# ---------------------------------------------------------------------------
# Multi-chart color empty string edge case
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_chart_empty_color(client):
    """Empty string color should not cause issues."""
    r = await client.call_tool("create_multi_chart", {
        "title": "Color Test",
        "data": {"x": [1, 2, 3], "y": [10, 20, 15]},
        "charts": [{"kind": "bar", "x": "x", "y": "y", "color": ""}],
    })
    result = json.loads(r.content[0].text)
    assert result["action"] == "multi_chart"
