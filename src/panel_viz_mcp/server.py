"""panel-viz-mcp: Interactive Panel/HoloViews visualizations inside AI chats via MCP Apps."""

import atexit
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import uuid
import webbrowser

import bokeh
import holoviews as hv
import hvplot.pandas  # noqa: F401 - enables df.hvplot()
import pandas as pd
from bokeh.embed import json_item
from bokeh.models import (
    Arrow,
    BoxAnnotation,
    ColumnDataSource,
    CustomJS,
    Label,
    NormalHead,
    Span,
    TapTool,
)
from bokeh.palettes import Category10
from bokeh.plotting import figure as bokeh_figure
from bokeh.transform import cumsum
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP

hv.extension("bokeh")

# ---------------------------------------------------------------------------
# BokehJS CDN scripts
# ---------------------------------------------------------------------------
BOKEH_VERSION = bokeh.__version__
_BOKEH_BASE = "https://cdn.bokeh.org/bokeh/release"
BOKEH_SCRIPTS = "\n".join(
    f'  <script src="{_BOKEH_BASE}/bokeh-{ext}{BOKEH_VERSION}.min.js" crossorigin="anonymous"></script>'
    for ext in ["", "gl-", "widgets-", "tables-"]
)
BOKEH_SCRIPTS_WITH_API = "\n".join(
    f'  <script src="{_BOKEH_BASE}/bokeh-{ext}{BOKEH_VERSION}.min.js" crossorigin="anonymous"></script>'
    for ext in ["", "gl-", "widgets-", "tables-", "api-"]
)

# ---------------------------------------------------------------------------
# Theme system
# ---------------------------------------------------------------------------
THEME_COLORS = {
    "dark": {
        "label": "#94a3b8",
        "tick": "#475569",
        "grid": "#334155",
        "grid_alpha": 0.5,
        "title": "#e0e0e0",
        "legend_text": "#94a3b8",
    },
    "light": {
        "label": "#374151",
        "tick": "#d1d5db",
        "grid": "#e5e7eb",
        "grid_alpha": 0.8,
        "title": "#111827",
        "legend_text": "#374151",
    },
}

# CSS variables for HTML resources - shared across all views
_CSS_THEME_VARS = """
    body.theme-dark {
      --text-primary: #e0e0e0; --text-secondary: #94a3b8; --text-muted: #64748b;
      --bg-card: rgba(30,41,59,0.6); --bg-surface: rgba(15,23,42,0.5);
      --border: #334155; --accent: #818cf8; --accent-bg: rgba(99,102,241,0.08);
      --error: #f87171; --success: #4ade80; --warning: #f59e0b;
      --btn-bg: #1e293b; --btn-border: #334155; --input-bg: #0f172a;
      --stat-value: #818cf8; --table-header-bg: #1e293b;
    }
    body.theme-light {
      --text-primary: #1f2937; --text-secondary: #6b7280; --text-muted: #9ca3af;
      --bg-card: rgba(255,255,255,0.9); --bg-surface: rgba(249,250,251,0.8);
      --border: #e5e7eb; --accent: #6366f1; --accent-bg: rgba(99,102,241,0.06);
      --error: #dc2626; --success: #16a34a; --warning: #d97706;
      --btn-bg: #f9fafb; --btn-border: #d1d5db; --input-bg: #ffffff;
      --stat-value: #6366f1; --table-header-bg: #f3f4f6;
    }
"""

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="panel-viz-mcp",
    instructions=(
        "You are a visualization assistant that creates interactive charts "
        "directly in the conversation using the HoloViz ecosystem (Panel, "
        "HoloViews, hvPlot). Use create_viz to make new charts, update_viz "
        "to modify existing ones, load_data to visualize files, "
        "create_multi_chart for multi-panel views, annotate_viz to add "
        "annotations, export_data to download data, and launch_panel to "
        "open a full interactive Panel dashboard in the browser."
    ),
)

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_viz_store: dict[str, dict] = {}
_panel_servers: dict[str, dict] = {}

VIEW_URI = "ui://panel-viz-mcp/viz.html"
DASHBOARD_URI = "ui://panel-viz-mcp/dashboard.html"
STREAM_URI = "ui://panel-viz-mcp/stream.html"
MULTI_URI = "ui://panel-viz-mcp/multi.html"

CHART_TYPES = [
    "bar", "line", "scatter", "area", "pie", "histogram",
    "box", "violin", "kde", "step", "heatmap", "hexbin", "points",
]
ANNOTATION_TYPES = ["text", "hline", "vline", "band", "arrow"]


# ---------------------------------------------------------------------------
# Chart building helpers
# ---------------------------------------------------------------------------
def _apply_theme(fig, theme: str = "dark"):
    """Apply theme styling to a Bokeh figure."""
    colors = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    fig.background_fill_alpha = 0
    fig.border_fill_alpha = 0
    fig.outline_line_alpha = 0

    for axis in fig.axis:
        axis.axis_label_text_color = colors["label"]
        axis.major_label_text_color = colors["label"]
        axis.major_tick_line_color = colors["tick"]
        axis.minor_tick_line_color = None
        axis.axis_line_color = colors["tick"]

    for grid in fig.grid:
        grid.grid_line_color = colors["grid"]
        grid.grid_line_alpha = colors["grid_alpha"]

    if fig.title:
        fig.title.text_color = colors["title"]
        fig.title.text_font_size = "14px"

    if fig.legend:
        fig.legend.label_text_color = colors["legend_text"]
        fig.legend.background_fill_alpha = 0
        fig.legend.border_line_alpha = 0


def _build_bokeh_figure(kind: str, df: pd.DataFrame, x: str, y: str,
                        title: str, color: str | None = None,
                        target_id: str = "chart-container",
                        theme: str = "dark"):
    """Build a Bokeh figure using hvPlot/HoloViews and serialize to JSON."""
    if kind not in CHART_TYPES:
        raise ValueError(f"Unsupported chart type: {kind}. Supported: {CHART_TYPES}")

    if x not in df.columns:
        raise ValueError(f"Column '{x}' not found. Available: {list(df.columns)}")
    if y not in df.columns:
        raise ValueError(f"Column '{y}' not found. Available: {list(df.columns)}")
    if color and color not in df.columns:
        raise ValueError(f"Color column '{color}' not found. Available: {list(df.columns)}")

    if kind == "pie":
        fig = _build_pie_chart(df, x, y, title, theme)
    else:
        fig = _build_hvplot_chart(kind, df, x, y, title, color)
        _apply_theme(fig, theme)

    fig.add_tools(TapTool())
    _add_click_callbacks(fig, x, y)

    return json_item(fig, target_id)


def _build_hvplot_chart(kind: str, df: pd.DataFrame, x: str, y: str,
                        title: str, color: str | None = None):
    """Create a chart with hvPlot and convert to Bokeh figure."""
    base = {"title": title, "width": 600, "height": 350}

    # Standard x/y charts
    simple_methods = {
        "bar": df.hvplot.bar,
        "line": df.hvplot.line,
        "scatter": df.hvplot.scatter,
        "area": df.hvplot.area,
        "step": df.hvplot.step,
    }

    if kind in simple_methods:
        kwargs = {**base, "x": x, "y": y}
        if color and color in df.columns:
            kwargs["by"] = color
        plot = simple_methods[kind](**kwargs)

    elif kind == "histogram":
        kwargs = {**base, "y": y}
        if color and color in df.columns:
            kwargs["by"] = color
        plot = df.hvplot.hist(**kwargs)

    elif kind == "box":
        kwargs = {**base, "y": y}
        if x and x in df.columns and not pd.api.types.is_numeric_dtype(df[x]):
            kwargs["by"] = x
        plot = df.hvplot.box(**kwargs)

    elif kind == "violin":
        kwargs = {**base, "y": y}
        if x and x in df.columns and not pd.api.types.is_numeric_dtype(df[x]):
            kwargs["by"] = x
        plot = df.hvplot.violin(**kwargs)

    elif kind == "kde":
        kwargs = {**base, "y": y}
        if color and color in df.columns:
            kwargs["by"] = color
        plot = df.hvplot.kde(**kwargs)

    elif kind == "heatmap":
        kwargs = {**base, "x": x, "y": y}
        if color and color in df.columns:
            kwargs["C"] = color
        plot = df.hvplot.heatmap(**kwargs)

    elif kind == "hexbin":
        kwargs = {**base, "x": x, "y": y}
        plot = df.hvplot.hexbin(**kwargs)

    elif kind == "points":
        kwargs = {**base, "x": x, "y": y, "geo": True, "tiles": "CartoDark"}
        kwargs["height"] = 400
        if color and color in df.columns:
            kwargs["c"] = color
        try:
            plot = df.hvplot.points(**kwargs)
        except Exception:
            # Fallback without geo if geoviews not installed
            kwargs.pop("geo", None)
            kwargs.pop("tiles", None)
            plot = df.hvplot.scatter(**kwargs)

    else:
        raise ValueError(f"Unsupported chart type: {kind}")

    return hv.render(plot, backend="bokeh")


