# panel-viz-mcp

Interactive [Panel](https://panel.holoviz.org/) / [HoloViews](https://holoviews.org/) visualizations rendered directly inside AI chat UIs via the [MCP Apps Standard](https://github.com/modelcontextprotocol/ext-apps).

> Built with [FastMCP](https://github.com/jlowin/fastmcp), [hvPlot](https://hvplot.holoviz.org/), [Bokeh](https://bokeh.org/), and [Panel](https://panel.holoviz.org/).

## What is this?

An MCP server that lets AI assistants create, modify, and render interactive visualizations **inline** in the chat conversation. Charts render as live BokehJS figures inside sandboxed iframes - not static images, not external links.

Works with any MCP Apps-compatible client:
- **VS Code Copilot Chat**
- **Claude Desktop / Claude Code**
- **ChatGPT** (Business/Enterprise/Edu)
- **Cursor**
- **Goose**

## Features

### 13 Chart Types

| Type | Description | Special Parameters |
|------|-------------|-------------------|
| `bar` | Vertical bar chart | - |
| `line` | Line chart | - |
| `scatter` | Scatter plot | - |
| `area` | Filled area chart | - |
| `pie` | Pie/donut chart | - |
| `histogram` | Frequency distribution | - |
| `box` | Box plot | `x` = grouping column (categorical), `y` = numeric |
| `violin` | Violin plot | `x` = grouping column (categorical), `y` = numeric |
| `kde` | Kernel density estimate | Only `y` needed (density of that column) |
| `step` | Step chart | - |
| `heatmap` | Categorical heatmap | `color` = value column (C) |
| `hexbin` | Hexagonal binning | Both `x` and `y` must be numeric |
| `points` | Geographic scatter map | `x` = longitude, `y` = latitude, requires `geoviews` |

### 15 MCP Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `create_viz` | Create a chart (any of 13 types) |
| 2 | `update_viz` | Modify an existing chart (change type, data, axes, title) |
| 3 | `load_data` | Load CSV/Parquet/JSON/Excel/Feather/Zarr and visualize |
| 4 | `handle_click` | Process click events from charts (bidirectional) |
| 5 | `list_vizs` | List all active visualizations |
| 6 | `create_dashboard` | Dashboard with chart + stats + table + filter widgets |
| 7 | `stream_data` | Live-updating streaming chart |
| 8 | `apply_filter` | Apply widget filters to a dashboard (crossfiltering) |
| 9 | `set_theme` | Switch between dark and light theme |
| 10 | `create_multi_chart` | 2-4 chart grid layout from the same dataset |
| 11 | `annotate_viz` | Add annotations (hline, vline, text, band, arrow) |
| 12 | `export_data` | Export data as CSV or JSON |
| 13 | `launch_panel` | Open a full interactive Panel app in the browser |
| 14 | `stop_panel` | Stop a running Panel server |
| 15 | `create_panel_app` | Launch a custom Panel app from LLM-written Python code |

### 4 Interactive UI Resources (MCP Apps)

| Resource | Description |
|----------|-------------|
| `ui://panel-viz-mcp/viz.html` | Single chart viewer with toolbar (theme toggle, Save PNG, Export CSV, Open in Panel) |
| `ui://panel-viz-mcp/dashboard.html` | Dashboard with chart, summary stats, data table, and filter sidebar |
| `ui://panel-viz-mcp/stream.html` | Live streaming chart with play/pause/reset controls |
| `ui://panel-viz-mcp/multi.html` | Multi-chart grid (2-4 charts from the same data) |

### Key Capabilities

- **Bidirectional communication** - click a data point in the chart, get AI-generated insights back
- **Server-side crossfiltering** - filter sidebar with Select dropdowns and Range sliders, filters update chart + stats + table
- **Live streaming** - real-time data simulation with client-side BokehJS updates
- **Annotations** - horizontal/vertical lines, text labels, bands, arrows
- **Theme switching** - dark/light mode toggle with CSS variables + Bokeh re-rendering
- **"Open in Panel" button** - launch a full interactive Panel app in the browser from any inline chart
- **Rich Panel apps** - generated apps include FloatPanel chart inspector, Tabulator data table, Number indicators, crossfiltering sidebar, FastListTemplate dark theme
- **Save PNG / Export CSV** - toolbar buttons on every chart

## Quick Start

First, clone and install (required for all clients):

```bash
git clone https://github.com/AtharvaJaiswal005/panel-viz-mcp.git
cd panel-viz-mcp
pip install -e .
```

For geographic maps, also install geo extras: `pip install -e ".[geo]"`

Then pick your client:

### Claude Code (CLI)

Just paste this prompt into Claude Code and it will handle everything:

> Install panel-viz-mcp: clone https://github.com/AtharvaJaiswal005/panel-viz-mcp.git, run `pip install -e .`, then run `claude mcp add panel-viz-mcp -- panel-viz-mcp`

Or do it manually:

```bash
claude mcp add panel-viz-mcp -- panel-viz-mcp
```

### Claude Desktop

1. Open **Settings > Developer > Edit Config**
2. Paste this into `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "panel-viz-mcp": {
      "command": "panel-viz-mcp"
    }
  }
}
```

3. Save the file and **fully restart** Claude Desktop

### VS Code / Copilot Chat

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "panel-viz-mcp": {
      "command": "panel-viz-mcp"
    }
  }
}
```

### Cursor / Goose / Other MCP Clients

Use stdio transport with command `panel-viz-mcp`.

## Usage Examples

### Basic bar chart

> "Create a bar chart of sales by region"

The AI calls `create_viz` with your data, and an interactive BokehJS chart appears inline in the chat.

### Dashboard with filters

> "Create a dashboard from this CSV file with filters for category and quarter"

Creates a full dashboard with chart, summary statistics (count, mean, min, max), data table, and a filter sidebar. Changing a filter updates everything in real-time via server round-trips.

### Geographic map

> "Plot these cities on a map: NYC (40.7, -73.9), LA (34.1, -118.2), Chicago (41.9, -87.6)"

Creates a geographic scatter plot with CartoDark tile basemaps (requires `geoviews`).

### Multi-chart view

> "Show me a bar chart and a line chart of the same data side by side"

Creates a 2-chart grid layout from the same dataset.

### Streaming

> "Create a live stock price chart starting at $100"

Creates a streaming chart that simulates real-time data with play/pause/reset controls.

### Open in Panel

Click the **"Open in Panel"** button on any inline chart to launch a full interactive Panel app in your browser with:
- Chart inspector (change chart type, axes, colors, title live)
- Tabulator data table with sorting/filtering/pagination
- Number indicators (count, mean, min, max)
- Filter sidebar with crossfiltering
- Dark theme (FastListTemplate)

## Architecture

```
User prompt
  -> AI calls MCP tool (e.g. create_viz)
    -> Python builds chart via hvPlot / HoloViews
      -> hv.render(backend="bokeh") converts to Bokeh figure
        -> bokeh.embed.json_item(fig) serializes to JSON
          -> JSON sent to MCP Apps iframe
            -> BokehJS renders interactive chart inline in chat UI
