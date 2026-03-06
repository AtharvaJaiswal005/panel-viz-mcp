"""MCP Apps resource: dashboard HTML."""

from fastmcp.server.apps import AppConfig, ResourceCSP

from ..app import mcp
from ..cdn import BOKEH_SCRIPTS
from ..constants import DASHBOARD_URI, MCP_APPS_SDK_URL
from ..themes import CSS_THEME_VARS as _CSS_THEME_VARS


@mcp.resource(
    DASHBOARD_URI,
    app=AppConfig(
        csp=ResourceCSP(resource_domains=[
            "https://cdn.bokeh.org", "https://unpkg.com",
            "https://*.basemaps.cartocdn.com", "https://*.tile.openstreetmap.org",
        ]),
    ),
)
def dashboard_view() -> str:
    """Interactive dashboard with chart, table, statistics, and filter widgets."""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="color-scheme" content="light dark">\n'
        "  <title>Panel Dashboard</title>\n"
        f'{BOKEH_SCRIPTS}\n'
        "  <style>\n"
        "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
        f'{_CSS_THEME_VARS}\n'
        "    body {\n"
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\n'
        "      background: var(--bg-body); color: var(--text-primary); padding: 12px;\n"
        "    }\n"
        "    .dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }\n"
        "    .dashboard-title { font-size: 18px; font-weight: 600; }\n"
        "    .dash-toolbar { display: flex; gap: 6px; }\n"
        "    .toolbar-btn {\n"
        "      padding: 3px 10px; border-radius: 4px; border: 1px solid var(--btn-border);\n"
        "      background: var(--btn-bg); color: var(--text-secondary); cursor: pointer; font-size: 11px;\n"
        "    }\n"
        "    .toolbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "    .dashboard-layout { display: flex; gap: 12px; }\n"
        "    .dashboard-main { flex: 1; min-width: 0; overflow: hidden; }\n"
        "    .filter-sidebar {\n"
        "      width: 180px; flex-shrink: 0; overflow: hidden;\n"
        "      background: var(--bg-card); border: 1px solid var(--border);\n"
        "      border-radius: 8px; padding: 10px;\n"
        "      max-height: 500px; overflow-y: auto;\n"
        "    }\n"
        "    .filter-range { max-width: 100%; }\n"
        "    .filter-title {\n"
        "      font-size: 12px; color: var(--text-secondary); text-transform: uppercase;\n"
        "      letter-spacing: 0.5px; margin-bottom: 12px; padding-bottom: 6px;\n"
        "      border-bottom: 1px solid var(--border);\n"
        "    }\n"
        "    .filter-group { margin-bottom: 12px; }\n"
        "    .filter-label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }\n"
        "    .filter-select, .filter-range {\n"
        "      width: 100%; padding: 4px 8px; border-radius: 4px;\n"
        "      border: 1px solid var(--btn-border); background: var(--input-bg); color: var(--text-primary);\n"
        "      font-size: 12px;\n"
        "    }\n"
        "    .filter-range-labels { display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); }\n"
        "    .filter-btn {\n"
        "      width: 100%; padding: 6px; border-radius: 6px; border: 1px solid var(--accent);\n"
        "      background: var(--accent-bg); color: var(--accent); cursor: pointer;\n"
        "      font-size: 12px; margin-top: 8px;\n"
        "    }\n"
        "    .filter-btn:hover { opacity: 0.8; }\n"
        "    .filter-status { font-size: 11px; color: var(--text-muted); margin-top: 8px; text-align: center; }\n"
        "    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }\n"
        "    .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }\n"
        "    .card-title { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }\n"
        "    #chart { width: 100%; min-height: 280px; }\n"
        "    .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }\n"
        "    .stat-item { text-align: center; padding: 8px; background: var(--bg-surface); border-radius: 6px; }\n"
        "    .stat-value { font-size: 20px; font-weight: 700; color: var(--stat-value); }\n"
        "    .stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }\n"
        "    .table-wrap { max-height: 250px; overflow-y: auto; }\n"
        "    .table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }\n"
        "    .table-count { font-size: 11px; color: var(--text-muted); }\n"
        "    table { width: 100%; border-collapse: collapse; font-size: 12px; }\n"
        "    th { position: sticky; top: 0; background: var(--table-header-bg); padding: 6px 8px; text-align: left; color: var(--text-secondary); border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; }\n"
        "    th:hover { color: var(--accent); }\n"
        "    td { padding: 5px 8px; border-bottom: 1px solid var(--border); }\n"
        "    tr:hover td { background: var(--accent-bg); }\n"
        "    #status { font-size: 11px; color: var(--text-muted); text-align: center; padding: 4px; }\n"
        "  </style>\n"
        '</head>\n<body class="theme-dark">\n'
        '  <div class="dash-header">\n'
        '    <div class="dashboard-title" id="dash-title">Loading dashboard...</div>\n'
        '    <div class="dash-toolbar">\n'
        '      <button class="toolbar-btn" id="theme-btn" onclick="toggleTheme()">Light Mode</button>\n'
        '      <button class="toolbar-btn" id="panel-btn" onclick="openInPanel()">Open in Panel</button>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div class="dashboard-layout">\n'
        '    <div class="dashboard-main">\n'
        '      <div class="grid">\n'
        '        <div class="card" style="grid-column: 1 / -1;">\n'
        '          <div class="card-title">Chart</div>\n'
        '          <div id="chart"><div class="loading"><div class="spinner"></div><span>Preparing chart...</span></div></div>\n'
        "        </div>\n"
        '        <div class="card">\n'
        '          <div class="card-title">Statistics</div>\n'
        '          <div class="stats-grid" id="stats"><div class="loading"><div class="spinner"></div></div></div>\n'
        "        </div>\n"
        '        <div class="card">\n'
        '          <div class="card-title">Data Table</div>\n'
        '          <div class="table-wrap" id="table"><div class="loading"><div class="spinner"></div></div></div>\n'
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        '    <div class="filter-sidebar" id="filter-sidebar">\n'
        '      <div class="filter-title">Filters</div>\n'
        '      <div class="filter-status">Waiting for data...</div>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div id="status">panel-viz-mcp dashboard ready</div>\n'
        "\n"
        '  <script type="module">\n'
        f'    import {{ App }} from "{MCP_APPS_SDK_URL}";\n'
        '    const app = new App({ name: "Panel Dashboard", version: "0.2.0" });\n'
        "    let currentVizId = null;\n"
        '    let currentTheme = "dark";\n'
        "\n"
        "    window.toggleTheme = async () => {\n"
        '      currentTheme = currentTheme === "dark" ? "light" : "dark";\n'
        '      document.body.className = "theme-" + currentTheme;\n'
        '      document.getElementById("theme-btn").textContent = currentTheme === "dark" ? "Light Mode" : "Dark Mode";\n'
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
        '              document.getElementById("chart").innerHTML = "";\n'
        "              await Bokeh.embed.embed_item(r.figure);\n"
        "            }\n"
        "          }\n"
        "        } catch (err) { console.log('Theme switch:', err); }\n"
        "      }\n"
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
        "    function buildFilterWidgets(config) {\n"
        '      const sidebar = document.getElementById("filter-sidebar");\n'
        "      sidebar.innerHTML = '<div class=\"filter-title\">Filters</div>';\n"
        "      if (!config || config.length === 0) {\n"
        "        sidebar.innerHTML += '<div class=\"filter-status\">No filterable columns</div>';\n"
        "        return;\n"
        "      }\n"
        "      config.forEach(w => {\n"
        '        const group = document.createElement("div");\n'
        '        group.className = "filter-group";\n'
        "        group.innerHTML = '<div class=\"filter-label\">' + w.column + '</div>';\n"
        '        if (w.type === "select") {\n'
        "          let html = '<select class=\"filter-select\" data-column=\"' + w.column + '\">';\n"
        "          html += '<option value=\"__all__\">All</option>';\n"
        "          w.options.forEach(opt => { html += '<option value=\"' + opt + '\">' + opt + '</option>'; });\n"
        "          html += '</select>';\n"
        "          group.innerHTML += html;\n"
        '        } else if (w.type === "range") {\n'
        "          group.innerHTML +=\n"
        "            '<input type=\"range\" class=\"filter-range\" data-column=\"' + w.column + '\"' +\n"
        "            ' min=\"' + w.min + '\" max=\"' + w.max + '\" step=\"' + w.step + '\"' +\n"
        "            ' value=\"' + w.min + '\" data-role=\"min\">' +\n"
        "            '<input type=\"range\" class=\"filter-range\" data-column=\"' + w.column + '\"' +\n"
        "            ' min=\"' + w.min + '\" max=\"' + w.max + '\" step=\"' + w.step + '\"' +\n"
        "            ' value=\"' + w.max + '\" data-role=\"max\">' +\n"
        "            '<div class=\"filter-range-labels\">' +\n"
        "            '<span id=\"range-min-' + w.column + '\">' + w.min + '</span>' +\n"
        "            '<span id=\"range-max-' + w.column + '\">' + w.max + '</span></div>';\n"
        "        }\n"
        "        sidebar.appendChild(group);\n"
        "      });\n"
        '      const applyBtn = document.createElement("button");\n'
        '      applyBtn.className = "filter-btn";\n'
        '      applyBtn.textContent = "Apply Filters";\n'
        "      applyBtn.onclick = applyFilters;\n"
        "      sidebar.appendChild(applyBtn);\n"
        '      const resetBtn = document.createElement("button");\n'
        '      resetBtn.className = "filter-btn";\n'
        '      resetBtn.textContent = "Reset";\n'
        '      resetBtn.style.marginTop = "4px";\n'
        "      resetBtn.onclick = resetFilters;\n"
        "      sidebar.appendChild(resetBtn);\n"
        "      sidebar.innerHTML += '<div id=\"filter-status\" class=\"filter-status\"></div>';\n"
        "      sidebar.querySelectorAll('.filter-range').forEach(input => {\n"
        "        input.addEventListener('input', () => {\n"
        "          const col = input.dataset.column;\n"
        "          const role = input.dataset.role;\n"
        "          const el = document.getElementById('range-' + role + '-' + col);\n"
        "          if (el) el.textContent = input.value;\n"
        "        });\n"
        "      });\n"
        "    }\n"
        "\n"
        "    async function applyFilters() {\n"
        "      if (!currentVizId) return;\n"
        "      const filters = {};\n"
        "      document.querySelectorAll('.filter-select').forEach(sel => {\n"
        "        filters[sel.dataset.column] = sel.value;\n"
        "      });\n"
        "      const rangeByCol = {};\n"
        "      document.querySelectorAll('.filter-range').forEach(input => {\n"
        "        const col = input.dataset.column;\n"
        "        if (!rangeByCol[col]) rangeByCol[col] = {};\n"
        "        rangeByCol[col][input.dataset.role] = parseFloat(input.value);\n"
        "      });\n"
        "      for (const [col, range] of Object.entries(rangeByCol)) {\n"
        "        filters[col] = [range.min, range.max];\n"
        "      }\n"
        '      const statusEl = document.getElementById("filter-status");\n'
        '      if (statusEl) statusEl.textContent = "Filtering...";\n'
        '      document.getElementById("chart").innerHTML = \'<div class="loading"><div class="spinner"></div><span>Applying filters...</span></div>\';\n'
        "      try {\n"
        "        const response = await app.callServerTool({\n"
        '          name: "apply_filter",\n'
        "          arguments: { viz_id: currentVizId, filters: filters },\n"
        "        });\n"
        '        const t = response?.content?.find(c => c.type === "text");\n'
        "        if (t) {\n"
        "          const r = JSON.parse(t.text);\n"
        '          if (r.action === "filter_result") {\n'
        "            if (r.empty) {\n"
        '              document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">No Results</div>No data matches the current filters<div class="error-hint">Try adjusting or resetting filters</div></div>\';\n'
        '              if (statusEl) statusEl.textContent = "0 rows match";\n'
        "            } else {\n"
        '              document.getElementById("chart").innerHTML = "";\n'
        "              try { await Bokeh.embed.embed_item(r.figure); } catch (embedErr) {\n"
        '                document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Render Error</div>\' + embedErr.message + \'</div>\';\n'
        "              }\n"
        "              renderStats(r.stats);\n"
        "              renderTable(r.table);\n"
        '              if (statusEl) statusEl.textContent = r.filtered_rows.toLocaleString() + " rows";\n'
        "            }\n"
        '          } else if (r.action === "error") {\n'
        '            document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Filter Error</div>\' + r.message + \'</div>\';\n'
        '            if (statusEl) statusEl.textContent = "Error";\n'
        "          }\n"
        "        }\n"
        "      } catch (err) {\n"
        '        document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Connection Error</div>Failed to apply filters</div>\';\n'
        '        if (statusEl) statusEl.textContent = "Filter error";\n'
        "      }\n"
        "    }\n"
        "\n"
        "    function resetFilters() {\n"
        "      document.querySelectorAll('.filter-select').forEach(sel => { sel.value = '__all__'; });\n"
        "      document.querySelectorAll('.filter-range').forEach(input => {\n"
        "        input.value = input.dataset.role === 'min' ? input.min : input.max;\n"
        "        const el = document.getElementById('range-' + input.dataset.role + '-' + input.dataset.column);\n"
        "        if (el) el.textContent = input.value;\n"
        "      });\n"
        "      applyFilters();\n"
        "    }\n"
        "\n"
        "    function renderStats(stats) {\n"
        '      const statsEl = document.getElementById("stats");\n'
        "      statsEl.innerHTML = Object.entries(stats).map(([k,v]) =>\n"
        "        '<div class=\"stat-item\"><div class=\"stat-value\">' +\n"
        "        (typeof v === 'number' && v >= 1000 ? (v/1000).toFixed(1)+'k' : v) +\n"
        "        '</div><div class=\"stat-label\">' + k + '</div></div>'\n"
        "      ).join('');\n"
        "    }\n"
        "\n"
        "    let currentSortCol = -1, currentSortAsc = true;\n"
        "    let currentTableData = null;\n"
        "\n"
        "    function renderTable(table) {\n"
        "      currentTableData = table;\n"
        '      const tableEl = document.getElementById("table");\n'
        "      const total = table.total || table.rows.length;\n"
        "      const showing = table.rows.length;\n"
        '      let html = \'<div class="table-header"><span class="table-count">\' +\n'
        "        (total > showing ? 'Showing ' + showing + ' of ' + total.toLocaleString() + ' rows' : showing + ' rows') +\n"
        "        '</span></div>';\n"
        '      html += "<table><thead><tr>" +\n'
        '        table.columns.map((c, i) => \'<th onclick="sortTable(\'+i+\')">\'+c+\' <span style="opacity:0.4">&#8597;</span></th>\').join("") +\n'
        '        "</tr></thead><tbody>" +\n'
        "        table.rows.map(row => '<tr>' + row.map(v => {\n"
        "          const n = Number(v);\n"
        "          return '<td' + ((!isNaN(n) && v !== '' && v !== null) ? ' style=\"text-align:right\"' : '') + '>' +\n"
        "            ((!isNaN(n) && v !== '' && v !== null) ? n.toLocaleString() : (v === null ? '' : v)) + '</td>';\n"
        "        }).join('') + '</tr>').join('') +\n"
        '        "</tbody></table>";\n'
        "      tableEl.innerHTML = html;\n"
        "    }\n"
        "\n"
        "    window.sortTable = (colIdx) => {\n"
        "      if (!currentTableData) return;\n"
        "      if (currentSortCol === colIdx) { currentSortAsc = !currentSortAsc; }\n"
        "      else { currentSortCol = colIdx; currentSortAsc = true; }\n"
        "      const sorted = [...currentTableData.rows].sort((a, b) => {\n"
        "        let va = a[colIdx], vb = b[colIdx];\n"
        "        const na = Number(va), nb = Number(vb);\n"
        "        if (!isNaN(na) && !isNaN(nb)) return currentSortAsc ? na - nb : nb - na;\n"
        "        va = String(va || ''); vb = String(vb || '');\n"
        "        return currentSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);\n"
        "      });\n"
        "      renderTable({...currentTableData, rows: sorted});\n"
        "    };\n"
        "\n"
        "    app.ontoolresult = async ({ content }) => {\n"
        '      const text = content?.find(c => c.type === "text");\n'
        "      if (!text) return;\n"
        "      let r;\n"
        "      try { r = JSON.parse(text.text); } catch { return; }\n"
        "\n"
        '      if (r.action === "dashboard") {\n'
        "        currentVizId = r.id;\n"
        '        document.getElementById("dash-title").textContent = r.title;\n'
        '        document.getElementById("chart").innerHTML = "";\n'
        "        try { await Bokeh.embed.embed_item(r.figure); } catch (err) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Chart Error</div>\' + err.message + \'</div>\';\n'
        "        }\n"
        "        renderStats(r.stats);\n"
        "        renderTable(r.table);\n"
        "        if (r.widget_config) buildFilterWidgets(r.widget_config);\n"
        "        let statusText = 'Dashboard loaded | ID: ' + r.id;\n"
        "        if (r.sampled) { statusText += ' | Showing ' + r.shown_rows.toLocaleString() + ' of ' + r.total_rows.toLocaleString() + ' points (sampled)'; }\n"
        '        document.getElementById("status").textContent = statusText;\n'
        "      }\n"
        "\n"
        '      if (r.action === "filter_result") {\n'
        '        const statusEl = document.getElementById("filter-status");\n'
        "        if (r.empty) {\n"
        '          document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">No Results</div>No data matches filters</div>\';\n'
        '          if (statusEl) statusEl.textContent = "0 rows match";\n'
        "        } else {\n"
        '          document.getElementById("chart").innerHTML = "";\n'
        "          try { await Bokeh.embed.embed_item(r.figure); } catch (err) {\n"
        '            document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Render Error</div>\' + err.message + \'</div>\';\n'
        "          }\n"
        "          renderStats(r.stats);\n"
        "          renderTable(r.table);\n"
        '          if (statusEl) statusEl.textContent = r.filtered_rows.toLocaleString() + " rows";\n'
        "        }\n"
        "      }\n"
        "\n"
        '      if (r.action === "error") {\n'
        '        document.getElementById("chart").innerHTML = \'<div class="error-box"><div class="error-title">Error</div>\' + r.message + \'</div>\';\n'
        "      }\n"
        "    };\n"
        "\n"
        "    await app.connect();\n"
        "  </script>\n"
        "</body>\n</html>"
    )
