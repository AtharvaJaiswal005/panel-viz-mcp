"""Multi-chart Panel app code generator with cross-filtering."""

import json

import pandas as pd


def _has_geo_chart(charts: list) -> bool:
    """Check if any chart config uses geographic map kind."""
    return any(c.get("kind") == "points" for c in charts)


def _generate_multi_panel_code(viz: dict) -> str:
    """Generate a clean Panel app with cross-filtered multi-chart grid."""
    data_json = json.dumps(viz["data"])
    title = viz["title"]
    charts_json = json.dumps(viz["charts"])

    df_temp = pd.DataFrame(viz["data"])
    n_rows = len(df_temp)
    n_cols_count = len(df_temp.columns)
    has_geo = _has_geo_chart(viz.get("charts", []))

    L: list[str] = []

    # ---- imports ----
    L.append("import json")
    L.append("import pandas as pd")
    L.append("import panel as pn")
    L.append("import holoviews as hv")
    L.append("import hvplot.pandas  # noqa: F401")
    if has_geo:
        L.append("import geoviews as gv")
    L.append("")
    L.append('pn.extension("tabulator", "gridstack", sizing_mode="stretch_width")')
    L.append('hv.extension("bokeh")')
    L.append('hv.renderer("bokeh").theme = "dark_minimal"')
    L.append("")

    # ---- data ----
    escaped_data = json.dumps(data_json)  # double-encode for safe embedding
    escaped_charts = json.dumps(charts_json)
    L.append(f"df = pd.DataFrame(json.loads({escaped_data}))")
    L.append(f"charts_config = json.loads({escaped_charts})")
    L.append("")
    L.append('cat_cols = [c for c in df.columns if df[c].dtype == "object"]')
    L.append("num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]")
    L.append("")

    # ---- sidebar filters ----
    L.append("# ==================== Filters ====================")
    L.append("filter_widgets = {}")
    L.append("for col in cat_cols:")
    L.append('    uvals = sorted(str(v) for v in df[col].unique()[:50])')
    L.append('    filter_widgets[col] = pn.widgets.Select(')
    L.append('        name=col, options=["All"] + uvals, value="All",')
    L.append("    )")
    L.append('reset_btn = pn.widgets.Button(name="Reset", button_type="warning")')
    L.append("")
    L.append("def on_reset(event):")
    L.append("    for w in filter_widgets.values():")
    L.append('        w.value = "All"')
    L.append("reset_btn.on_click(on_reset)")
    L.append("")

    L.append("def apply_filters():")
    L.append("    filt = df.copy()")
    L.append("    for col, w in filter_widgets.items():")
    L.append('        if w.value != "All":')
    L.append("            filt = filt[filt[col].astype(str) == w.value]")
    L.append("    return filt")
    L.append("")

    # ---- reactive main ----
    L.append("# ==================== Main View ====================")
    L.append("def build_main(*args):")
    L.append("    filt = apply_filters()")
    L.append("    if filt.empty:")
    L.append('        return pn.pane.Alert("No data matches filters.", alert_type="warning")')
    L.append("")

    # indicators
    L.append("    fcat = [c for c in filt.columns if filt[c].dtype == 'object']")
    L.append("    y_cols = [cfg.get('y') for cfg in charts_config if cfg.get('y') in filt.columns")
    L.append("             and pd.api.types.is_numeric_dtype(filt[cfg.get('y', '')])]")
    L.append("    y_col = y_cols[0] if y_cols else (num_cols[0] if num_cols else None)")
    L.append('    ikw = dict(default_color="currentcolor", font_size="24px", title_size="11px")')
    L.append("    ind_items = [")
    L.append('        pn.indicators.Number(name="Count", value=len(filt), format="{value:,}", **ikw),')
    L.append("    ]")
    L.append("    if y_col:")
    L.append('        ydata = pd.to_numeric(filt[y_col], errors="coerce").dropna()')
    L.append("        if len(ydata):")
    L.append('            ind_items.append(pn.indicators.Number(name="Mean",')
    L.append('                value=round(float(ydata.mean()), 2), format="{value:,.2f}", **ikw))')
    L.append('            ind_items.append(pn.indicators.Trend(name="Trend",')
    L.append('                data={"y": list(ydata.values[-50:])}, height=60, width=180, plot_type="area"))')
    L.append("    indicators = pn.FlexBox(*ind_items)")
    L.append("")

    # charts - with geo map support
    L.append("    ls = hv.link_selections.instance()")
    L.append("    plots = []")
    L.append("    geo_indices = []  # track which plots are geo maps")
    L.append("    for i, cfg in enumerate(charts_config):")
    L.append("        kind = cfg.get('kind', 'bar')")
    L.append("        cx, cy = cfg.get('x', ''), cfg.get('y', '')")
    L.append("        cc = cfg.get('color')")
    L.append("        ct = cfg.get('title', '')")
    L.append("        if cx not in filt.columns or cy not in filt.columns:")
    L.append("            continue")
    L.append("        bkw = {'responsive': True, 'height': 320, 'title': ct}")
    L.append('        if kind == "points":')
    L.append("            bkw['x'], bkw['y'] = cx, cy")
    L.append("            bkw['geo'] = True")
    L.append("            if cc and cc in filt.columns: bkw['color'] = cc")
    L.append("            plots.append(filt.hvplot.points(**bkw))")
    L.append("            geo_indices.append(len(plots) - 1)")
    L.append('        elif kind == "scatter":')
    L.append("            bkw['x'], bkw['y'] = cx, cy")
    L.append("            if cc and cc in filt.columns: bkw['c'] = cc")
    L.append("            plots.append(filt.hvplot.scatter(**bkw))")
    L.append('        elif kind in ("bar", "line", "area", "step"):')
    L.append("            bkw['x'], bkw['y'] = cx, cy")
    L.append("            if cc and cc in fcat: bkw['by'] = cc")
    L.append("            plots.append(getattr(filt.hvplot, kind)(**bkw))")
    L.append('        elif kind == "histogram":')
    L.append("            bkw['y'] = cy")
    L.append("            if cc and cc in fcat: bkw['by'] = cc")
    L.append("            plots.append(filt.hvplot.hist(**bkw))")
    L.append('        elif kind in ("box", "violin"):')
    L.append("            bkw['y'] = cy")
    L.append("            by = cx if cx in fcat else cc")
    L.append("            if by and by in filt.columns: bkw['by'] = by")
    L.append("            plots.append(getattr(filt.hvplot, kind)(**bkw))")
    L.append("        else:")
    L.append("            bkw['x'], bkw['y'] = cx, cy")
    L.append("            plots.append(filt.hvplot.bar(**bkw))")
    L.append("")
    L.append("    if not plots:")
    L.append('        return pn.pane.Alert("No valid charts.", alert_type="warning")')
    L.append("")

    # link_selections + tile overlay for geo charts
    L.append("    try:")
    L.append("        linked = ls(hv.Layout(plots).cols(min(len(plots), 2)))")
    L.append("        # Overlay tiles on geo charts after link_selections")
    if has_geo:
        L.append("        if geo_indices:")
        L.append("            tiles = gv.tile_sources.EsriImagery.opts(alpha=0.5)")
        L.append("            for gi in geo_indices:")
        L.append("                try:")
        L.append("                    linked[gi] = tiles * linked[gi]")
        L.append("                except Exception:")
        L.append("                    pass")
    L.append("        chart_layout = linked")
    L.append("    except Exception:")
    L.append("        chart_layout = hv.Layout(plots).cols(min(len(plots), 2))")
    L.append("")
    L.append("    chart_pane = pn.pane.HoloViews(chart_layout, sizing_mode='stretch_both', min_height=400)")
    L.append("")

    # GridStack
    L.append("    try:")
    L.append("        grid = pn.GridStack(sizing_mode='stretch_both', min_height=500)")
    L.append("        for i, p in enumerate(plots[:4]):")
    L.append("            r, c = divmod(i, 2)")
    L.append("            grid[r*3:(r+1)*3, c*6:(c+1)*6] = pn.pane.HoloViews(p, sizing_mode='stretch_both')")
    L.append("        grid_pane = grid")
    L.append("    except Exception:")
    L.append("        grid_pane = chart_pane")
    L.append("")

    # table
    L.append("    table = pn.widgets.Tabulator(")
    L.append('        filt, show_index=False, page_size=15, pagination="remote",')
    L.append('        sizing_mode="stretch_width", height=250, theme="midnight",')
    L.append("    )")
    L.append("")
    L.append("    return pn.Column(")
    L.append("        indicators,")
    L.append("        pn.Tabs(('Charts', chart_pane), ('Grid', grid_pane), ('Data', table), dynamic=True),")
    L.append("        sizing_mode='stretch_width',")
    L.append("    )")
    L.append("")

    # ---- bind ----
    L.append("main_view = pn.bind(build_main, *filter_widgets.values())")
    L.append("")

    # ---- sidebar ----
    L.append("# ==================== Sidebar ====================")
    L.append("sidebar_items = [")
    L.append(f'    pn.pane.Markdown("### {title}\\n\\n'
             f'**{n_rows:,}** rows | **{n_cols_count}** columns"),')
    L.append("]")
    L.append("if filter_widgets:")
    L.append("    sidebar_items.append(pn.layout.Divider())")
    L.append('    sidebar_items.append(pn.pane.Markdown("**Filters**"))')
    L.append("    sidebar_items.extend(filter_widgets.values())")
    L.append("    sidebar_items.append(reset_btn)")
    L.append("")

    # ---- template ----
    L.append("pn.template.FastListTemplate(")
    L.append(f'    title="{title}",')
    L.append("    sidebar=sidebar_items,")
    L.append("    main=[pn.panel(main_view)],")
    L.append('    theme="dark",')
    L.append('    accent_base_color="#818cf8",')
    L.append('    header_background="#1e293b",')
    L.append(").servable()")

    return "\n".join(L)