```

**Bidirectional flow:**
```
User clicks data point in chart
  -> BokehJS TapTool fires callback
    -> app.callServerTool("handle_click", {viz_id, point_index, x_value, y_value})
      -> Server generates insight text
        -> Response displayed in chart's status bar
```

**Filter flow:**
```
User changes filter widget in dashboard
  -> app.callServerTool("apply_filter", {viz_id, filters})
    -> Server filters DataFrame, rebuilds chart + stats + table
      -> Updated figure JSON + stats + table HTML returned
        -> Dashboard re-renders chart, stats panel, and data table
```

## Development

```bash
git clone https://github.com/AtharvaJaiswal005/panel-viz-mcp.git
cd panel-viz-mcp
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/ -v
```

51 tests cover all 15 tools, 13 chart types, edge cases, code generation, and security sandboxing.

### Project structure

```
panel-viz-mcp/
  src/panel_viz_mcp/
    __init__.py          # Package re-export
    app.py               # FastMCP instance + in-memory stores
    server.py            # Thin entry point with re-exports
    constants.py         # Chart types, URIs, limits, SDK version
    cdn.py               # BokehJS CDN script tags
    themes.py            # Theme colors + CSS variables
    chart_builders.py    # Bokeh figure construction + annotations
    code_generators/     # Panel app code generators
      standard.py        # Single-chart Panel apps
      geo.py             # DeckGL geographic apps
      multi.py           # Multi-chart grid apps
    tools/               # 15 MCP tools
      viz.py             # create, update, load, click, list
      dashboard.py       # create_dashboard, apply_filter, set_theme
      stream.py          # stream_data
      multi.py           # create_multi_chart
      annotation.py      # annotate_viz
      export.py          # export_data
      panel_launch.py    # launch_panel, stop_panel
      custom_app.py      # create_panel_app
    resources/           # 4 HTML resources (MCP Apps)
      viz_html.py        # Single chart viewer
      dashboard_html.py  # Dashboard with filters
      stream_html.py     # Live streaming chart
      multi_html.py      # Multi-chart grid
  tests/
    test_tools.py        # 51 pytest tests
  examples/
    sample_data.csv      # Sample CSV for load_data tool
  pyproject.toml
  LICENSE                # MIT
  README.md
```

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp) 3.x** - MCP server framework with Apps support
- **[Panel](https://panel.holoviz.org/)** - Interactive web apps and dashboards
- **[HoloViews](https://holoviews.org/)** - Declarative data visualization
- **[hvPlot](https://hvplot.holoviz.org/)** - High-level plotting API for pandas
- **[Bokeh](https://bokeh.org/)** - Interactive visualization library (rendering backend)
- **[GeoViews](https://geoviews.org/)** - Geographic visualizations (optional, for `points` type)

## Related Projects

- **[holoviz-mcp](https://github.com/MarcSkovMadsen/holoviz-mcp)** by Marc Skov Madsen - MCP server for HoloViz documentation and code execution
- **[panel-live](https://panel-extensions.github.io/panel-live/)** - Run Panel code in the browser with MCP support
- **[Panel #8396](https://github.com/holoviz/panel/issues/8396)** - Tracking issue for MCP Apps Standard support in Panel core

## License

MIT
