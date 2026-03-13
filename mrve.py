"""
MRVE - Minimum Reproducible Viable Example
Panel/HoloViz + MCP Apps: Inline interactive charts with bidirectional communication.

Run: fastmcp run mrve.py

Core concept:
  1. LLM calls create_viz -> hvPlot builds chart -> Bokeh json_item() -> BokehJS renders in MCP Apps iframe
  2. User clicks chart -> iframe calls handle_click (app-only tool) -> server computes insight -> UI shows it
"""

import json
import uuid

import bokeh
import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
from bokeh.embed import json_item
from bokeh.models import CustomJS, NumeralTickFormatter, TapTool
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP

hv.extension("bokeh")

# --- Server setup ---
mcp = FastMCP(
    name="panel-viz-mrve",
    instructions="Create interactive charts with create_viz. Charts render inline in the conversation.",
)

_viz_store: dict[str, dict] = {}

# --- Constants ---
BOKEH_VERSION = bokeh.__version__
BOKEH_CDN = "https://cdn.bokeh.org/bokeh/release"
MCP_SDK = "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"
VIEW_URI = "ui://panel-viz-mrve/viz.html"
PALETTE = ["#818cf8", "#4ade80", "#f59e0b", "#f87171", "#38bdf8", "#c084fc"]
THEME = {
    "label": "#94a3b8", "tick": "#475569", "grid": "#334155",
    "grid_alpha": 0.5, "title": "#e0e0e0", "legend_text": "#94a3b8",
}


# --- Chart builder ---
def _build_chart(kind, df, x, y, title, color=None):
    """Build a Bokeh figure via hvPlot and serialize to JSON."""
    opts = {"title": title, "height": 350, "responsive": True, "x": x, "y": y}
    if color and color in df.columns:
        opts["by"] = color
    else:
        opts["color"] = PALETTE[0]

    method = getattr(df.hvplot, kind, df.hvplot.bar)
    fig = hv.render(method(**opts), backend="bokeh")

    # Theme
    fig.background_fill_alpha = 0
    fig.border_fill_alpha = 0
    fig.outline_line_alpha = 0
    for axis in fig.axis:
        axis.axis_label_text_color = THEME["label"]
        axis.major_label_text_color = THEME["label"]
        axis.major_tick_line_color = THEME["tick"]
        axis.minor_tick_line_color = None
        axis.axis_line_color = THEME["tick"]
    for grid in fig.grid:
        grid.grid_line_color = THEME["grid"]
        grid.grid_line_alpha = THEME["grid_alpha"]
    if fig.title:
        fig.title.text_color = THEME["title"]
        fig.title.text_font_size = "14px"
    if fig.legend:
        fig.legend.label_text_color = THEME["legend_text"]
        fig.legend.background_fill_alpha = 0
        fig.legend.border_line_alpha = 0

    fig.sizing_mode = "stretch_width"
    for axis in fig.yaxis:
        try:
            axis.formatter = NumeralTickFormatter(format="0,0.[00]")
        except Exception:
            pass

    # Click callback - dispatches bokeh-tap event to iframe JS
    fig.add_tools(TapTool())
    for renderer in fig.renderers:
        if hasattr(renderer, "data_source"):
            source = renderer.data_source
            cols = list(source.data.keys())
            x_key = x if x in source.data else cols[0]
            y_key = y if y in source.data else (cols[1] if len(cols) > 1 else cols[0])
            source.selected.js_on_change("indices", CustomJS(
                args=dict(source=source),
                code=(
                    "const idx = source.selected.indices;"
                    "if (!idx.length) return;"
                    "const i = idx[0];"
                    f"const xd = source.data['{x_key}'];"
                    f"const yd = source.data['{y_key}'];"
                    "if (!xd || !yd) return;"
                    "window.dispatchEvent(new CustomEvent('bokeh-tap', {"
                    "  detail: { index: i, xValue: String(xd[i]), yValue: Number(yd[i]) }"
                    "}));"
                ),
            ))
            break

    return json_item(fig, "chart-container")


