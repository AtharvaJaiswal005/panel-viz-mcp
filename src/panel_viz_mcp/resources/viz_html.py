"""MCP Apps resource: visualization viewer HTML."""

from fastmcp.server.apps import AppConfig, ResourceCSP

from ..app import mcp
from ..cdn import BOKEH_SCRIPTS
from ..constants import MCP_APPS_SDK_URL, VIEW_URI
from ..themes import CSS_THEME_VARS as _CSS_THEME_VARS


@mcp.resource(
    VIEW_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def viz_view() -> str:
    """Interactive visualization viewer powered by hvPlot + BokehJS."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Panel Viz MCP</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: var(--bg-body); color: var(--text-primary); padding: 8px;\n"
        "    }\n"
        "    #chart-container { width: 100%; min-height: 320px; border-radius: 8px; overflow: hidden; }\n"
        "    #status { font-size: 12px; color: var(--text-muted); padding: 4px 0; text-align: center; }\n"
        "    #insight-bar {\n"
        "      display: none; background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3);\n"
        "      border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 13px;\n"
        "      color: #93c5fd; white-space: pre-line;\n"
        "    }\n"
        "    #viz-id { font-size: 11px; color: var(--text-muted); text-align: right; padding: 2px 0; }\n"
        "    .toolbar { display: flex; gap: 6px; justify-content: flex-end; padding: 4px 0; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .export-modal {\n"
        "      position: fixed; top: 0; left: 0; width: 100%; height: 100%;\n"
        "      background: rgba(0,0,0,0.7); z-index: 1000; display: flex;\n"
        "      align-items: center; justify-content: center;\n"
        "    }\n"
        "    .export-modal-inner {\n"
        "      background: var(--btn-bg); border-radius: 8px; padding: 16px;\n"
        "      width: 80%; max-height: 80%; overflow: auto; border: 1px solid var(--border);\n"
        "    }\n"
        "    .export-textarea {\n"
        "      width: 100%; height: 300px; background: var(--input-bg); color: var(--text-primary);\n"
        "      border: 1px solid var(--border); border-radius: 4px; padding: 8px;\n"
        "      font-family: monospace; font-size: 11px; resize: vertical;\n"
        "    }\n"
        "    .geo-banner {\n"
        "      display: none; background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(59,130,246,0.15));\n"
        "      border: 1px solid rgba(99,102,241,0.3); border-radius: 8px; padding: 12px 16px;\n"
        "      margin-top: 8px; text-align: center;\n"
        "    }\n"
        "    .geo-banner .geo-icon { font-size: 24px; margin-bottom: 4px; }\n"
        "    .geo-banner .geo-text { font-size: 13px; color: #a5b4fc; }\n"
        "    .geo-banner .geo-hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="toolbar" id="toolbar" style="display:none;">\n'
        '    <button class="toolbar-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '    <button class="toolbar-btn" onclick="exportPNG()">Save PNG</button>\n'
        '    <button class="toolbar-btn" onclick="exportCSV()">Export CSV</button>\n'
        '    <button class="toolbar-btn" id="panel-btn" onclick="openInPanel()">Open in Panel</button>\n'
        "  </div>\n"
        '  <div id="chart-container"><div class="loading"><div class="spinner"></div><span>Preparing visualization...</span></div></div>\n'
        '  <div id="sample-notice" style="display:none;"></div>\n'
        '  <div class="geo-banner" id="geo-banner">\n'
        '    <div class="geo-icon">&#127758;</div>\n'
        '    <div class="geo-text">This is a geographic preview. Click <strong>Open in Panel</strong> above for the full interactive map with tile basemaps.</div>\n'
        '    <div class="geo-hint">The inline iframe restricts map tiles - the Panel app shows the complete CartoDark map.</div>\n'
        '  </div>\n'
        '  <div id="insight-bar"></div>\n'
        '  <div id="viz-id"></div>\n'
        '  <div id="status">panel-viz-mcp ready (HoloViz + BokehJS)</div>\n'
        "\n"
        '  <script type="module">\n'
        f'    import {{ App }} from "{MCP_APPS_SDK_URL}";\n'
        '    const app = new App({ name: "Panel Viz MCP", version: "0.2.0" });\n'
        "    let currentVizId = null;\n"
        '    let currentTheme = "dark";\n'
        "\n"
        "    window.toggleTheme = async () => {\n"
        '      currentTheme = currentTheme === "dark" ? "light" : "dark";\n'
        '      document.body.className = "theme-" + currentTheme;\n'
        '      document.querySelector(".toolbar-btn").textContent = currentTheme === "dark" ? "Light Mode" : "Dark Mode";\n'
        "      if (currentVizId) {\n"
        "        try {\n"
        "          const response = await app.callServerTool({\n"
        '            name: "set_theme",\n'
        "            arguments: { viz_id: currentVizId, theme: currentTheme },\n"
        "          });\n"
        '          const t = response?.content?.find(c => c.type === "text");\n'
        "          if (t) {\n"
        "            const r = JSON.parse(t.text);\n"
        '            if (r.action === "theme_change" && r.figure) {\n'
        '              const container = document.getElementById("chart-container");\n'
        '              container.innerHTML = "";\n'
        "              await Bokeh.embed.embed_item(r.figure);\n"
        "            }\n"
        "          }\n"
        "        } catch (err) { console.log('Theme switch:', err); }\n"
        "      }\n"
        "    };\n"
        "\n"
        "    window.exportPNG = () => {\n"
        "      const canvas = document.querySelector('#chart-container canvas');\n"
        "      if (!canvas) { alert('No chart canvas found'); return; }\n"
        '      const link = document.createElement("a");\n'
        '      link.download = "chart.png";\n'
        '      link.href = canvas.toDataURL("image/png");\n'
        "      link.click();\n"
        "    };\n"
        "\n"
        "    window.exportCSV = async () => {\n"
        "      if (!currentVizId) return;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "export_data",\n'
        '          arguments: { viz_id: currentVizId, format: "csv" },\n'
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const result = JSON.parse(t.text);\n"
        '          if (result.action === "export") {\n'
        "            try {\n"
        '              const blob = new Blob([result.data], { type: "text/csv" });\n'
        "              const url = URL.createObjectURL(blob);\n"
        '              const link = document.createElement("a");\n'
        "              link.href = url; link.download = result.filename; link.click();\n"
        "              URL.revokeObjectURL(url);\n"
        "            } catch (dlErr) {\n"
        '              const modal = document.createElement("div");\n'
        '              modal.className = "export-modal";\n'
        "              modal.innerHTML = '<div class=\"export-modal-inner\">' +\n"
        "                '<div style=\"display:flex;justify-content:space-between;margin-bottom:8px;\">' +\n"
        "                '<span>Export Data (CSV)</span>' +\n"
        "                '<button onclick=\"this.closest(\\'.export-modal\\').remove()\" class=\"toolbar-btn\">Close</button></div>' +\n"
        "                '<textarea class=\"export-textarea\">' + result.data.replace(/</g, '&lt;') + '</textarea></div>';\n"
        "              document.body.appendChild(modal);\n"
        "            }\n"
        "          }\n"
        "        }\n"
        "      } catch (err) { console.error('Export error:', err); }\n"
        "    };\n"
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
        "    window.addEventListener('bokeh-tap', async (e) => {\n"
        "      if (!currentVizId) return;\n"
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "handle_click",\n'
        "          arguments: {\n"
        "            viz_id: currentVizId,\n"
        "            point_index: e.detail.index,\n"
        "            x_value: e.detail.xValue,\n"
        "            y_value: e.detail.yValue,\n"
        "          },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "insight") {\n'
        '            const bar = document.getElementById("insight-bar");\n'
        "            bar.textContent = r.message;\n"
        '            bar.style.display = "block";\n'
        "          }\n"
        "        }\n"
        "      } catch (err) { console.log('Click handler:', err); }\n"
        "    });\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const textContent = content?.find(c => c.type === "text");\n'
        "      if (!textContent) return;\n"
        "      let result;\n"
        "      try { result = JSON.parse(textContent.text); } catch { return; }\n"
        "\n"
        '      if (result.action === "create" || result.action === "update") {\n'
        "        currentVizId = result.id;\n"
        '        document.getElementById("toolbar").style.display = "flex";\n'
        '        const container = document.getElementById("chart-container");\n'
        '        container.innerHTML = \'<div class="loading"><div class="spinner"></div><span>Rendering chart...</span></div>\';\n'
        "        try {\n"
        '          container.innerHTML = "";\n'
        "          await Bokeh.embed.embed_item(result.figure);\n"
        '          let statusText = result.action === "create" ? "Visualization created" : "Visualization updated";\n'
        "          if (result.info) { statusText += ' | ' + result.info.rows + ' rows from ' + result.info.file; }\n"
        '          document.getElementById("status").textContent = statusText;\n'
        "        } catch (err) {\n"
        '          container.innerHTML = \'<div class="error-box"><div class="error-title">Render Error</div>\' + err.message + \'<div class="error-hint">Try a different chart type or check your data columns</div></div>\';\n'
        "        }\n"
        '        const notice = document.getElementById("sample-notice");\n'
        "        if (result.sampled) {\n"
        '          notice.className = "sample-notice";\n'
        '          notice.textContent = "Showing " + result.shown_rows.toLocaleString() + " of " + result.total_rows.toLocaleString() + " data points (sampled for performance)";\n'
        '          notice.style.display = "block";\n'
        '        } else { notice.style.display = "none"; }\n'
        '        document.getElementById("viz-id").textContent = "ID: " + result.id;\n'
        '        document.getElementById("insight-bar").style.display = "none";\n'
        '        document.getElementById("geo-banner").style.display = result.geo ? "block" : "none";\n'
        "      }\n"
        "\n"
        '      if (result.action === "theme_change" && result.figure) {\n'
        '        const container = document.getElementById("chart-container");\n'
        '        container.innerHTML = "";\n'
        "        try { await Bokeh.embed.embed_item(result.figure); } catch (err) {\n"
        '          container.innerHTML = \'<div class="error-box"><div class="error-title">Theme Error</div>\' + err.message + \'</div>\';\n'
        "        }\n"
        "      }\n"
        "\n"
        '      if (result.action === "insight") {\n'
        '        const bar = document.getElementById("insight-bar");\n'
        "        bar.textContent = result.message;\n"
        '        bar.style.display = "block";\n'
        "      }\n"
        "\n"
        '      if (result.action === "export") {\n'
        "        try {\n"
        '          const blob = new Blob([result.data], { type: result.format === "csv" ? "text/csv" : "application/json" });\n'
        "          const url = URL.createObjectURL(blob);\n"
        '          const link = document.createElement("a");\n'
        "          link.href = url;\n"
        "          link.download = result.filename;\n"
        "          link.click();\n"
        "          URL.revokeObjectURL(url);\n"
        "        } catch (err) {\n"
        '          const modal = document.createElement("div");\n'
        '          modal.className = "export-modal";\n'
        "          modal.innerHTML = '<div class=\"export-modal-inner\">' +\n"
        "            '<div style=\"display:flex;justify-content:space-between;margin-bottom:8px;\">' +\n"
        "            '<span>Export Data (' + result.format.toUpperCase() + ')</span>' +\n"
        "            '<button onclick=\"this.closest(\\'.export-modal\\').remove()\" class=\"toolbar-btn\">Close</button></div>' +\n"
        "            '<textarea class=\"export-textarea\">' + result.data.replace(/</g, '&lt;') + '</textarea></div>';\n"
        "          document.body.appendChild(modal);\n"
        "        }\n"
        "      }\n"
        "\n"
        '      if (result.action === "error") {\n'
        '        document.getElementById("chart-container").innerHTML =\n'
        '          \'<div class="error-box"><div class="error-title">Error</div>\' + result.message + \'<div class="error-hint">Check your data format and column names</div></div>\';\n'
        '        document.getElementById("status").textContent = "Error";\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        '    document.getElementById("status").textContent = "Connected - HoloViz + BokehJS ready";\n'
        "  </script>\n"
        "</body>\n</html>"
    )