def _build_pie_chart(df: pd.DataFrame, names_col: str, values_col: str,
                     title: str, theme: str = "dark"):
    """Build a pie chart using Bokeh directly (hvPlot doesn't support pie)."""
    data = df.groupby(names_col)[values_col].sum().reset_index()
    data["angle"] = data[values_col] / data[values_col].sum() * 2 * math.pi

    n = len(data)
    if n <= 2:
        colors = ["#6366f1", "#f59e0b"][:n]
    else:
        colors = list(Category10[min(n, 10)][:n])
    data["color"] = colors

    source = ColumnDataSource(data)

    fig = bokeh_figure(
        title=title,
        toolbar_location=None,
        tools="hover",
        tooltips=f"@{names_col}: @{values_col}",
        x_range=(-0.5, 1.0),
        width=500,
        height=350,
    )

    fig.wedge(
        x=0, y=1, radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend_field=names_col,
        source=source,
    )

    fig.axis.visible = False
    fig.grid.grid_line_color = None

    tc = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    if fig.legend:
        fig.legend.label_text_color = tc["legend_text"]
        fig.legend.background_fill_alpha = 0
        fig.legend.border_line_alpha = 0

    return fig


def _add_click_callbacks(fig, x_col: str, y_col: str):
    """Add click event callbacks to Bokeh figure renderers."""
    for renderer in fig.renderers:
        if hasattr(renderer, "data_source"):
            source = renderer.data_source
            cols = list(source.data.keys())
            x_key = x_col if x_col in source.data else (cols[0] if cols else "x")
            y_key = y_col if y_col in source.data else (cols[1] if len(cols) > 1 else "y")

            callback = CustomJS(
                args=dict(source=source),
                code=(
                    "try {"
                    "const idx = source.selected.indices;"
                    "if (!idx.length) return;"
                    "const i = idx[0];"
                    "const xd = source.data['" + x_key + "'];"
                    "const yd = source.data['" + y_key + "'];"
                    "if (!xd || !yd) return;"
                    "window.dispatchEvent(new CustomEvent('bokeh-tap', {"
                    "  detail: { index: i, xValue: String(xd[i]), yValue: Number(yd[i]) }"
                    "}));"
                    "} catch(e) { console.warn('Click callback error:', e); }"
                ),
            )
            source.selected.js_on_change("indices", callback)
            break


# ---------------------------------------------------------------------------
# Widget config builder (for dashboard filters)
# ---------------------------------------------------------------------------
def _build_widget_config(df: pd.DataFrame) -> list[dict]:
    """Build widget configuration for dashboard filter sidebar."""
    widgets = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_min = float(df[col].min())
            col_max = float(df[col].max())
            rng = col_max - col_min
            if rng == 0:
                step = 1.0
            elif pd.api.types.is_integer_dtype(df[col]):
                step = max(1, int(rng / 100))
            else:
                step = round(rng / 100, 4)
            widgets.append({
                "column": col,
                "type": "range",
                "min": col_min,
                "max": col_max,
                "step": step,
            })
        elif pd.api.types.is_string_dtype(df[col]) or df[col].dtype.name == "category":
            unique_vals = sorted(df[col].dropna().unique().tolist())
            if len(unique_vals) <= 50:
                widgets.append({
                    "column": col,
                    "type": "select",
                    "options": unique_vals,
                })
    return widgets


# ---------------------------------------------------------------------------
# Annotation helper
# ---------------------------------------------------------------------------
def _add_annotation_to_figure(fig, annotation_type: str, config: dict):
    """Add a Bokeh annotation to a figure."""
    if annotation_type == "hline":
        span = Span(
            location=config.get("y_value", 0),
            dimension="width",
            line_color=config.get("color", "#ef4444"),
            line_dash=config.get("dash", "dashed"),
            line_width=2,
        )
        fig.add_layout(span)
        if config.get("label"):
            label = Label(
                x=10, y=config["y_value"],
                text=config["label"],
                text_color=config.get("color", "#ef4444"),
                text_font_size="11px",
                x_units="screen",
            )
            fig.add_layout(label)

    elif annotation_type == "vline":
        span = Span(
            location=config.get("x_value", 0),
            dimension="height",
            line_color=config.get("color", "#6366f1"),
            line_dash=config.get("dash", "dotted"),
            line_width=2,
        )
        fig.add_layout(span)

    elif annotation_type == "text":
        label = Label(
            x=config.get("x", 0),
            y=config.get("y", 0),
            text=config.get("text", ""),
            text_color=config.get("color", "#e0e0e0"),
            text_font_size=config.get("font_size", "12px"),
        )
        fig.add_layout(label)

    elif annotation_type == "band":
        box = BoxAnnotation(
            bottom=config.get("lower", 0),
            top=config.get("upper", 100),
            fill_color=config.get("color", "#4ade80"),
            fill_alpha=config.get("alpha", 0.1),
        )
        fig.add_layout(box)

    elif annotation_type == "arrow":
        arrow = Arrow(
            end=NormalHead(fill_color=config.get("color", "#f59e0b"), size=10),
            x_start=config.get("x_start", 0),
            y_start=config.get("y_start", 0),
            x_end=config.get("x_end", 1),
            y_end=config.get("y_end", 1),
            line_color=config.get("color", "#f59e0b"),
            line_width=2,
        )
        fig.add_layout(arrow)


def _rebuild_figure_with_annotations(viz: dict, target_id: str = "chart-container"):
    """Rebuild a Bokeh figure from viz store data, including all stored annotations."""
    df = pd.DataFrame(viz["data"])
    theme = viz.get("theme", "dark")

    if viz["kind"] == "pie":
        fig = _build_pie_chart(df, viz["x"], viz["y"], viz["title"], theme)
    else:
        fig = _build_hvplot_chart(viz["kind"], df, viz["x"], viz["y"], viz["title"], viz.get("color"))
        _apply_theme(fig, theme)

    fig.add_tools(TapTool())
    _add_click_callbacks(fig, viz["x"], viz["y"])

    for ann in viz.get("annotations", []):
        _add_annotation_to_figure(fig, ann["type"], ann["config"])

    return json_item(fig, target_id)


# ---------------------------------------------------------------------------
# Panel server helpers
# ---------------------------------------------------------------------------
def _find_free_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _generate_panel_code(viz: dict) -> str:
    """Generate a rich standalone Panel app with FloatPanel inspector, Tabulator, and indicators."""
    data_json = json.dumps(viz["data"])
    kind = viz["kind"]
    x_col = viz["x"]
    y_col = viz["y"]
    title = viz["title"]
    color = viz.get("color")

    return textwrap.dedent(f'''\
        import json
        import pandas as pd
        import panel as pn
        import hvplot.pandas  # noqa: F401

        pn.extension("floatpanel", "tabulator", sizing_mode="stretch_width")

        data = json.loads("""{data_json}""")
        df = pd.DataFrame(data)

        CHART_TYPES = ["bar", "line", "scatter", "area", "histogram",
                       "box", "violin", "kde", "step"]

        categorical_cols = [c for c in df.columns if df[c].dtype == "object"]
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        all_cols = list(df.columns)

        # --- Filter widgets ---
        filter_widgets = {{}}
        for col in categorical_cols:
            opts = ["All"] + sorted(df[col].unique().tolist())
            filter_widgets[col] = pn.widgets.Select(name=col, options=opts, value="All")
        for col in numeric_cols:
            filter_widgets[col] = pn.widgets.RangeSlider(
                name=col, start=float(df[col].min()), end=float(df[col].max()),
                value=(float(df[col].min()), float(df[col].max())),
            )

        # --- Inspector widgets (FloatPanel) ---
        chart_type_w = pn.widgets.Select(name="Chart Type", options=CHART_TYPES, value="{kind}")
        x_w = pn.widgets.Select(name="X Axis", options=all_cols, value="{x_col}")
        y_w = pn.widgets.Select(name="Y Axis", options=numeric_cols, value="{y_col}")
        color_w = pn.widgets.Select(
            name="Color By", options=["None"] + categorical_cols,
            value={repr(color)} if {repr(color)} else "None",
        )
        title_w = pn.widgets.TextInput(name="Title", value="{title}")

        def get_filtered_df(**kwargs):
            filtered = df.copy()
            for col, val in kwargs.items():
                if col in categorical_cols and val != "All":
                    filtered = filtered[filtered[col] == val]
                elif col in numeric_cols:
                    filtered = filtered[(filtered[col] >= val[0]) & (filtered[col] <= val[1])]
            return filtered

        @pn.depends(chart_type_w, x_w, y_w, color_w, title_w,
                    **{{k: v for k, v in filter_widgets.items()}})
        def main_chart(ct, x, y, clr, ttl, **kwargs):
            filtered = get_filtered_df(**kwargs)
            if filtered.empty:
                return pn.pane.Markdown("**No data matches current filters**")
            c = clr if clr != "None" else None
            base = {{"title": ttl, "responsive": True, "height": 450}}
            simple = {{"bar", "line", "scatter", "area", "step"}}
            try:
                if ct in simple:
                    pk = {{**base, "x": x, "y": y}}
                    if c:
                        pk["by"] = c
                    return getattr(filtered.hvplot, ct)(**pk)
                elif ct == "histogram":
                    pk = {{**base, "y": y}}
                    if c:
                        pk["by"] = c
                    return filtered.hvplot.hist(**pk)
                elif ct in ("box", "violin"):
                    pk = {{**base, "y": y}}
                    if x and filtered[x].dtype == "object":
                        pk["by"] = x
                    return getattr(filtered.hvplot, ct)(**pk)
                elif ct == "kde":
                    pk = {{**base, "y": y}}
                    if c:
                        pk["by"] = c
                    return filtered.hvplot.kde(**pk)
                else:
                    return filtered.hvplot.bar(**{{**base, "x": x, "y": y}})
            except Exception as e:
                return pn.pane.Markdown(f"**Chart error:** {{e}}")

        @pn.depends(**{{k: v for k, v in filter_widgets.items()}})
        def indicators(**kwargs):
            filtered = get_filtered_df(**kwargs)
            if filtered.empty or "{y_col}" not in filtered.columns:
                return pn.pane.Markdown("No data")
            s = filtered["{y_col}"]
            return pn.Row(
                pn.indicators.Number(name="Count", value=int(s.count()), format="{{value}}", default_color="#818cf8"),
                pn.indicators.Number(name="Mean", value=round(float(s.mean()), 1), format="{{value:,.1f}}", default_color="#4ade80"),
                pn.indicators.Number(name="Min", value=round(float(s.min()), 1), format="{{value:,.1f}}", default_color="#f59e0b"),
                pn.indicators.Number(name="Max", value=round(float(s.max()), 1), format="{{value:,.1f}}", default_color="#ef4444"),
            )

        @pn.depends(**{{k: v for k, v in filter_widgets.items()}})
        def data_table(**kwargs):
            filtered = get_filtered_df(**kwargs)
            return pn.widgets.Tabulator(
                filtered, height=300, show_index=False,
                theme="midnight", page_size=25,
            )

        inspector = pn.layout.FloatPanel(
            pn.Column(chart_type_w, x_w, y_w, color_w, title_w),
            name="Chart Inspector",
            contained=False,
            position="right-top",
            margin=20,
        )

        sidebar = pn.Column("## Filters", *filter_widgets.values(), width=250)
        main_area = pn.Column(indicators, main_chart, data_table)

        pn.template.FastListTemplate(
            title="{title}",
            sidebar=[sidebar],
            main=[main_area, inspector],
            theme="dark",
        ).servable()
    ''')


