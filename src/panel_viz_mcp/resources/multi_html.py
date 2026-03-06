"""MCP Apps resource: multi-chart grid HTML."""

from fastmcp.server.apps import AppConfig, ResourceCSP

from ..app import mcp
from ..cdn import BOKEH_SCRIPTS
from ..constants import MCP_APPS_SDK_URL, MULTI_URI
from ..themes import CSS_THEME_VARS as _CSS_THEME_VARS


@mcp.resource(
    MULTI_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def multi_view() -> str:
    """Multi-chart dashboard with 2-4 charts in a grid layout."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Multi-Chart Dashboard</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: var(--bg-body); color: var(--text-primary); padding: 12px;\n"
        "    }\n"
        "    .multi-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }\n"
        "    .multi-title { font-size: 18px; font-weight: 600; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }\n"
        "    .chart-grid.count-1 { grid-template-columns: 1fr; }\n"
        "    .chart-grid.count-3 .chart-cell:last-child { grid-column: 1 / -1; }\n"
        "    .chart-cell {\n"
        "      background: var(--bg-card); border: 1px solid var(--border);\n"
        "      border-radius: 8px; padding: 8px; min-height: 280px;\n"
        "    }\n"
        "    .chart-cell-title { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; text-align: center; }\n"
        "    #status { font-size: 11px; color: var(--text-muted); text-align: center; padding: 8px; }\n"
        "    .loading { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text-muted); }\n"
        "    .error-msg { color: var(--error); padding: 20px; text-align: center; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="multi-header">\n'
        '    <div class="multi-title" id="multi-title">Multi-Chart Dashboard</div>\n'
        '    <button class="toolbar-btn" id="theme-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '    <button class="toolbar-btn" id="panel-btn" onclick="openInPanel()" style="display:none;">Open in Panel</button>\n'
        "  </div>\n"
        '  <div class="chart-grid" id="chart-grid"><div class="loading" style="grid-column:1/-1"><div class="spinner"></div><span>Waiting for chart data...</span></div></div>\n'
        '  <div id="status">panel-viz-mcp multi-chart ready</div>\n'
        "\n"
        '  <script type="module">\n'
        f'    import {{ App }} from "{MCP_APPS_SDK_URL}";\n'
        '    const app = new App({ name: "Panel Multi-Chart", version: "0.2.0" });\n'
        "    let currentVizId = null;\n"
        "\n"
        "    window.openInPanel = async () => {\n"
        "      if (!currentVizId) return;\n"
        '      const btn = document.getElementById("panel-btn");\n'
        '      btn.textContent = "Launching...";\n'
        "      btn.disabled = true;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "launch_panel",\n'
        "          arguments: { viz_id: currentVizId },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.url) document.getElementById("status").textContent = "Panel app: " + r.url;\n'
        "        }\n"
        "      } catch (err) { console.log('Panel launch:', err); }\n"
        "      finally {\n"
        '        btn.textContent = "Open in Panel";\n'
        "        btn.disabled = false;\n"
        "      }\n"
        "    };\n"
        "\n"
        "    window.toggleTheme = async () => {\n"
        '      const newTheme = document.body.className === "theme-dark" ? "light" : "dark";\n'
        '      document.body.className = "theme-" + newTheme;\n'
        '      document.getElementById("theme-btn").textContent = newTheme === "dark" ? "Light Mode" : "Dark Mode";\n'
        "      if (currentVizId) {\n"
        "        try {\n"
        "          const response = await app.callServerTool({\n"
        '            name: "set_theme",\n'
        "            arguments: { viz_id: currentVizId, theme: newTheme },\n"
        "          });\n"
        '          const t = response?.content?.find(c => c.type === "text");\n'
        "          if (t) {\n"
        "            const r = JSON.parse(t.text);\n"
        "            if (r.figure) {\n"
        '              const grid = document.getElementById("chart-grid");\n'
        '              grid.innerHTML = "";\n'
        '              grid.className = "chart-grid count-1";\n'
        "              await Bokeh.embed.embed_item(r.figure);\n"
        "            } else if (r.figures) {\n"
        '              const grid = document.getElementById("chart-grid");\n'
        '              grid.innerHTML = "";\n'
        '              grid.className = "chart-grid count-" + r.figures.length;\n'
        "              for (const fig of r.figures) {\n"
        '                const cell = document.createElement("div");\n'
        '                cell.className = "chart-cell";\n'
        "                cell.innerHTML = '<div id=\"' + fig.target_id + '\"></div>';\n"
        "                grid.appendChild(cell);\n"
        "              }\n"
        "              for (const fig of r.figures) {\n"
        "                if (fig.figure) await Bokeh.embed.embed_item(fig.figure);\n"
        "              }\n"
        "            }\n"
        "          }\n"
        "        } catch (err) { console.log('Theme toggle:', err); }\n"
        "      }\n"
        "    };\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const text = content?.find(c => c.type === "text");\n'
        "      if (!text) return;\n"
        "      let r;\n"
        "      try { r = JSON.parse(text.text); } catch { return; }\n"
        "\n"
        '      if (r.action === "multi_chart") {\n'
        "        currentVizId = r.id;\n"
        '        document.getElementById("panel-btn").style.display = "inline-block";\n'
        '        document.getElementById("multi-title").textContent = r.title;\n'
        '        const grid = document.getElementById("chart-grid");\n'
        '        grid.innerHTML = "";\n'
        "\n"
        "        if (r.figure) {\n"
        "          // Linked brushing - single layout figure\n"
        '          grid.className = "chart-grid count-1";\n'
        "          try { await Bokeh.embed.embed_item(r.figure); } catch (err) {\n"
        '            grid.innerHTML = \'<div class="error-box" style="grid-column:1/-1"><div class="error-title">Render Error</div>\' + err.message + \'</div>\';\n'
        "          }\n"
        "        } else if (r.figures) {\n"
        "          // Fallback - individual charts\n"
        '          grid.className = "chart-grid count-" + r.chart_count;\n'
        "          for (const fig of r.figures) {\n"
        '            const cell = document.createElement("div");\n'
        '            cell.className = "chart-cell";\n'
        "            cell.innerHTML = '<div class=\"chart-cell-title\">' + fig.title + '</div>' +\n"
        "              '<div id=\"' + fig.target_id + '\"></div>';\n"
        "            grid.appendChild(cell);\n"
        "          }\n"
        "          for (const fig of r.figures) {\n"
        "            if (fig.figure) {\n"
        "              try { await Bokeh.embed.embed_item(fig.figure); } catch (err) {\n"
        "                document.getElementById(fig.target_id).innerHTML = '<div class=\"error-box\"><div class=\"error-title\">Render Error</div>' + err.message + '</div>';\n"
        "              }\n"
        "            } else if (fig.error) {\n"
        "              document.getElementById(fig.target_id).innerHTML = '<div class=\"error-box\"><div class=\"error-title\">Chart Error</div>' + fig.error + '</div>';\n"
        "            }\n"
        "          }\n"
        "        }\n"
        '        const linkedTag = r.linked ? " (linked)" : "";\n'
        '        document.getElementById("status").textContent = "Multi-chart loaded | " + r.chart_count + " charts" + linkedTag;\n'
        "      }\n"
        "\n"
        '      if (r.action === "error") {\n'
        '        document.getElementById("chart-grid").innerHTML = \'<div class="error-box" style="grid-column:1/-1"><div class="error-title">Error</div>\' + r.message + \'</div>\';\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )
