"""Dashboard tools: create dashboard, apply filter, set theme."""

import json
import uuid

import pandas as pd
from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..chart_builders import (
    _build_bokeh_figure,
    _build_widget_config,
    _rebuild_figure_with_annotations,
)
from ..constants import DASHBOARD_URI, MAX_CHART_ROWS, MAX_TABLE_ROWS, VIEW_URI


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

        total_rows = len(df)
        table_rows = df.head(MAX_TABLE_ROWS).values.tolist()

        result = {
            "action": "dashboard",
            "id": viz_id,
            "title": title,
            "figure": spec,
            "table": {"columns": list(df.columns), "rows": table_rows, "total": total_rows},
            "stats": stats,
            "y_column": y,
            "widget_config": widget_config,
        }
        if total_rows > MAX_CHART_ROWS:
            result["sampled"] = True
            result["total_rows"] = total_rows
            result["shown_rows"] = MAX_CHART_ROWS
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


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
            "table": {"columns": list(df.columns), "rows": df.head(MAX_TABLE_ROWS).values.tolist(), "total": len(df)},
            "stats": stats,
            "filtered_rows": len(df),
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


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
