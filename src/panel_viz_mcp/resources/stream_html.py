"""MCP Apps resource: streaming chart HTML."""

from fastmcp.server.apps import AppConfig, ResourceCSP

from ..app import mcp
from ..cdn import BOKEH_SCRIPTS_WITH_API
from ..constants import MCP_APPS_SDK_URL, STREAM_URI
from ..themes import CSS_THEME_VARS as _CSS_THEME_VARS


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
        "      background: var(--bg-body); color: var(--text-primary); padding: 12px;\n"
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
        '      <!-- Panel launch not supported for streams -->\n'
        '      <div class="live-badge"><div class="live-dot"></div>LIVE</div>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div id="chart"><div class="loading"><div class="spinner"></div><span>Waiting for stream config...</span></div></div>\n'
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
        f'    import {{ App }} from "{MCP_APPS_SDK_URL}";\n'
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
        "    let currentVizId = null;\n"
        "\n"
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
        "        currentVizId = r.id;\n"
        '        document.getElementById("stream-title").textContent = r.title;\n'
        "        config = r.config;\n"
        "        currentVal = config.initial_value;\n"
        "        xData = []; yData = []; tickCount = 0;\n"
        "        highVal = config.initial_value; lowVal = config.initial_value;\n"
        '        document.getElementById("chart").innerHTML = "";\n'
        "        try {\n"
        "          bokehSource = new Bokeh.ColumnDataSource({ data: { x: [0], y: [config.initial_value] } });\n"
        "          const fig = Bokeh.Plotting.figure({\n"
        "            height: 280, toolbar_location: null,\n"
        "            background_fill_alpha: 0, border_fill_alpha: 0, outline_line_alpha: 0,\n"
        "            sizing_mode: 'stretch_width',\n"
        "          });\n"
        "          fig.line({ field: 'x' }, { field: 'y' }, { source: bokehSource, line_width: 3, line_color: '#818cf8' });\n"
        "          fig.scatter({ field: 'x' }, { field: 'y' }, { source: bokehSource, size: 5, fill_color: '#818cf8', line_color: '#818cf8' });\n"
        "          for (const ax of [...fig.xaxis, ...fig.yaxis]) {\n"
        "            ax.axis_label_text_color = '#94a3b8'; ax.major_label_text_color = '#94a3b8';\n"
        "            ax.major_tick_line_color = '#475569'; ax.axis_line_color = '#475569';\n"
        "          }\n"
        "          for (const g of [...fig.xgrid, ...fig.ygrid]) { g.grid_line_color = '#334155'; g.grid_line_alpha = 0.5; }\n"
        "          if (fig.title) { fig.title.text_color = '#e0e0e0'; }\n"
        '          await Bokeh.Plotting.show(fig, "#chart");\n'
        "          startStream();\n"
        "        } catch (err) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Stream Error</div>\' + err.message + \'</div>\';\n'
        "        }\n"
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )
