"""Data export tool."""

import json

import pandas as pd
from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..constants import VIEW_URI


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
