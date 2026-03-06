"""Standard Panel app code generator - clean, gallery-quality dashboards."""

import json

import pandas as pd

from .geo import _generate_geo_panel_code
from .multi import _generate_multi_panel_code


def _generate_panel_code(viz: dict) -> str:
    """Generate a clean, focused Panel app matching gallery quality.

    Produces apps with:
    - One main interactive chart (hvPlot)
    - Simple sidebar controls (chart type, axes, color, filters)
    - Clean indicator row (Count, Mean, Min, Max)
    - Data table (Tabulator)
    - Dark FastListTemplate
    """
    if viz["kind"] == "points":
        return _generate_geo_panel_code(viz)
    if viz["kind"] == "multi":
        return _generate_multi_panel_code(viz)

    data_json = json.dumps(viz["data"])
    kind = viz["kind"]
    x_col = viz["x"]
    y_col = viz["y"]
    title = viz["title"]
    color = viz.get("color")

    df_temp = pd.DataFrame(viz["data"])
    n_rows = len(df_temp)
    n_cols = len(df_temp.columns)

    chart_default = kind if kind in (
        "bar", "line", "scatter", "area", "step", "histogram",
        "box", "violin", "kde",
    ) else "scatter"

    L: list[str] = []

    # ---- imports ----
    L.append("import json")
    L.append("import pandas as pd")
    L.append("import numpy as np")
    L.append("import panel as pn")
    L.append("import holoviews as hv")
    L.append("import hvplot.pandas  # noqa: F401")
    L.append("")
    L.append('pn.extension("tabulator", sizing_mode="stretch_width")')
    L.append('hv.extension("bokeh")')
    L.append('hv.renderer("bokeh").theme = "dark_minimal"')
    L.append("")

    # ---- data ----
    escaped_data = json.dumps(data_json)  # double-encode: JSON string inside Python string
    L.append(f"df = pd.DataFrame(json.loads({escaped_data}))")
    L.append("")
    L.append('cat_cols = [c for c in df.columns if df[c].dtype == "object"]')
    L.append("num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]")
    L.append("all_cols = list(df.columns)")
    L.append("")

    # ---- sidebar widgets ----
    L.append("# ==================== Sidebar Controls ====================")
    L.append("chart_type_w = pn.widgets.RadioButtonGroup(")
    L.append('    name="Chart Type",')
    L.append('    options=["scatter", "bar", "line", "area", "histogram", "box", "violin", "kde", "step"],')
    L.append(f'    value="{chart_default}",')
    L.append('    button_type="primary",')
    L.append(")")
    L.append(f'x_w = pn.widgets.Select(name="X Axis", options=all_cols, value="{x_col}")')
    L.append(f'y_w = pn.widgets.Select(name="Y Axis", options=num_cols if num_cols else all_cols, value="{y_col}")')

    if color and color in df_temp.columns:
        L.append(f'color_w = pn.widgets.Select(name="Color By", options=["None"] + cat_cols, value="{color}")')
    else:
        L.append('color_w = pn.widgets.Select(name="Color By", options=["None"] + cat_cols, value="None")')
    L.append("")

    # ---- filters ----
    L.append("# ==================== Filters ====================")
    L.append("filter_widgets = []")
    L.append("_filter_refs = {}")
    L.append("for col in cat_cols:")
    L.append('    uvals = sorted(str(v) for v in df[col].unique()[:50])')
    L.append('    w = pn.widgets.Select(name=col, options=["All"] + uvals, value="All")')
    L.append("    filter_widgets.append(w)")
    L.append("    _filter_refs[col] = w")
    L.append("for col in num_cols:")
    L.append("    cmin, cmax = float(df[col].min()), float(df[col].max())")
    L.append("    if cmin < cmax:")
    L.append("        w = pn.widgets.RangeSlider(")
    L.append('            name=col, start=cmin, end=cmax, value=(cmin, cmax),')
    L.append('            step=round((cmax - cmin) / 100, 6),')
    L.append("        )")
    L.append("        filter_widgets.append(w)")
    L.append("        _filter_refs[col] = w")
    L.append("")

    L.append('reset_btn = pn.widgets.Button(name="Reset Filters", button_type="warning")')
    L.append("")
    L.append("def on_reset(event):")
    L.append("    for col, w in _filter_refs.items():")
    L.append("        if isinstance(w, pn.widgets.Select):")
    L.append('            w.value = "All"')
    L.append("        elif isinstance(w, pn.widgets.RangeSlider):")
    L.append("            w.value = (w.start, w.end)")
    L.append("reset_btn.on_click(on_reset)")
    L.append("")

    # ---- filter helper ----
    L.append("def apply_filters():")
    L.append("    filt = df.copy()")
    L.append("    for col, w in _filter_refs.items():")
    L.append("        val = w.value")
    L.append('        if isinstance(w, pn.widgets.Select) and val != "All":')
    L.append("            filt = filt[filt[col].astype(str) == val]")
    L.append("        elif isinstance(w, pn.widgets.RangeSlider):")
    L.append("            lo, hi = val")
    L.append("            filt = filt[(filt[col] >= lo) & (filt[col] <= hi)]")
    L.append("    return filt")
    L.append("")

    # ---- main reactive function ----
    L.append("# ==================== Main View ====================")
    L.append("def build_view(chart_type, x_val, y_val, color_val, *filter_args):")
    L.append("    filt = apply_filters()")
    L.append("    if filt.empty:")
    L.append('        return pn.pane.Alert("No data matches filters.", alert_type="warning")')
    L.append("")

    # indicators
    L.append('    y_data = pd.to_numeric(filt[y_val], errors="coerce").dropna()')
    L.append("    n = len(filt)")
    L.append("    y_mean = round(float(y_data.mean()), 2) if len(y_data) else 0")
    L.append("    y_min = round(float(y_data.min()), 2) if len(y_data) else 0")
    L.append("    y_max = round(float(y_data.max()), 2) if len(y_data) else 0")
    L.append("")
    L.append('    ikw = dict(default_color="currentcolor", font_size="24px", title_size="11px")')
    L.append("    indicators = pn.FlexBox(")
    L.append('        pn.indicators.Number(name="Count", value=n, format="{value:,}", **ikw),')
    L.append('        pn.indicators.Number(name="Mean", value=y_mean, format="{value:,.2f}", **ikw),')
    L.append('        pn.indicators.Number(name="Min", value=y_min, format="{value:,.2f}", **ikw),')
    L.append('        pn.indicators.Number(name="Max", value=y_max, format="{value:,.2f}", **ikw),')
    L.append("    )")
    L.append("")

    # chart
    L.append('    cc = color_val if color_val != "None" else None')
    L.append("    kw = dict(responsive=True, height=400)")
    L.append("")
    L.append('    if chart_type == "scatter":')
    L.append("        mkw = {**kw, 'x': x_val, 'y': y_val}")
    L.append("        if cc: mkw['c'] = cc")
    L.append("        chart = filt.hvplot.scatter(**mkw)")
    L.append('    elif chart_type in ("bar", "line", "area", "step"):')
    L.append("        mkw = {**kw, 'x': x_val, 'y': y_val}")
    L.append("        if cc: mkw['by'] = cc")
    L.append("        chart = getattr(filt.hvplot, chart_type)(**mkw)")
    L.append('    elif chart_type == "histogram":')
    L.append("        mkw = {**kw, 'y': y_val}")
    L.append("        if cc: mkw['by'] = cc")
    L.append("        chart = filt.hvplot.hist(**mkw)")
    L.append('    elif chart_type in ("box", "violin"):')
    L.append("        fcat = [c for c in filt.columns if filt[c].dtype == 'object']")
    L.append("        mkw = {**kw, 'y': y_val}")
    L.append("        by = x_val if x_val in fcat else cc")
    L.append("        if by: mkw['by'] = by")
    L.append("        chart = getattr(filt.hvplot, chart_type)(**mkw)")
    L.append('    elif chart_type == "kde":')
    L.append("        mkw = {**kw, 'y': y_val}")
    L.append("        if cc: mkw['by'] = cc")
    L.append("        chart = filt.hvplot.kde(**mkw)")
    L.append("    else:")
    L.append("        chart = filt.hvplot.scatter(x=x_val, y=y_val, responsive=True, height=400)")
    L.append("")
    L.append("    chart_pane = pn.pane.HoloViews(chart, sizing_mode='stretch_both', min_height=400)")
    L.append("")

    # table
    L.append("    table = pn.widgets.Tabulator(")
    L.append('        filt, show_index=False, page_size=15, pagination="remote",')
    L.append('        sizing_mode="stretch_width", height=250, theme="midnight",')
    L.append("    )")
    L.append("")

    L.append("    return pn.Column(")
    L.append("        indicators,")
    L.append("        chart_pane,")
    L.append('        pn.pane.Markdown("### Data"),')
    L.append("        table,")
    L.append("        sizing_mode='stretch_width',")
    L.append("    )")
    L.append("")

    # ---- bind ----
    L.append("# ==================== Bind ====================")
    L.append("main_view = pn.bind(")
    L.append("    build_view,")
    L.append("    chart_type_w, x_w, y_w, color_w,")
    L.append("    *[w for w in filter_widgets],")
    L.append(")")
    L.append("")

    # ---- sidebar ----
    L.append("# ==================== Sidebar ====================")
    L.append("sidebar_items = [")
    L.append(f'    pn.pane.Markdown("### {title}\\n\\n'
             f'**{n_rows:,}** rows | **{n_cols}** columns"),')
    L.append("    pn.layout.Divider(),")
    L.append('    pn.pane.Markdown("**Chart Type**"),')
    L.append("    chart_type_w,")
    L.append("    x_w, y_w, color_w,")
    L.append("]")
    L.append("if filter_widgets:")
    L.append('    sidebar_items.append(pn.layout.Divider())')
    L.append('    sidebar_items.append(pn.pane.Markdown("**Filters**"))')
    L.append("    sidebar_items.extend(filter_widgets)")
    L.append("    sidebar_items.append(reset_btn)")
    L.append("")

    # ---- template ----
    L.append("# ==================== Template ====================")
    L.append("template = pn.template.FastListTemplate(")
    L.append(f'    title="{title}",')
    L.append("    sidebar=sidebar_items,")
    L.append("    main=[pn.panel(main_view)],")
    L.append('    theme="dark",')
    L.append('    accent_base_color="#818cf8",')
    L.append('    header_background="#1e293b",')
    L.append(")")
    L.append("template.servable()")

    return "\n".join(L)
