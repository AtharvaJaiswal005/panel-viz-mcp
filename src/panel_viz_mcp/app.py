"""FastMCP application instance and shared in-memory stores.

This module has ZERO internal imports to prevent circular dependencies.
All other modules import `mcp` from here.
"""

from fastmcp import FastMCP

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

# In-memory stores
_viz_store: dict[str, dict] = {}
_panel_servers: dict[str, dict] = {}
