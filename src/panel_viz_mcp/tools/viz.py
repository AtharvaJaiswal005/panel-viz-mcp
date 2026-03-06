"""Visualization tools: create, update, load, click handler, list."""

import json
import os
import uuid

import pandas as pd
from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..chart_builders import _build_bokeh_figure, _rebuild_figure_with_annotations
from ..constants import MAX_CHART_ROWS, VIEW_URI


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
        total_rows = len(df)
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

        result = {"action": "create", "id": viz_id, "figure": spec}
        if total_rows > MAX_CHART_ROWS:
            result["sampled"] = True
            result["total_rows"] = total_rows
            result["shown_rows"] = MAX_CHART_ROWS
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


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

        # Validate columns exist in current data
        cols = list(pd.DataFrame(viz["data"]).columns)
        if viz["x"] not in cols:
            return json.dumps({"action": "error", "message": f"Column '{viz['x']}' not found in data. Available: {cols}"})
        if viz["y"] not in cols:
            return json.dumps({"action": "error", "message": f"Column '{viz['y']}' not found in data. Available: {cols}"})

        spec = _rebuild_figure_with_annotations(viz)

        return json.dumps({"action": "update", "id": viz_id, "figure": spec})
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


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

        lp = file_path.lower()
        if lp.endswith(".parquet") or lp.endswith(".pq"):
            df = pd.read_parquet(file_path)
        elif lp.endswith(".csv") or lp.endswith(".tsv"):
            sep = "\t" if lp.endswith(".tsv") else ","
            df = pd.read_csv(file_path, sep=sep)
        elif lp.endswith(".json") or lp.endswith(".jsonl"):
            df = pd.read_json(file_path, lines=lp.endswith(".jsonl"))
        elif lp.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        elif lp.endswith(".feather") or lp.endswith(".arrow"):
            df = pd.read_feather(file_path)
        elif lp.endswith(".zarr"):
            import zarr
            zgroup = zarr.open(file_path, mode="r")
            arrays = {k: zgroup[k][:] for k in zgroup.array_keys()}
            df = pd.DataFrame(arrays)
        else:
            return json.dumps({"action": "error",
                               "message": "Unsupported format. Use: .csv, .tsv, .parquet, .json, .jsonl, .xlsx, .feather, .arrow, .zarr"})

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

        # Column preview: dtype + sample values for each column
        col_preview = {}
        for col in df.columns:
            sample = df[col].dropna().head(3).tolist()
            col_preview[col] = {
                "dtype": str(df[col].dtype),
                "nulls": int(df[col].isna().sum()),
                "unique": int(df[col].nunique()),
                "sample": [str(v) for v in sample],
            }

        return json.dumps({
            "action": "create",
            "id": viz_id,
            "figure": spec,
            "info": {
                "columns": list(df.columns),
                "rows": len(df),
                "file": file_path,
                "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 1),
                "column_preview": col_preview,
            },
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})


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


@mcp.tool(app=AppConfig(resource_uri=VIEW_URI, visibility=["app"]))
def list_vizs() -> str:
    """List all active visualizations. Called by the app UI."""
    vizs = [{"id": v["id"], "title": v["title"], "kind": v["kind"]} for v in _viz_store.values()]
    return json.dumps({"action": "list", "visualizations": vizs})