def _cleanup_panel_servers():
    """Stop all running Panel servers on exit."""
    for info in _panel_servers.values():
        try:
            info["process"].terminate()
        except Exception:
            pass


atexit.register(_cleanup_panel_servers)


# ===========================================================================
# TOOLS
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 1 - Create visualization
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def create_viz(
    kind: str,
    title: str,
    data: dict[str, list],
    x: str,
    y: str,
    color: str | None = None,
) -> str:
    """Create an interactive visualization that renders in the conversation.

    Args:
        kind: Chart type - one of: bar, line, scatter, area, pie, histogram, box, violin, kde, step, heatmap, hexbin, points.
              box/violin: x is grouping column (categorical), y is numeric.
              kde: only y needed (density estimate of that column).
              heatmap: x and y are categorical axes, color is the value column.
              hexbin: both x and y must be numeric.
              points: geographic scatter map - x is longitude, y is latitude.
        title: Chart title
        data: Dictionary of column_name -> list of values (e.g. {"region": ["East", "West"], "sales": [100, 200]})
        x: Column name for x-axis (or grouping column for box/violin, longitude for points)
        y: Column name for y-axis (or numeric column for box/violin/kde, latitude for points)
        color: Optional column for color grouping (or value column C for heatmap)
    """
    try:
        df = pd.DataFrame(data)
        spec = _build_bokeh_figure(kind, df, x, y, title, color)

        viz_id = str(uuid.uuid4())[:8]
        _viz_store[viz_id] = {
            "id": viz_id,
            "kind": kind,
            "title": title,
            "data": data,
            "x": x,
            "y": y,
            "color": color,
            "theme": "dark",
            "annotations": [],
        }

        return json.dumps({"action": "create", "id": viz_id, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 2 - Update existing visualization
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def update_viz(
    viz_id: str,
    kind: str | None = None,
    title: str | None = None,
    data: dict[str, list] | None = None,
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
) -> str:
    """Update an existing visualization. Only provide the fields you want to change.

    Args:
        viz_id: ID of the visualization to update (returned by create_viz)
        kind: New chart type (bar, line, scatter, area, pie, histogram, box, violin, kde, step, heatmap, hexbin, points)
        title: New chart title
        data: New data dictionary
        x: New x-axis column
        y: New y-axis column
        color: New color grouping column (use empty string to remove)
    """
    try:
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        if kind is not None:
            viz["kind"] = kind
        if title is not None:
            viz["title"] = title
        if data is not None:
            viz["data"] = data
        if x is not None:
            viz["x"] = x
        if y is not None:
            viz["y"] = y
        if color is not None:
            viz["color"] = color if color != "" else None

        spec = _rebuild_figure_with_annotations(viz)

        return json.dumps({"action": "update", "id": viz_id, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 3 - Load data from file
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def load_data(
    file_path: str,
    kind: str,
    x: str,
    y: str,
    title: str = "Data Visualization",
    color: str | None = None,
) -> str:
    """Load data from a CSV or Parquet file and create a visualization.

    Args:
        file_path: Path to a .csv or .parquet file
        kind: Chart type (bar, line, scatter, area, pie, histogram)
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column for color grouping
    """
    try:
        if not os.path.exists(file_path):
            return json.dumps({"action": "error", "message": f"File not found: {file_path}"})

        if file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        elif file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            return json.dumps({"action": "error", "message": "Unsupported file format. Use .csv or .parquet"})

        spec = _build_bokeh_figure(kind, df, x, y, title, color)

        viz_id = str(uuid.uuid4())[:8]
        _viz_store[viz_id] = {
            "id": viz_id,
            "kind": kind,
            "title": title,
            "data": df.to_dict(orient="list"),
            "x": x,
            "y": y,
            "color": color,
            "theme": "dark",
            "annotations": [],
        }

        return json.dumps({
            "action": "create",
            "id": viz_id,
            "figure": spec,
            "info": {"columns": list(df.columns), "rows": len(df), "file": file_path},
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 4 - Bidirectional: handle click events from the UI
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
def handle_click(viz_id: str, point_index: int, x_value: str, y_value: float) -> str:
    """Handle a click event from the visualization UI. Called by the app, not the LLM.

    Args:
        viz_id: ID of the visualization that was clicked
        point_index: Index of the clicked data point
        x_value: X-axis value of the clicked point
        y_value: Y-axis value of the clicked point
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
        pct_of_max = round((y_value / max_val) * 100, 1) if max_val else 0

        message = (
            f"Point: {x_value} = {y_value}\n"
            f"This is {comparison} the average ({mean_val:.1f}).\n"
            f"It represents {pct_of_max}% of the maximum value ({max_val})."
        )
    else:
        message = f"Clicked: {x_value} = {y_value}"

    return json.dumps({"action": "insight", "message": message})


# ---------------------------------------------------------------------------
# Tool 5 - List all active visualizations
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
def list_vizs() -> str:
    """List all active visualizations. Called by the app UI."""
    vizs = [{"id": v["id"], "title": v["title"], "kind": v["kind"]} for v in _viz_store.values()]
    return json.dumps({"action": "list", "visualizations": vizs})


# ---------------------------------------------------------------------------
# Tool 6 - Create dashboard (modified: now includes widget_config)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=DASHBOARD_URI))
def create_dashboard(
    title: str,
    data: dict[str, list],
    x: str,
    y: str,
    chart_kind: str = "bar",
    color: str | None = None,
) -> str:
    """Create an interactive dashboard with chart, data table, summary statistics, and filter widgets.

    Args:
        title: Dashboard title
        data: Dictionary of column_name -> list of values
        x: Column for x-axis
        y: Column for y-axis (must be numeric)
        chart_kind: Chart type (bar, line, scatter, area)
        color: Optional column for color grouping
    """
    try:
        df = pd.DataFrame(data)
        spec = _build_bokeh_figure(chart_kind, df, x, y, title, color, target_id="chart")

        y_series = pd.to_numeric(df[y], errors="coerce").dropna()
        stats = {
            "count": int(y_series.count()),
            "mean": round(float(y_series.mean()), 2),
            "median": round(float(y_series.median()), 2),
            "min": round(float(y_series.min()), 2),
            "max": round(float(y_series.max()), 2),
            "std": round(float(y_series.std()), 2),
            "sum": round(float(y_series.sum()), 2),
        }

        widget_config = _build_widget_config(df)

        viz_id = str(uuid.uuid4())[:8]
        _viz_store[viz_id] = {
            "id": viz_id,
            "kind": chart_kind,
            "title": title,
            "data": data,
            "x": x,
            "y": y,
            "color": color,
            "theme": "dark",
            "is_dashboard": True,
        }

        return json.dumps({
            "action": "dashboard",
            "id": viz_id,
            "title": title,
            "figure": spec,
            "table": {"columns": list(df.columns), "rows": df.head(50).values.tolist()},
            "stats": stats,
            "y_column": y,
            "widget_config": widget_config,
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 7 - Streaming chart
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=STREAM_URI))
def stream_data(
    title: str = "Live Data Stream",
    metric_name: str = "value",
    initial_value: float = 100.0,
    volatility: float = 5.0,
    points: int = 30,
    interval_ms: int = 1000,
) -> str:
    """Create a live-updating streaming chart that simulates real-time data.

    Args:
        title: Chart title
        metric_name: Name of the metric being streamed
        initial_value: Starting value for the stream
        volatility: How much the value fluctuates (standard deviation)
        points: Number of visible data points on chart
        interval_ms: Update interval in milliseconds
    """
    viz_id = str(uuid.uuid4())[:8]
    _viz_store[viz_id] = {
        "id": viz_id,
        "kind": "stream",
        "title": title,
    }

    return json.dumps({
        "action": "stream",
        "id": viz_id,
        "title": title,
        "config": {
            "metric_name": metric_name,
            "initial_value": initial_value,
            "volatility": volatility,
            "points": points,
            "interval_ms": interval_ms,
        },
    })


# ---------------------------------------------------------------------------
# Tool 8 - Apply filter (NEW - app only, for dashboard widgets)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=DASHBOARD_URI, visibility=["app"]))
def apply_filter(
    viz_id: str,
    filters: dict[str, str | float | list],
) -> str:
    """Apply filters to a dashboard visualization. Called by the app UI widgets.

    Args:
        viz_id: The visualization ID to filter
        filters: Dictionary of column_name -> filter value. Use string for categorical,
                 [min, max] list for numeric range, or "__all__" to clear a filter.
    """
    try:
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        df = pd.DataFrame(viz["data"])

        for col, value in filters.items():
            if col not in df.columns:
                continue
            if value == "__all__":
                continue
            if isinstance(value, str):
                df = df[df[col] == value]
            elif isinstance(value, list) and len(value) == 2:
                df = df[(df[col] >= value[0]) & (df[col] <= value[1])]

        if df.empty:
            return json.dumps({
                "action": "filter_result", "id": viz_id, "empty": True,
                "message": "No data matches the current filters",
            })

        theme = viz.get("theme", "dark")
        spec = _build_bokeh_figure(viz["kind"], df, viz["x"], viz["y"],
                                   viz["title"], viz.get("color"), target_id="chart", theme=theme)

        y_series = pd.to_numeric(df[viz["y"]], errors="coerce").dropna()
        stats = {
            "count": int(y_series.count()),
            "mean": round(float(y_series.mean()), 2),
            "median": round(float(y_series.median()), 2),
            "min": round(float(y_series.min()), 2),
            "max": round(float(y_series.max()), 2),
            "std": round(float(y_series.std()), 2) if len(y_series) > 1 else 0.0,
            "sum": round(float(y_series.sum()), 2),
        }

        return json.dumps({
            "action": "filter_result",
            "id": viz_id,
            "empty": False,
            "figure": spec,
            "table": {"columns": list(df.columns), "rows": df.head(50).values.tolist()},
            "stats": stats,
            "filtered_rows": len(df),
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 9 - Set theme (NEW - app only)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
def set_theme(viz_id: str, theme: str = "dark") -> str:
    """Switch visualization theme between light and dark. Called by the app UI.

    Args:
        viz_id: ID of the visualization to re-theme
        theme: "dark" or "light"
    """
    try:
        if theme not in ("dark", "light"):
            return json.dumps({"action": "error", "message": "Theme must be 'dark' or 'light'"})
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        viz["theme"] = theme

        if viz["kind"] == "stream":
            return json.dumps({"action": "theme_change", "id": viz_id, "theme": theme})

        target_id = "chart" if viz.get("is_dashboard") else "chart-container"
        spec = _rebuild_figure_with_annotations(viz, target_id)

        return json.dumps({"action": "theme_change", "id": viz_id, "theme": theme, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 10 - Multi-chart dashboard (NEW)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=MULTI_URI))
def create_multi_chart(
    title: str,
    data: dict[str, list],
    charts: list[dict],
) -> str:
    """Create a multi-chart dashboard with 2-4 charts showing different views of the same data.

    Args:
        title: Dashboard title
        data: Shared dataset as dictionary of column_name -> list of values
        charts: List of 1-4 chart configs, each with keys: kind, x, y, title (optional), color (optional)
    """
    try:
        if len(charts) < 1 or len(charts) > 4:
            return json.dumps({"action": "error", "message": "Provide 1-4 chart configurations"})

        df = pd.DataFrame(data)
        viz_id = str(uuid.uuid4())[:8]
        figures = []

        for i, chart_cfg in enumerate(charts):
            kind = chart_cfg.get("kind", "bar")
            x = chart_cfg.get("x")
            y = chart_cfg.get("y")
            chart_title = chart_cfg.get("title", f"Chart {i + 1}")
            color = chart_cfg.get("color")
            target_id = f"chart-{i}"

            try:
                spec = _build_bokeh_figure(kind, df, x, y, chart_title, color, target_id)
                figures.append({"index": i, "target_id": target_id, "figure": spec, "title": chart_title})
            except Exception as e:
                figures.append({"index": i, "target_id": target_id, "error": str(e), "title": chart_title})

        _viz_store[viz_id] = {
            "id": viz_id,
            "kind": "multi",
            "title": title,
            "data": data,
            "charts": charts,
            "theme": "dark",
        }

        return json.dumps({
            "action": "multi_chart",
            "id": viz_id,
            "title": title,
            "figures": figures,
            "chart_count": len(figures),
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 11 - Chart annotations (NEW)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def annotate_viz(
    viz_id: str,
    annotation_type: str,
    config: dict,
) -> str:
    """Add annotations to an existing visualization (text labels, reference lines, bands, arrows).

    Args:
        viz_id: ID of the visualization to annotate
        annotation_type: One of: text, hline, vline, band, arrow
        config: Annotation config. For text: {x, y, text, color?, font_size?}.
                For hline: {y_value, color?, dash?, label?}. For vline: {x_value, color?, dash?}.
                For band: {lower, upper, color?, alpha?}. For arrow: {x_start, y_start, x_end, y_end, color?}.
    """
    try:
        if annotation_type not in ANNOTATION_TYPES:
            return json.dumps({"action": "error",
                               "message": f"Unsupported annotation type. Supported: {ANNOTATION_TYPES}"})
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        if viz["kind"] in ("stream", "multi"):
            return json.dumps({"action": "error",
                               "message": "Annotations not supported for stream/multi charts"})

        if "annotations" not in viz:
            viz["annotations"] = []
        viz["annotations"].append({"type": annotation_type, "config": config})

        spec = _rebuild_figure_with_annotations(viz)

        return json.dumps({"action": "update", "id": viz_id, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 12 - Export data (NEW)
# ---------------------------------------------------------------------------
@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def export_data(viz_id: str, format: str = "csv") -> str:
    """Export visualization data as CSV or JSON.

    Args:
        viz_id: ID of the visualization to export
        format: Export format - "csv" or "json"
    """
    try:
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        if "data" not in viz:
            return json.dumps({"action": "error", "message": "No data available for export"})

        df = pd.DataFrame(viz["data"])

        if format == "csv":
            data_str = df.to_csv(index=False)
        elif format == "json":
            data_str = df.to_json(orient="records", indent=2)
        else:
            return json.dumps({"action": "error", "message": "Format must be 'csv' or 'json'"})

        safe_title = viz["title"].replace(" ", "_").lower()
        return json.dumps({
            "action": "export",
            "id": viz_id,
            "format": format,
            "data": data_str,
            "filename": f"{safe_title}.{format}",
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 13 - Launch Panel server (NEW)
# ---------------------------------------------------------------------------
@mcp.tool()
def launch_panel(viz_id: str) -> str:
    """Launch a full interactive Panel dashboard in the browser with live widgets and filtering.

    Args:
        viz_id: ID of a visualization to open as a Panel app
    """
    try:
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        if viz["kind"] in ("stream",):
            return json.dumps({"action": "error", "message": "Stream charts cannot be launched as Panel apps"})

        if viz_id in _panel_servers:
            url = _panel_servers[viz_id]["url"]
            return json.dumps({"action": "panel_launched", "id": viz_id, "url": url,
                               "message": f"Panel app already running at {url}"})

        port = _find_free_port()
        code = _generate_panel_code(viz)

        tmp_dir = tempfile.mkdtemp(prefix="panel_viz_mcp_")
        script_path = os.path.join(tmp_dir, "app.py")
        with open(script_path, "w") as f:
            f.write(code)

        process = subprocess.Popen(
            [sys.executable, "-m", "panel", "serve", script_path,
             "--port", str(port), "--show", "--allow-websocket-origin", "*"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        url = f"http://localhost:{port}/app"
        _panel_servers[viz_id] = {"process": process, "port": port, "url": url, "tmp_dir": tmp_dir}

        try:
            webbrowser.open(url)
        except Exception:
            pass  # Headless server fallback - user gets URL in response

        return json.dumps({
            "action": "panel_launched",
            "id": viz_id,
            "url": url,
            "port": port,
            "message": f"Panel app launched at {url}. Opening in browser.",
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": f"Failed to launch Panel: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 14 - Stop Panel server (NEW)
# ---------------------------------------------------------------------------
@mcp.tool()
def stop_panel(viz_id: str) -> str:
    """Stop a running Panel server.

    Args:
        viz_id: ID of the visualization whose Panel server to stop
    """
    if viz_id not in _panel_servers:
        return json.dumps({"action": "error", "message": f"No Panel server running for {viz_id}"})

    info = _panel_servers[viz_id]
    try:
        info["process"].terminate()
        info["process"].wait(timeout=5)
    except subprocess.TimeoutExpired:
        info["process"].kill()
    except Exception:
        pass

    tmp_dir = info.get("tmp_dir")
    if tmp_dir and os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)

    del _panel_servers[viz_id]

    return json.dumps({"action": "panel_stopped", "id": viz_id, "message": "Panel server stopped"})


# ===========================================================================
# HTML RESOURCES
# ===========================================================================

# ---------------------------------------------------------------------------
# Resource 1 - Visualization viewer (viz.html)
# ---------------------------------------------------------------------------
@mcp.resource(
    VIEW_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def viz_view() -> str:
    """Interactive visualization viewer powered by hvPlot + BokehJS."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Panel Viz MCP</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: transparent; color: var(--text-primary); padding: 8px;\n"
        "    }\n"
        "    #chart-container { width: 100%; min-height: 320px; border-radius: 8px; overflow: hidden; }\n"
        "    #status { font-size: 12px; color: var(--text-muted); padding: 4px 0; text-align: center; }\n"
        "    #insight-bar {\n"
        "      display: none; background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3);\n"
        "      border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 13px;\n"
        "      color: #93c5fd; white-space: pre-line;\n"
        "    }\n"
        "    #viz-id { font-size: 11px; color: var(--text-muted); text-align: right; padding: 2px 0; }\n"
        "    .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text-muted); }\n"
        "    .error-msg { color: var(--error); padding: 20px; text-align: center; }\n"
        "    .toolbar { display: flex; gap: 6px; justify-content: flex-end; padding: 4px 0; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .export-modal {\n"
        "      position: fixed; top: 0; left: 0; width: 100%; height: 100%;\n"
        "      background: rgba(0,0,0,0.7); z-index: 1000; display: flex;\n"
        "      align-items: center; justify-content: center;\n"
        "    }\n"
        "    .export-modal-inner {\n"
        "      background: var(--btn-bg); border-radius: 8px; padding: 16px;\n"
        "      width: 80%; max-height: 80%; overflow: auto; border: 1px solid var(--border);\n"
        "    }\n"
        "    .export-textarea {\n"
        "      width: 100%; height: 300px; background: var(--input-bg); color: var(--text-primary);\n"
        "      border: 1px solid var(--border); border-radius: 4px; padding: 8px;\n"
        "      font-family: monospace; font-size: 11px; resize: vertical;\n"
        "    }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="toolbar" id="toolbar" style="display:none;">\n'
        '    <button class="toolbar-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '    <button class="toolbar-btn" onclick="exportPNG()">Save PNG</button>\n'
        '    <button class="toolbar-btn" onclick="exportCSV()">Export CSV</button>\n'
        '    <button class="toolbar-btn" id="panel-btn" onclick="openInPanel()">Open in Panel</button>\n'
        "  </div>\n"
        '  <div id="chart-container"><div class="loading">Waiting for visualization data...</div></div>\n'
        '  <div id="insight-bar"></div>\n'
        '  <div id="viz-id"></div>\n'
        '  <div id="status">panel-viz-mcp ready (HoloViz + BokehJS)</div>\n'
        "\n"
        '  <script type="module">\n'
        '    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";\n'
        '    const app = new App({ name: "Panel Viz MCP", version: "0.2.0" });\n'
        "    let currentVizId = null;\n"
        '    let currentTheme = "dark";\n'
        "\n"
        "    window.toggleTheme = async () => {\n"
        '      currentTheme = currentTheme === "dark" ? "light" : "dark";\n'
        '      document.body.className = "theme-" + currentTheme;\n'
        '      document.querySelector(".toolbar-btn").textContent = currentTheme === "dark" ? "Light Mode" : "Dark Mode";\n'
        "      if (currentVizId) {\n"
        "        try {\n"
        "          const response = await app.callServerTool({\n"
        '            name: "set_theme",\n'
        "            arguments: { viz_id: currentVizId, theme: currentTheme },\n"
        "          });\n"
        '          const t = response?.content?.find(c => c.type === "text");\n'
        "          if (t) {\n"
        "            const r = JSON.parse(t.text);\n"
        '            if (r.action === "theme_change" && r.figure) {\n'
        '              const container = document.getElementById("chart-container");\n'
        '              container.innerHTML = "";\n'
        "              await Bokeh.embed.embed_item(r.figure);\n"
        "            }\n"
        "          }\n"
        "        } catch (err) { console.log('Theme switch:', err); }\n"
        "      }\n"
        "    };\n"
        "\n"
        "    window.exportPNG = () => {\n"
        "      const canvas = document.querySelector('#chart-container canvas');\n"
        "      if (!canvas) { alert('No chart canvas found'); return; }\n"
        '      const link = document.createElement("a");\n'
        '      link.download = "chart.png";\n'
        '      link.href = canvas.toDataURL("image/png");\n'
        "      link.click();\n"
        "    };\n"
        "\n"
        "    window.exportCSV = async () => {\n"
        "      if (!currentVizId) return;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "export_data",\n'
        '          arguments: { viz_id: currentVizId, format: "csv" },\n'
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const result = JSON.parse(t.text);\n"
        '          if (result.action === "export") {\n'
        "            try {\n"
        '              const blob = new Blob([result.data], { type: "text/csv" });\n'
        "              const url = URL.createObjectURL(blob);\n"
        '              const link = document.createElement("a");\n'
        "              link.href = url; link.download = result.filename; link.click();\n"
        "              URL.revokeObjectURL(url);\n"
        "            } catch (dlErr) {\n"
        '              const modal = document.createElement("div");\n'
        '              modal.className = "export-modal";\n'
        "              modal.innerHTML = '<div class=\"export-modal-inner\">' +\n"
        "                '<div style=\"display:flex;justify-content:space-between;margin-bottom:8px;\">' +\n"
        "                '<span>Export Data (CSV)</span>' +\n"
        "                '<button onclick=\"this.closest(\\'.export-modal\\').remove()\" class=\"toolbar-btn\">Close</button></div>' +\n"
        "                '<textarea class=\"export-textarea\">' + result.data.replace(/</g, '&lt;') + '</textarea></div>';\n"
        "              document.body.appendChild(modal);\n"
        "            }\n"
        "          }\n"
        "        }\n"
        "      } catch (err) { console.error('Export error:', err); }\n"
        "    };\n"
        "\n"
        "    window.openInPanel = async () => {\n"
        "      if (!currentVizId) return;\n"
        '      const btn = document.getElementById("panel-btn");\n'
        '      btn.textContent = "Launching...";\n'
        "      btn.disabled = true;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "launch_panel",\n'
        "          arguments: { viz_id: currentVizId },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "panel_launched") {\n'
        '            document.getElementById("status").textContent = "Panel app: " + r.url;\n'
        "          }\n"
        "        }\n"
        "      } catch (err) { console.log('Panel launch:', err); }\n"
        '      btn.textContent = "Open in Panel";\n'
        "      btn.disabled = false;\n"
        "    };\n"
        "\n"
        "    window.addEventListener('bokeh-tap', async (e) => {\n"
        "      if (!currentVizId) return;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "handle_click",\n'
        "          arguments: {\n"
        "            viz_id: currentVizId,\n"
        "            point_index: e.detail.index,\n"
        "            x_value: e.detail.xValue,\n"
        "            y_value: e.detail.yValue,\n"
        "          },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "insight") {\n'
        '            const bar = document.getElementById("insight-bar");\n'
        "            bar.textContent = r.message;\n"
        '            bar.style.display = "block";\n'
        "          }\n"
        "        }\n"
        "      } catch (err) { console.log('Click handler:', err); }\n"
        "    });\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const textContent = content?.find(c => c.type === "text");\n'
        "      if (!textContent) return;\n"
        "      let result;\n"
        "      try { result = JSON.parse(textContent.text); } catch { return; }\n"
        "\n"
        '      if (result.action === "create" || result.action === "update") {\n'
        "        currentVizId = result.id;\n"
        '        document.getElementById("toolbar").style.display = "flex";\n'
        '        const container = document.getElementById("chart-container");\n'
        '        container.innerHTML = "";\n'
        "        try {\n"
        "          await Bokeh.embed.embed_item(result.figure);\n"
        '          document.getElementById("status").textContent =\n'
        '            result.action === "create" ? "Visualization created" : "Visualization updated";\n'
        "          if (result.info) {\n"
        '            document.getElementById("status").textContent +=\n'
        '              " | " + result.info.rows + " rows from " + result.info.file;\n'
        "          }\n"
        "        } catch (err) {\n"
        '          container.innerHTML = \'<div class="error-msg">Chart render error: \' + err.message + \'</div>\';\n'
        "        }\n"
        '        document.getElementById("viz-id").textContent = "ID: " + result.id;\n'
        '        document.getElementById("insight-bar").style.display = "none";\n'
        "      }\n"
        "\n"
        '      if (result.action === "theme_change" && result.figure) {\n'
        '        const container = document.getElementById("chart-container");\n'
        '        container.innerHTML = "";\n'
        "        try { await Bokeh.embed.embed_item(result.figure); } catch (err) {\n"
        '          container.innerHTML = \'<div class="error-msg">Theme error: \' + err.message + \'</div>\';\n'
        "        }\n"
        "      }\n"
        "\n"
        '      if (result.action === "insight") {\n'
        '        const bar = document.getElementById("insight-bar");\n'
        "        bar.textContent = result.message;\n"
        '        bar.style.display = "block";\n'
        "      }\n"
        "\n"
        '      if (result.action === "export") {\n'
        "        try {\n"
        '          const blob = new Blob([result.data], { type: result.format === "csv" ? "text/csv" : "application/json" });\n'
        "          const url = URL.createObjectURL(blob);\n"
        '          const link = document.createElement("a");\n'
        "          link.href = url;\n"
        "          link.download = result.filename;\n"
        "          link.click();\n"
        "          URL.revokeObjectURL(url);\n"
        "        } catch (err) {\n"
        '          const modal = document.createElement("div");\n'
        '          modal.className = "export-modal";\n'
        "          modal.innerHTML = '<div class=\"export-modal-inner\">' +\n"
        "            '<div style=\"display:flex;justify-content:space-between;margin-bottom:8px;\">' +\n"
        "            '<span>Export Data (' + result.format.toUpperCase() + ')</span>' +\n"
        "            '<button onclick=\"this.closest(\\'.export-modal\\').remove()\" class=\"toolbar-btn\">Close</button></div>' +\n"
        "            '<textarea class=\"export-textarea\">' + result.data.replace(/</g, '&lt;') + '</textarea></div>';\n"
        "          document.body.appendChild(modal);\n"
        "        }\n"
        "      }\n"
        "\n"
        '      if (result.action === "error") {\n'
        '        document.getElementById("chart-container").innerHTML =\n'
        '          \'<div class="error-msg">\' + result.message + \'</div>\';\n'
        '        document.getElementById("status").textContent = "Error";\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        '    document.getElementById("status").textContent = "Connected - HoloViz + BokehJS ready";\n'
        "  </script>\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Resource 2 - Dashboard (dashboard.html) - with filter sidebar
# ---------------------------------------------------------------------------
@mcp.resource(
    DASHBOARD_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def dashboard_view() -> str:
    """Interactive dashboard with chart, table, statistics, and filter widgets."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Panel Dashboard</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: transparent; color: var(--text-primary); padding: 12px;\n"
        "    }\n"
        "    .dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }\n"
        "    .dashboard-title { font-size: 18px; font-weight: 600; }\n"
        "    .dash-toolbar { display: flex; gap: 6px; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .dashboard-layout { display: flex; gap: 12px; }\n"
        "    .dashboard-main { flex: 1; min-width: 0; }\n"
        "    .filter-sidebar {\n"
        "      width: 220px; flex-shrink: 0;\n"
        "      background: var(--bg-card); border: 1px solid var(--border);\n"
        "      border-radius: 8px; padding: 12px;\n"
        "      max-height: 600px; overflow-y: auto;\n"
        "    }\n"
        "    .filter-title {\n"
        "      font-size: 12px; color: var(--text-secondary); text-transform: uppercase;\n"
        "      letter-spacing: 0.5px; margin-bottom: 12px; padding-bottom: 6px;\n"
        "      border-bottom: 1px solid var(--border);\n"
        "    }\n"
        "    .filter-group { margin-bottom: 12px; }\n"
        "    .filter-label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }\n"
        "    .filter-select, .filter-range {\n"
        "      width: 100%; padding: 4px 8px; border-radius: 4px;\n"
        "      border: 1px solid var(--btn-border); background: var(--input-bg); color: var(--text-primary);\n"
        "      font-size: 12px;\n"
        "    }\n"
        "    .filter-range-labels { display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); }\n"
        "    .filter-btn {\n"
        "      width: 100%; padding: 6px; border-radius: 6px; border: 1px solid var(--accent);\n"
        "      background: var(--accent-bg); color: var(--accent); cursor: pointer;\n"
        "      font-size: 12px; margin-top: 8px;\n"
        "    }\n"
        "    .filter-btn:hover { opacity: 0.8; }\n"
        "    .filter-status { font-size: 11px; color: var(--text-muted); margin-top: 8px; text-align: center; }\n"
        "    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }\n"
        "    .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }\n"
        "    .card-title { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }\n"
        "    #chart { width: 100%; min-height: 280px; }\n"
        "    .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }\n"
        "    .stat-item { text-align: center; padding: 8px; background: var(--bg-surface); border-radius: 6px; }\n"
        "    .stat-value { font-size: 20px; font-weight: 700; color: var(--stat-value); }\n"
        "    .stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }\n"
        "    .table-wrap { max-height: 200px; overflow-y: auto; }\n"
        "    table { width: 100%; border-collapse: collapse; font-size: 12px; }\n"
        "    th { position: sticky; top: 0; background: var(--table-header-bg); padding: 6px 8px; text-align: left; color: var(--text-secondary); border-bottom: 1px solid var(--border); }\n"
        "    td { padding: 5px 8px; border-bottom: 1px solid var(--border); }\n"
        "    tr:hover td { background: var(--accent-bg); }\n"
        "    #status { font-size: 11px; color: var(--text-muted); text-align: center; padding: 4px; }\n"
        "    .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text-muted); }\n"
        "    .error-msg { color: var(--error); padding: 20px; text-align: center; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="dash-header">\n'
        '    <div class="dashboard-title" id="dash-title">Loading dashboard...</div>\n'
        '    <div class="dash-toolbar">\n'
        '      <button class="toolbar-btn" id="theme-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '      <button class="toolbar-btn" id="panel-btn" onclick="openInPanel()">Open in Panel</button>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div class="dashboard-layout">\n'
        '    <div class="dashboard-main">\n'
        '      <div class="grid">\n'
        '        <div class="card" style="grid-column: 1 / -1;">\n'
        '          <div class="card-title">Chart</div>\n'
        '          <div id="chart"><div class="loading">Waiting...</div></div>\n'
        "        </div>\n"
        '        <div class="card">\n'
        '          <div class="card-title">Statistics</div>\n'
        '          <div class="stats-grid" id="stats"><div class="loading">Waiting...</div></div>\n'
        "        </div>\n"
        '        <div class="card">\n'
        '          <div class="card-title">Data Table</div>\n'
        '          <div class="table-wrap" id="table"><div class="loading">Waiting...</div></div>\n'
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        '    <div class="filter-sidebar" id="filter-sidebar">\n'
        '      <div class="filter-title">Filters</div>\n'
        '      <div class="filter-status">Waiting for data...</div>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div id="status">panel-viz-mcp dashboard ready</div>\n'
        "\n"
        '  <script type="module">\n'
        '    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";\n'
        '    const app = new App({ name: "Panel Dashboard", version: "0.2.0" });\n'
        "    let currentVizId = null;\n"
        '    let currentTheme = "dark";\n'
        "\n"
        "    window.toggleTheme = () => {\n"
        '      currentTheme = currentTheme === "dark" ? "light" : "dark";\n'
        '      document.body.className = "theme-" + currentTheme;\n'
        '      document.getElementById("theme-btn").textContent = currentTheme === "dark" ? "Light Mode" : "Dark Mode";\n'
        "    };\n"
        "\n"
        "    window.openInPanel = async () => {\n"
        "      if (!currentVizId) return;\n"
        '      const btn = document.getElementById("panel-btn");\n'
        '      btn.textContent = "Launching...";\n'
        "      btn.disabled = true;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "launch_panel",\n'
        "          arguments: { viz_id: currentVizId },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "panel_launched") {\n'
        '            document.getElementById("status").textContent = "Panel app: " + r.url;\n'
        "          }\n"
        "        }\n"
        "      } catch (err) { console.log('Panel launch:', err); }\n"
        '      btn.textContent = "Open in Panel";\n'
        "      btn.disabled = false;\n"
        "    };\n"
        "\n"
        "    function buildFilterWidgets(config) {\n"
        '      const sidebar = document.getElementById("filter-sidebar");\n'
        "      sidebar.innerHTML = '<div class=\"filter-title\">Filters</div>';\n"
        "      if (!config || config.length === 0) {\n"
        "        sidebar.innerHTML += '<div class=\"filter-status\">No filterable columns</div>';\n"
        "        return;\n"
        "      }\n"
        "      config.forEach(w => {\n"
        '        const group = document.createElement("div");\n'
        '        group.className = "filter-group";\n'
        "        group.innerHTML = '<div class=\"filter-label\">' + w.column + '</div>';\n"
        '        if (w.type === "select") {\n'
        "          let html = '<select class=\"filter-select\" data-column=\"' + w.column + '\">';\n"
        "          html += '<option value=\"__all__\">All</option>';\n"
        "          w.options.forEach(opt => { html += '<option value=\"' + opt + '\">' + opt + '</option>'; });\n"
        "          html += '</select>';\n"
        "          group.innerHTML += html;\n"
        '        } else if (w.type === "range") {\n'
        "          group.innerHTML +=\n"
        "            '<input type=\"range\" class=\"filter-range\" data-column=\"' + w.column + '\"' +\n"
        "            ' min=\"' + w.min + '\" max=\"' + w.max + '\" step=\"' + w.step + '\"' +\n"
        "            ' value=\"' + w.min + '\" data-role=\"min\">' +\n"
        "            '<input type=\"range\" class=\"filter-range\" data-column=\"' + w.column + '\"' +\n"
        "            ' min=\"' + w.min + '\" max=\"' + w.max + '\" step=\"' + w.step + '\"' +\n"
        "            ' value=\"' + w.max + '\" data-role=\"max\">' +\n"
        "            '<div class=\"filter-range-labels\">' +\n"
        "            '<span id=\"range-min-' + w.column + '\">' + w.min + '</span>' +\n"
        "            '<span id=\"range-max-' + w.column + '\">' + w.max + '</span></div>';\n"
        "        }\n"
        "        sidebar.appendChild(group);\n"
        "      });\n"
        '      const applyBtn = document.createElement("button");\n'
        '      applyBtn.className = "filter-btn";\n'
        '      applyBtn.textContent = "Apply Filters";\n'
        "      applyBtn.onclick = applyFilters;\n"
        "      sidebar.appendChild(applyBtn);\n"
        '      const resetBtn = document.createElement("button");\n'
        '      resetBtn.className = "filter-btn";\n'
        '      resetBtn.textContent = "Reset";\n'
        '      resetBtn.style.marginTop = "4px";\n'
        "      resetBtn.onclick = resetFilters;\n"
        "      sidebar.appendChild(resetBtn);\n"
        "      sidebar.innerHTML += '<div id=\"filter-status\" class=\"filter-status\"></div>';\n"
        "      sidebar.querySelectorAll('.filter-range').forEach(input => {\n"
        "        input.addEventListener('input', () => {\n"
        "          const col = input.dataset.column;\n"
        "          const role = input.dataset.role;\n"
        "          const el = document.getElementById('range-' + role + '-' + col);\n"
        "          if (el) el.textContent = input.value;\n"
        "        });\n"
        "      });\n"
        "    }\n"
        "\n"
        "    async function applyFilters() {\n"
        "      if (!currentVizId) return;\n"
        "      const filters = {};\n"
        "      document.querySelectorAll('.filter-select').forEach(sel => {\n"
        "        filters[sel.dataset.column] = sel.value;\n"
        "      });\n"
        "      const rangeByCol = {};\n"
        "      document.querySelectorAll('.filter-range').forEach(input => {\n"
        "        const col = input.dataset.column;\n"
        "        if (!rangeByCol[col]) rangeByCol[col] = {};\n"
        "        rangeByCol[col][input.dataset.role] = parseFloat(input.value);\n"
        "      });\n"
        "      for (const [col, range] of Object.entries(rangeByCol)) {\n"
        "        filters[col] = [range.min, range.max];\n"
        "      }\n"
        '      const statusEl = document.getElementById("filter-status");\n'
        '      if (statusEl) statusEl.textContent = "Filtering...";\n'
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "apply_filter",\n'
        "          arguments: { viz_id: currentVizId, filters: filters },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "filter_result") {\n'
        "            if (r.empty) {\n"
        '              document.getElementById("chart").innerHTML = \'<div class="error-msg">No data matches filters</div>\';\n'
        '              if (statusEl) statusEl.textContent = "0 rows match";\n'
        "            } else {\n"
        '              document.getElementById("chart").innerHTML = "";\n'
        "              try { await Bokeh.embed.embed_item(r.figure); } catch (embedErr) {\n"
        '                document.getElementById("chart").innerHTML = \'<div class="error-msg">\' + embedErr.message + \'</div>\';\n'
        "              }\n"
        "              renderStats(r.stats);\n"
        "              renderTable(r.table);\n"
        '              if (statusEl) statusEl.textContent = r.filtered_rows + " rows";\n'
        "            }\n"
        '          } else if (r.action === "error") {\n'
        '            document.getElementById("chart").innerHTML = \'<div class="error-msg">\' + r.message + \'</div>\';\n'
        '            if (statusEl) statusEl.textContent = "Error";\n'
        "          }\n"
        "        }\n"
        "      } catch (err) {\n"
        '        if (statusEl) statusEl.textContent = "Filter error";\n'
        "      }\n"
        "    }\n"
        "\n"
        "    function resetFilters() {\n"
        "      document.querySelectorAll('.filter-select').forEach(sel => { sel.value = '__all__'; });\n"
        "      document.querySelectorAll('.filter-range').forEach(input => {\n"
        "        input.value = input.dataset.role === 'min' ? input.min : input.max;\n"
        "        const el = document.getElementById('range-' + input.dataset.role + '-' + input.dataset.column);\n"
        "        if (el) el.textContent = input.value;\n"
        "      });\n"
        "      applyFilters();\n"
        "    }\n"
        "\n"
        "    function renderStats(stats) {\n"
        '      const statsEl = document.getElementById("stats");\n'
        "      statsEl.innerHTML = Object.entries(stats).map(([k,v]) =>\n"
        "        '<div class=\"stat-item\"><div class=\"stat-value\">' +\n"
        "        (typeof v === 'number' && v >= 1000 ? (v/1000).toFixed(1)+'k' : v) +\n"
        "        '</div><div class=\"stat-label\">' + k + '</div></div>'\n"
        "      ).join('');\n"
        "    }\n"
        "\n"
        "    function renderTable(table) {\n"
        '      const tableEl = document.getElementById("table");\n'
        '      let html = "<table><thead><tr>" +\n'
        '        table.columns.map(c => "<th>"+c+"</th>").join("") +\n'
        '        "</tr></thead><tbody>" +\n'
        '        table.rows.map(row => "<tr>" + row.map(v => "<td>"+v+"</td>").join("") + "</tr>").join("") +\n'
        '        "</tbody></table>";\n'
        "      tableEl.innerHTML = html;\n"
        "    }\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const text = content?.find(c => c.type === "text");\n'
        "      if (!text) return;\n"
        "      let r;\n"
        "      try { r = JSON.parse(text.text); } catch { return; }\n"
        "\n"
        '      if (r.action === "dashboard") {\n'
        "        currentVizId = r.id;\n"
        '        document.getElementById("dash-title").textContent = r.title;\n'
        '        document.getElementById("chart").innerHTML = "";\n'
        "        try { await Bokeh.embed.embed_item(r.figure); } catch (err) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-msg">Chart error: \' + err.message + \'</div>\';\n'
        "        }\n"
        "        renderStats(r.stats);\n"
        "        renderTable(r.table);\n"
        "        if (r.widget_config) buildFilterWidgets(r.widget_config);\n"
        '        document.getElementById("status").textContent = "Dashboard loaded | ID: " + r.id + " | " + r.table.rows.length + " rows";\n'
        "      }\n"
        "\n"
        '      if (r.action === "filter_result") {\n'
        "        if (r.empty) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-msg">No data matches filters</div>\';\n'
        '          const statusEl = document.getElementById("filter-status");\n'
        '          if (statusEl) statusEl.textContent = "0 rows match";\n'
        "        } else {\n"
        '          document.getElementById("chart").innerHTML = "";\n'
        "          try { await Bokeh.embed.embed_item(r.figure); } catch (err) {\n"
        '            document.getElementById("chart").innerHTML = \'<div class="error-msg">\' + err.message + \'</div>\';\n'
        "          }\n"
        "          renderStats(r.stats);\n"
        "          renderTable(r.table);\n"
        '          const statusEl = document.getElementById("filter-status");\n'
        '          if (statusEl) statusEl.textContent = r.filtered_rows + " rows";\n'
        "        }\n"
        "      }\n"
        "\n"
        '      if (r.action === "error") {\n'
        '        document.getElementById("chart").innerHTML = \'<div class="error-msg">\' + r.message + \'</div>\';\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Resource 3 - Streaming chart (stream.html)
# ---------------------------------------------------------------------------
@mcp.resource(
    STREAM_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def stream_view() -> str:
    """Live-updating streaming chart powered by BokehJS Plotting API."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Live Stream</title>\n"
        f'{BOKEH_SCRIPTS_WITH_API}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: transparent; color: var(--text-primary); padding: 12px;\n"
        "    }\n"
        "    .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }\n"
        "    .title { font-size: 16px; font-weight: 600; }\n"
        "    .header-right { display: flex; align-items: center; gap: 8px; }\n"
        "    .live-badge {\n"
        "      display: flex; align-items: center; gap: 6px;\n"
        "      background: rgba(239,68,68,0.15); color: #f87171;\n"
        "      padding: 3px 10px; border-radius: 12px; font-size: 12px;\n"
        "    }\n"
        "    .live-dot {\n"
        "      width: 8px; height: 8px; background: #ef4444; border-radius: 50%;\n"
        "      animation: pulse 1s infinite;\n"
        "    }\n"
        "    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); }\n"
        "    #chart { width: 100%; min-height: 300px; }\n"
        "    .metrics { display: flex; gap: 16px; margin-top: 8px; }\n"
        "    .metric {\n"
        "      flex: 1; text-align: center; padding: 8px;\n"
        "      background: var(--bg-card); border-radius: 6px; border: 1px solid var(--border);\n"
        "    }\n"
        "    .metric-value { font-size: 22px; font-weight: 700; }\n"
        "    .metric-value.up { color: var(--success); }\n"
        "    .metric-value.down { color: var(--error); }\n"
        "    .metric-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }\n"
        "    #status { font-size: 11px; color: var(--text-muted); text-align: center; padding: 4px; }\n"
        "    .controls { display: flex; gap: 8px; margin-top: 8px; justify-content: center; }\n"
        "    .ctrl-btn {\n"
        "      padding: 4px 14px; border-radius: 6px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-primary); cursor: pointer; font-size: 12px;\n"
        "    }\n"
        "    .ctrl-btn:hover { border-color: var(--accent); }\n"
        "    .ctrl-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }\n"
        "    .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text-muted); }\n"
        "    .error-msg { color: var(--error); padding: 20px; text-align: center; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="header">\n'
        '    <div class="title" id="stream-title">Live Data Stream</div>\n'
        '    <div class="header-right">\n'
        '      <button class="toolbar-btn" id="theme-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '      <div class="live-badge"><div class="live-dot"></div>LIVE</div>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div id="chart"><div class="loading">Waiting for stream config...</div></div>\n'
        '  <div class="metrics">\n'
        '    <div class="metric"><div class="metric-value" id="current">--</div><div class="metric-label">Current</div></div>\n'
        '    <div class="metric"><div class="metric-value" id="change">--</div><div class="metric-label">Change</div></div>\n'
        '    <div class="metric"><div class="metric-value" id="high">--</div><div class="metric-label">High</div></div>\n'
        '    <div class="metric"><div class="metric-value" id="low">--</div><div class="metric-label">Low</div></div>\n'
        "  </div>\n"
        '  <div class="controls">\n'
        '    <button class="ctrl-btn active" id="btn-play" onclick="toggleStream()">Pause</button>\n'
        '    <button class="ctrl-btn" onclick="resetStream()">Reset</button>\n'
        "  </div>\n"
        '  <div id="status">Waiting for stream...</div>\n'
        "\n"
        '  <script type="module">\n'
        '    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";\n'
        '    const app = new App({ name: "Panel Stream", version: "0.2.0" });\n'
        "\n"
        "    let config = null;\n"
        "    let streamInterval = null;\n"
        "    let running = false;\n"
        "    let currentVal = 0;\n"
        "    let highVal = -Infinity, lowVal = Infinity;\n"
        "    let tickCount = 0;\n"
        "    let bokehSource = null;\n"
        "    let xData = [];\n"
        "    let yData = [];\n"
        "\n"
        "    window.toggleTheme = () => {\n"
        '      const theme = document.body.className === "theme-dark" ? "theme-light" : "theme-dark";\n'
        "      document.body.className = theme;\n"
        '      document.getElementById("theme-btn").textContent = theme === "theme-dark" ? "Light Mode" : "Dark Mode";\n'
        "    };\n"
        "\n"
        "    window.toggleStream = () => {\n"
        '      const btn = document.getElementById("btn-play");\n'
        "      if (running) {\n"
        "        clearInterval(streamInterval);\n"
        "        running = false;\n"
        '        btn.textContent = "Play";\n'
        '        btn.classList.remove("active");\n'
        "      } else {\n"
        "        startStream();\n"
        '        btn.textContent = "Pause";\n'
        '        btn.classList.add("active");\n'
        "      }\n"
        "    };\n"
        "\n"
        "    window.resetStream = () => {\n"
        "      xData = []; yData = [];\n"
        "      tickCount = 0;\n"
        "      highVal = -Infinity; lowVal = Infinity;\n"
        "      if (config) {\n"
        "        currentVal = config.initial_value;\n"
        "        if (bokehSource) {\n"
        "          bokehSource.data = { x: [], y: [] };\n"
        "          bokehSource.change.emit();\n"
        "        }\n"
        "        startStream();\n"
        "      }\n"
        "    };\n"
        "\n"
        "    function startStream() {\n"
        "      if (streamInterval) clearInterval(streamInterval);\n"
        "      running = true;\n"
        "      streamInterval = setInterval(() => {\n"
        "        const change = (Math.random() - 0.5) * 2 * config.volatility;\n"
        "        currentVal += change;\n"
        "        tickCount++;\n"
        "        const val = Math.round(currentVal * 100) / 100;\n"
        "        xData.push(tickCount);\n"
        "        yData.push(val);\n"
        "        if (xData.length > config.points) { xData.shift(); yData.shift(); }\n"
        "        highVal = Math.max(highVal, currentVal);\n"
        "        lowVal = Math.min(lowVal, currentVal);\n"
        "        const pctChange = ((currentVal - config.initial_value) / config.initial_value * 100);\n"
        "        if (bokehSource) {\n"
        "          bokehSource.data = { x: xData.slice(), y: yData.slice() };\n"
        "          bokehSource.change.emit();\n"
        "        }\n"
        '        const curEl = document.getElementById("current");\n'
        "        curEl.textContent = currentVal.toFixed(1);\n"
        '        curEl.className = "metric-value " + (pctChange >= 0 ? "up" : "down");\n'
        '        const chgEl = document.getElementById("change");\n'
        '        chgEl.textContent = (pctChange >= 0 ? "+" : "") + pctChange.toFixed(2) + "%";\n'
        '        chgEl.className = "metric-value " + (pctChange >= 0 ? "up" : "down");\n'
        '        document.getElementById("high").textContent = highVal.toFixed(1);\n'
        '        document.getElementById("high").className = "metric-value up";\n'
        '        document.getElementById("low").textContent = lowVal.toFixed(1);\n'
        '        document.getElementById("low").className = "metric-value down";\n'
        '        document.getElementById("status").textContent =\n'
        '          "Streaming | " + yData.length + " points | " + config.interval_ms + "ms interval";\n'
        "      }, config.interval_ms);\n"
        "    }\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const text = content?.find(c => c.type === "text");\n'
        "      if (!text) return;\n"
        "      let r;\n"
        "      try { r = JSON.parse(text.text); } catch { return; }\n"
        "\n"
        '      if (r.action === "stream") {\n'
        '        document.getElementById("stream-title").textContent = r.title;\n'
        "        config = r.config;\n"
        "        currentVal = config.initial_value;\n"
        "        xData = []; yData = []; tickCount = 0;\n"
        "        highVal = config.initial_value; lowVal = config.initial_value;\n"
        '        document.getElementById("chart").innerHTML = "";\n'
        "        try {\n"
        "          bokehSource = new Bokeh.ColumnDataSource({ data: { x: [0], y: [config.initial_value] } });\n"
        "          const fig = Bokeh.Plotting.figure({\n"
        "            width: 600, height: 280, toolbar_location: null,\n"
        "            background_fill_alpha: 0, border_fill_alpha: 0, outline_line_alpha: 0,\n"
        "          });\n"
        "          fig.line({ field: 'x' }, { field: 'y' }, { source: bokehSource, line_width: 3, line_color: '#4ade80' });\n"
        "          fig.scatter({ field: 'x' }, { field: 'y' }, { source: bokehSource, size: 5, fill_color: '#4ade80', line_color: '#4ade80' });\n"
        "          for (const ax of [...fig.xaxis, ...fig.yaxis]) {\n"
        "            ax.axis_label_text_color = '#94a3b8'; ax.major_label_text_color = '#94a3b8';\n"
        "            ax.major_tick_line_color = '#475569'; ax.axis_line_color = '#475569';\n"
        "          }\n"
        "          for (const g of [...fig.xgrid, ...fig.ygrid]) { g.grid_line_color = '#334155'; g.grid_line_alpha = 0.5; }\n"
        "          if (fig.title) { fig.title.text_color = '#e0e0e0'; }\n"
        '          await Bokeh.Plotting.show(fig, "#chart");\n'
        "          startStream();\n"
        "        } catch (err) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-msg">Stream error: \' + err.message + \'</div>\';\n'
        "        }\n"
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Resource 4 - Multi-chart dashboard (multi.html) - NEW
# ---------------------------------------------------------------------------
@mcp.resource(
    MULTI_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def multi_view() -> str:
    """Multi-chart dashboard with 2-4 charts in a grid layout."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Multi-Chart Dashboard</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: transparent; color: var(--text-primary); padding: 12px;\n"
        "    }\n"
        "    .multi-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }\n"
        "    .multi-title { font-size: 18px; font-weight: 600; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }\n"
        "    .chart-grid.count-1 { grid-template-columns: 1fr; }\n"
        "    .chart-grid.count-3 .chart-cell:last-child { grid-column: 1 / -1; }\n"
        "    .chart-cell {\n"
        "      background: var(--bg-card); border: 1px solid var(--border);\n"
        "      border-radius: 8px; padding: 8px; min-height: 280px;\n"
        "    }\n"
        "    .chart-cell-title { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; text-align: center; }\n"
        "    #status { font-size: 11px; color: var(--text-muted); text-align: center; padding: 8px; }\n"
        "    .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text-muted); }\n"
        "    .error-msg { color: var(--error); padding: 20px; text-align: center; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="multi-header">\n'
        '    <div class="multi-title" id="multi-title">Multi-Chart Dashboard</div>\n'
        '    <button class="toolbar-btn" id="theme-btn" onclick="toggleTheme()">Light Mode</button>\n'
        "  </div>\n"
        '  <div class="chart-grid" id="chart-grid"><div class="loading">Waiting for chart data...</div></div>\n'
        '  <div id="status">panel-viz-mcp multi-chart ready</div>\n'
        "\n"
        '  <script type="module">\n'
        '    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";\n'
        '    const app = new App({ name: "Panel Multi-Chart", version: "0.2.0" });\n'
        "\n"
        "    window.toggleTheme = () => {\n"
        '      const theme = document.body.className === "theme-dark" ? "theme-light" : "theme-dark";\n'
        "      document.body.className = theme;\n"
        '      document.getElementById("theme-btn").textContent = theme === "theme-dark" ? "Light Mode" : "Dark Mode";\n'
        "    };\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const text = content?.find(c => c.type === "text");\n'
        "      if (!text) return;\n"
        "      let r;\n"
        "      try { r = JSON.parse(text.text); } catch { return; }\n"
        "\n"
        '      if (r.action === "multi_chart") {\n'
        '        document.getElementById("multi-title").textContent = r.title;\n'
        '        const grid = document.getElementById("chart-grid");\n'
        '        grid.innerHTML = "";\n'
        '        grid.className = "chart-grid count-" + r.chart_count;\n'
        "        for (const fig of r.figures) {\n"
        '          const cell = document.createElement("div");\n'
        '          cell.className = "chart-cell";\n'
        "          cell.innerHTML = '<div class=\"chart-cell-title\">' + fig.title + '</div>' +\n"
        "            '<div id=\"' + fig.target_id + '\"></div>';\n"
        "          grid.appendChild(cell);\n"
        "        }\n"
        "        for (const fig of r.figures) {\n"
        "          if (fig.figure) {\n"
        "            try { await Bokeh.embed.embed_item(fig.figure); } catch (err) {\n"
        "              document.getElementById(fig.target_id).innerHTML = '<div class=\"error-msg\">' + err.message + '</div>';\n"
        "            }\n"
        "          } else if (fig.error) {\n"
        "            document.getElementById(fig.target_id).innerHTML = '<div class=\"error-msg\">' + fig.error + '</div>';\n"
        "          }\n"
        "        }\n"
        '        document.getElementById("status").textContent = "Multi-chart loaded | ID: " + r.id + " | " + r.chart_count + " charts";\n'
        "      }\n"
        "\n"
        '      if (r.action === "error") {\n'
        '        document.getElementById("chart-grid").innerHTML = \'<div class="error-msg">\' + r.message + \'</div>\';\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )


# ===========================================================================
# Entry point
# ===========================================================================
def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
