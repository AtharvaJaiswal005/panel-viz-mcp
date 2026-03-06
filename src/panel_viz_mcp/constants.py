"""Shared constants for panel-viz-mcp."""

# ---------------------------------------------------------------------------
# MCP Apps SDK version (single source of truth for all HTML resources)
# ---------------------------------------------------------------------------
MCP_APPS_SDK_VERSION = "0.4.0"
MCP_APPS_SDK_URL = f"https://unpkg.com/@modelcontextprotocol/ext-apps@{MCP_APPS_SDK_VERSION}/app-with-deps"

# ---------------------------------------------------------------------------
# Resource URIs
# ---------------------------------------------------------------------------
VIEW_URI = "ui://panel-viz-mcp/viz.html"
DASHBOARD_URI = "ui://panel-viz-mcp/dashboard.html"
STREAM_URI = "ui://panel-viz-mcp/stream.html"
MULTI_URI = "ui://panel-viz-mcp/multi.html"

# ---------------------------------------------------------------------------
# Chart / annotation types
# ---------------------------------------------------------------------------
CHART_TYPES = [
    "bar", "line", "scatter", "area", "pie", "histogram",
    "box", "violin", "kde", "step", "heatmap", "hexbin", "points",
]
ANNOTATION_TYPES = ["text", "hline", "vline", "band", "arrow"]

# ---------------------------------------------------------------------------
# Color palette (vivid but not harsh on dark backgrounds)
# ---------------------------------------------------------------------------
CHART_PALETTE = [
    "#818cf8", "#4ade80", "#f59e0b", "#f87171", "#38bdf8",
    "#c084fc", "#fb923c", "#2dd4bf", "#e879f9", "#a3e635",
]

# ---------------------------------------------------------------------------
# Data limits
# ---------------------------------------------------------------------------
MAX_CHART_ROWS = 10000
MAX_TABLE_ROWS = 200
