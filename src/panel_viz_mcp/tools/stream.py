"""Streaming chart tool."""

import json
import uuid

from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..constants import STREAM_URI


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
    if volatility < 0:
        return json.dumps({"action": "error", "message": "volatility must be non-negative"})
    if points < 1 or points > 10000:
        return json.dumps({"action": "error", "message": "points must be between 1 and 10000"})
    if interval_ms < 50 or interval_ms > 60000:
        return json.dumps({"action": "error", "message": "interval_ms must be between 50 and 60000"})

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