# --- Tools ---
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def create_viz(
    kind: str, title: str, data: dict[str, list], x: str, y: str, color: str | None = None,
) -> str:
    """Create an interactive chart rendered inline in the conversation.

    Args:
        kind: Chart type - bar, line, scatter, or area
        title: Chart title
        data: Dict of column_name -> list of values
        x: Column for x-axis
        y: Column for y-axis
        color: Optional column for color grouping
    """
    try:
        df = pd.DataFrame(data)
        spec = _build_chart(kind, df, x, y, title, color)
        viz_id = str(uuid.uuid4())[:8]
        _viz_store[viz_id] = {"id": viz_id, "kind": kind, "title": title, "data": data, "x": x, "y": y}
        return json.dumps({"action": "create", "id": viz_id, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


@mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
def handle_click(viz_id: str, point_index: int, x_value: str, y_value: float) -> str:
    """Handle click event from the chart. Called by the app, not the LLM.

    Args:
        viz_id: ID of the clicked visualization
        point_index: Index of the clicked data point
        x_value: X-axis value of clicked point
        y_value: Y-axis value of clicked point
    """
    if viz_id not in _viz_store:
        return json.dumps({"action": "insight", "message": "Visualization not found"})
    viz = _viz_store[viz_id]
    df = pd.DataFrame(viz["data"])
    y_col = viz["y"]
    if y_col in df.columns:
        mean_val = df[y_col].mean()
        max_val = df[y_col].max()
        comparison = "above" if y_value > mean_val else "below"
        pct = round((y_value / max_val) * 100, 1) if max_val else 0
        message = f"Point: {x_value} = {y_value}\nThis is {comparison} the average ({mean_val:.1f}).\nIt represents {pct}% of the maximum ({max_val})."
    else:
        message = f"Clicked: {x_value} = {y_value}"
    return json.dumps({"action": "insight", "message": message})


# --- HTML Resource (MCP Apps) ---
@mcp.resource(
    VIEW_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://cdn.bokeh.org", "https://unpkg.com"])),
)
def viz_view() -> str:
    """Interactive chart viewer rendered inside the AI chat UI."""
    bokeh_scripts = "\n".join(
        f'  <script src="{BOKEH_CDN}/bokeh-{ext}{BOKEH_VERSION}.min.js" crossorigin="anonymous"></script>'
        for ext in ["", "gl-", "widgets-", "tables-"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <title>Panel Viz MRVE</title>
{bokeh_scripts}
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e0e0e0; padding: 8px; }}
    #chart-container {{ width: 100%; min-height: 320px; border-radius: 8px; overflow: hidden; }}
    #status {{ font-size: 12px; color: #64748b; padding: 4px 0; text-align: center; }}
    #insight-bar {{
      display: none; background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3);
      border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 13px;
      color: #93c5fd; white-space: pre-line;
    }}
    #viz-id {{ font-size: 11px; color: #64748b; text-align: right; padding: 2px 0; }}
    .loading {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; min-height: 200px; color: #64748b; font-size: 13px; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .spinner {{ width: 28px; height: 28px; border: 3px solid #334155; border-top-color: #818cf8; border-radius: 50%; animation: spin 0.8s linear infinite; }}
  </style>
</head>
<body>
  <div id="chart-container"><div class="loading"><div class="spinner"></div><span>Preparing chart...</span></div></div>
  <div id="insight-bar"></div>
  <div id="viz-id"></div>
  <div id="status">panel-viz-mrve ready</div>

  <script type="module">
    import {{ App }} from "{MCP_SDK}";
    const app = new App({{ name: "Panel Viz MRVE", version: "0.1.0" }});
    let currentVizId = null;

    // Bidirectional: chart click -> server tool -> insight displayed
    window.addEventListener('bokeh-tap', async (e) => {{
      if (!currentVizId) return;
      try {{
        const response = await app.callServerTool({{
          name: "handle_click",
          arguments: {{
            viz_id: currentVizId,
            point_index: e.detail.index,
            x_value: e.detail.xValue,
            y_value: e.detail.yValue,
          }},
        }});
        const t = response?.content?.find(c => c.type === "text");
        if (t) {{
          const r = JSON.parse(t.text);
          if (r.action === "insight") {{
            const bar = document.getElementById("insight-bar");
            bar.textContent = r.message;
            bar.style.display = "block";
          }}
        }}
      }} catch (err) {{ console.log('Click handler:', err); }}
    }});

    // LLM-initiated: receive chart data from create_viz tool
    app.ontoolresult = async ({{ content }}) => {{
      const textContent = content?.find(c => c.type === "text");
      if (!textContent) return;
      let result;
      try {{ result = JSON.parse(textContent.text); }} catch {{ return; }}

      if (result.action === "create") {{
        currentVizId = result.id;
        const container = document.getElementById("chart-container");
        container.innerHTML = "";
        try {{
          await Bokeh.embed.embed_item(result.figure);
          document.getElementById("status").textContent = "Chart created - click any data point for insights";
        }} catch (err) {{
          container.innerHTML = '<div style="color:#f87171;text-align:center;padding:20px;">Render error: ' + err.message + '</div>';
        }}
        document.getElementById("viz-id").textContent = "ID: " + result.id;
        document.getElementById("insight-bar").style.display = "none";
      }}

      if (result.action === "insight") {{
        const bar = document.getElementById("insight-bar");
        bar.textContent = result.message;
        bar.style.display = "block";
      }}

      if (result.action === "error") {{
        document.getElementById("chart-container").innerHTML =
          '<div style="color:#f87171;text-align:center;padding:20px;">' + result.message + '</div>';
      }}
    }};

    await app.connect();
    document.getElementById("status").textContent = "Connected - ready for charts";
  </script>
</body>
</html>"""
