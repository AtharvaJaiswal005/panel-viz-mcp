"""panel-viz-mcp: Interactive Panel/HoloViews visualizations inside AI chats via MCP Apps."""

# Re-export key symbols for backward compatibility and test imports
from .app import _panel_servers, _viz_store, mcp  # noqa: F401
from .cdn import BOKEH_SCRIPTS, BOKEH_SCRIPTS_WITH_API, BOKEH_VERSION  # noqa: F401
from .chart_builders import (  # noqa: F401
    _add_annotation_to_figure,
    _apply_theme,
    _apply_theme_to_layout,
    _build_bokeh_figure,
    _build_widget_config,
    _rebuild_figure_with_annotations,
)
from .code_generators import (  # noqa: F401
    _generate_geo_panel_code,
    _generate_multi_panel_code,
    _generate_panel_code,
)
from .constants import (  # noqa: F401
    ANNOTATION_TYPES,
    CHART_PALETTE,
    CHART_TYPES,
    DASHBOARD_URI,
    MAX_CHART_ROWS,
    MAX_TABLE_ROWS,
    MCP_APPS_SDK_URL,
    MCP_APPS_SDK_VERSION,
    MULTI_URI,
    STREAM_URI,
    VIEW_URI,
)
from .themes import CSS_THEME_VARS as _CSS_THEME_VARS  # noqa: F401
from .themes import THEME_COLORS  # noqa: F401

from . import tools  # noqa: F401 - triggers @mcp.tool() registration
from . import resources  # noqa: F401 - triggers @mcp.resource() registration

# ===========================================================================
# Entry point
# ===========================================================================
def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
