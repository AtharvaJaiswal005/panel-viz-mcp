"""Annotation tool for adding visual markers to charts."""

import json

from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..chart_builders import _rebuild_figure_with_annotations
from ..constants import ANNOTATION_TYPES, VIEW_URI


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
