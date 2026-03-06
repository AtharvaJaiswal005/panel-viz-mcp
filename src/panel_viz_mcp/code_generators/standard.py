"""Standard Panel app code generator - clean, gallery-quality dashboards."""

import json

import pandas as pd

from .geo import _generate_geo_panel_code
from .multi import _generate_multi_panel_code


def _generate_candlestick_panel_code(viz: dict) -> str:
    """Generate a Panel dashboard with candlestick chart + donut pie + styled table."""
    data_json = json.dumps(viz["data"])
    x_col = viz["x"]
    y_col = viz["y"]
    title = viz["title"]
    color = viz.get("color")

    df_temp = pd.DataFrame(viz["data"])

    # Auto-detect OHLC columns
    col_map = {c.lower(): c for c in df_temp.columns}
    o_col = col_map.get("open", "Open")
    h_col = col_map.get("high", "High")
    l_col = col_map.get("low", "Low")
    c_col = col_map.get("close", "Close")

    # Detect grouping column for pie chart
    pie_group = None
    if color and color in df_temp.columns and df_temp[color].dtype == "object":
        pie_group = color
    elif x_col in df_temp.columns and df_temp[x_col].dtype == "object":
        pie_group = x_col

    n_rows = len(df_temp)
    n_cols = len(df_temp.columns)

    escaped_data = json.dumps(data_json)

    L: list[str] = []

    # ---- imports ----
    L.append("import json")
    L.append("import math")
    L.append("import pandas as pd")
    L.append("import numpy as np")
    L.append("import panel as pn")
    L.append("from bokeh.plotting import figure as bokeh_figure")
    L.append("from bokeh.models import ColumnDataSource, FixedTicker, HoverTool")
    L.append("from bokeh.transform import cumsum")
    L.append("from bokeh.palettes import Category10, Category20")
    L.append("")
    L.append('pn.extension("tabulator", sizing_mode="stretch_width")')
    L.append("")

    # ---- data ----
    L.append(f"df = pd.DataFrame(json.loads({escaped_data}))")
    L.append("")
    L.append('cat_cols = [c for c in df.columns if df[c].dtype == "object"]')
    L.append("num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]")
    L.append("")

    # ---- candlestick builder ----
    L.append("# ==================== Candlestick Chart ====================")
    L.append("def build_candlestick(filt):")
    L.append(f"    o_col, h_col, l_col, c_col = '{o_col}', '{h_col}', '{l_col}', '{c_col}'")
    L.append("    tmp = filt.copy()")
    L.append("    tmp['_idx'] = range(len(tmp))")
    L.append("    tmp['_up'] = tmp[c_col] >= tmp[o_col]")
    L.append("    inc = tmp[tmp['_up']]")
    L.append("    dec = tmp[~tmp['_up']]")
    L.append("    fig = bokeh_figure(")
    L.append(f"        title='{title}',")
    L.append("        height=420, sizing_mode='stretch_width',")
    L.append("        tools='pan,wheel_zoom,box_zoom,reset',")
    L.append("    )")
    L.append("    fig.segment(x0='_idx', y0=l_col, x1='_idx', y1=h_col, source=inc, color='#4ade80')")
    L.append("    fig.segment(x0='_idx', y0=l_col, x1='_idx', y1=h_col, source=dec, color='#f87171')")
    L.append("    fig.vbar(x='_idx', width=0.6, top=c_col, bottom=o_col, source=inc,")
    L.append("             fill_color='#4ade80', line_color='#4ade80')")
    L.append("    fig.vbar(x='_idx', width=0.6, top=o_col, bottom=c_col, source=dec,")
    L.append("             fill_color='#f87171', line_color='#f87171')")
    # X-axis labels
    L.append(f"    if '{x_col}' in tmp.columns:")
    L.append(f"        labels = tmp['{x_col}'].astype(str).tolist()")
    L.append("        step = max(1, len(labels) // 15)")
    L.append("        overrides = {i: labels[i] for i in range(0, len(labels), step)}")
    L.append("        fig.xaxis[0].ticker = FixedTicker(ticks=list(overrides.keys()))")
    L.append("        fig.xaxis[0].major_label_overrides = overrides")
    L.append("        fig.xaxis[0].major_label_orientation = 0.8")
    # Hover
    L.append("    hover = HoverTool(tooltips=[")
    L.append(f"        ('{x_col}', '@{{{x_col}}}'),")
    L.append(f"        ('Open', '@{{{o_col}}}{{0,0.[00]}}'),")
    L.append(f"        ('High', '@{{{h_col}}}{{0,0.[00]}}'),")
    L.append(f"        ('Low', '@{{{l_col}}}{{0,0.[00]}}'),")
    L.append(f"        ('Close', '@{{{c_col}}}{{0,0.[00]}}'),")
    L.append("    ])")
    L.append("    fig.add_tools(hover)")
    # Theme
    L.append("    fig.background_fill_alpha = 0")
    L.append("    fig.border_fill_alpha = 0")
    L.append("    fig.outline_line_alpha = 0")
    L.append("    for ax in fig.axis:")
    L.append("        ax.axis_label_text_color = '#94a3b8'")
    L.append("        ax.major_label_text_color = '#94a3b8'")
    L.append("        ax.major_tick_line_color = '#475569'")
    L.append("        ax.minor_tick_line_color = None")
    L.append("        ax.axis_line_color = '#475569'")
    L.append("    for g in fig.grid:")
    L.append("        g.grid_line_color = '#334155'")
    L.append("        g.grid_line_alpha = 0.5")
    L.append("    if fig.title:")
    L.append("        fig.title.text_color = '#e2e8f0'")
    L.append("        fig.title.text_font_size = '14px'")
    L.append("    return fig")
    L.append("")

    # ---- pie chart builder ----
    L.append("# ==================== Pie Chart ====================")
    L.append("def build_pie(filt, y_val, group_col=None):")
    L.append("    if group_col and group_col in filt.columns:")
    L.append("        agg = filt.groupby(group_col)[y_val].sum().reset_index()")
    L.append("    else:")
    L.append("        agg = filt.head(20)[[filt.columns[0], y_val]].copy()")
    L.append("        group_col = filt.columns[0]")
    L.append("    agg = agg.sort_values(y_val, ascending=False).head(15)")
    L.append("    agg['angle'] = agg[y_val] / agg[y_val].sum() * 2 * math.pi")
    L.append("    agg['pct'] = (agg[y_val] / agg[y_val].sum() * 100).round(1)")
    L.append("    n = len(agg)")
    L.append("    palette = Category20[20] if n > 10 else Category10[max(3, min(n, 10))]")
    L.append("    agg['color'] = [palette[i % len(palette)] for i in range(n)]")
    L.append("    source = ColumnDataSource(agg)")
    L.append("    total = agg[y_val].sum()")
    L.append("    fig = bokeh_figure(")
    L.append("        title=f'Portfolio Total: {total:,.0f}',")
    L.append("        toolbar_location=None,")
    L.append("        tools='hover',")
    L.append("        tooltips=f'@{group_col}: @{y_val}{{0,0}} (@pct%)',")
    L.append("        x_range=(-0.5, 1.0),")
    L.append("        height=350, width=380,")
    L.append("    )")
    L.append("    fig.annular_wedge(")
    L.append("        x=0, y=1, inner_radius=0.15, outer_radius=0.4,")
    L.append("        start_angle=cumsum('angle', include_zero=True),")
    L.append("        end_angle=cumsum('angle'),")
    L.append("        line_color='white', line_width=2,")
    L.append("        fill_color='color',")
    L.append("        legend_field=group_col,")
    L.append("        source=source,")
    L.append("    )")
    L.append("    fig.axis.visible = False")
    L.append("    fig.grid.grid_line_color = None")
    L.append("    fig.background_fill_alpha = 0")
    L.append("    fig.border_fill_alpha = 0")
    L.append("    fig.outline_line_alpha = 0")
    L.append("    if fig.title:")
    L.append("        fig.title.text_color = '#e2e8f0'")
    L.append("        fig.title.text_font_size = '14px'")
    L.append("    if fig.legend:")
    L.append("        fig.legend.label_text_color = '#94a3b8'")
    L.append("        fig.legend.background_fill_alpha = 0")
    L.append("        fig.legend.border_line_alpha = 0")
    L.append("        fig.legend.label_text_font_size = '10px'")
    L.append("    return fig")
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
    L.append("def build_view(*filter_args):")
    L.append("    filt = apply_filters()")
    L.append("    if filt.empty:")
    L.append('        return pn.pane.Alert("No data matches filters.", alert_type="warning")')
    L.append("")

    # indicators
    L.append(f"    y_data = pd.to_numeric(filt['{c_col}'], errors='coerce').dropna()")
    L.append("    n = len(filt)")
    L.append("    y_total = round(float(y_data.sum()), 2) if len(y_data) else 0")
    L.append("    y_mean = round(float(y_data.mean()), 2) if len(y_data) else 0")
    L.append("    y_min = round(float(y_data.min()), 2) if len(y_data) else 0")
    L.append("    y_max = round(float(y_data.max()), 2) if len(y_data) else 0")
    L.append("")
    L.append('    ikw = dict(default_color="currentcolor", font_size="28px", title_size="12px")')
    L.append("    indicators = pn.FlexBox(")
    L.append('        pn.indicators.Number(name="Count", value=n, format="{value:,}", **ikw),')
    L.append('        pn.indicators.Number(name="Total", value=y_total, format="{value:,.0f}", **ikw),')
    L.append('        pn.indicators.Number(name="Mean", value=y_mean, format="{value:,.2f}", **ikw),')
    L.append('        pn.indicators.Number(name="Min", value=y_min, format="{value:,.2f}", **ikw),')
    L.append('        pn.indicators.Number(name="Max", value=y_max, format="{value:,.2f}", **ikw),')
    L.append("    )")
    L.append("")

    # candlestick chart
    L.append("    candle_fig = build_candlestick(filt)")
    L.append("    chart_pane = pn.pane.Bokeh(candle_fig, sizing_mode='stretch_both', min_height=420)")
    L.append("")

    # pie chart - group by color column or a categorical column
    if pie_group:
        pie_y = y_col
        # For OHLC data, use Close as the pie value
        if y_col.lower() in ("close", "open", "high", "low"):
            # Check if there's a Market_Value or similar numeric column
            for c in df_temp.columns:
                if c.lower() in ("market_value", "marketvalue", "value", "shares", "amount"):
                    pie_y = c
                    break
        L.append(f"    group_col = '{pie_group}'")
        L.append(f"    pie_y = '{pie_y}'")
        L.append("    if group_col in filt.columns and pd.api.types.is_numeric_dtype(filt[pie_y]):")
        L.append("        pie_fig = build_pie(filt, pie_y, group_col)")
        L.append("        pie_pane = pn.pane.Bokeh(pie_fig, sizing_mode='fixed', width=400, height=400)")
        L.append("    else:")
        L.append("        pie_pane = pn.Spacer(width=0)")
    else:
        L.append(f"    pie_y = '{y_col}'")
        L.append(f"    x_col = '{x_col}'")
        L.append("    if filt[x_col].dtype == 'object' and pd.api.types.is_numeric_dtype(filt[pie_y]):")
        L.append("        pie_fig = build_pie(filt, pie_y, x_col)")
        L.append("        pie_pane = pn.pane.Bokeh(pie_fig, sizing_mode='fixed', width=400, height=400)")
        L.append("    else:")
        L.append("        pie_pane = pn.Spacer(width=0)")
    L.append("")

    # chart row
    L.append("    chart_row = pn.Row(")
    L.append("        chart_pane,")
    L.append("        pie_pane,")
    L.append("        sizing_mode='stretch_width',")
    L.append("    )")
    L.append("")

    # table with styled formatters
    L.append("    # Styled table")
    L.append("    text_align = {col: 'right' for col in filt.columns if pd.api.types.is_numeric_dtype(filt[col])}")
    L.append("    style_cols = []")
    L.append("    for col in filt.columns:")
    L.append("        if filt[col].dtype == 'object':")
    L.append("            uv = [str(v).lower() for v in filt[col].unique()]")
    L.append("            if any(v in uv for v in ['buy', 'sell', 'hold']):")
    L.append("                style_cols.append(col)")
    L.append("    if style_cols:")
    L.append("        def color_action(val):")
    L.append("            v = str(val).lower()")
    L.append("            if v == 'buy': return 'color: #4ade80; font-weight: bold'")
    L.append("            if v == 'sell': return 'color: #f87171; font-weight: bold'")
    L.append("            if v == 'hold': return 'color: #94a3b8'")
    L.append("            return ''")
    L.append("        styler = filt.style")
    L.append("        for sc in style_cols:")
    L.append("            styler = styler.map(color_action, subset=[sc])")
    L.append("        table = pn.widgets.Tabulator(")
    L.append('            styler, show_index=False, page_size=15, pagination="remote",')
    L.append('            sizing_mode="stretch_width", height=300, theme="midnight",')
    L.append("            text_align=text_align,")
    L.append("        )")
    L.append("    else:")
    L.append("        table = pn.widgets.Tabulator(")
    L.append('            filt, show_index=False, page_size=15, pagination="remote",')
    L.append('            sizing_mode="stretch_width", height=300, theme="midnight",')
    L.append("            text_align=text_align,")
    L.append("        )")
    L.append("")

    L.append("    return pn.Column(")
    L.append("        indicators,")
    L.append("        chart_row,")
    L.append('        pn.pane.Markdown("### Data"),')
    L.append("        table,")
    L.append("        sizing_mode='stretch_width',")
    L.append("    )")
    L.append("")

    # ---- bind ----
    L.append("# ==================== Bind ====================")
    L.append("main_view = pn.bind(")
    L.append("    build_view,")
    L.append("    *[w for w in filter_widgets],")
    L.append(")")
    L.append("")

    # ---- sidebar ----
    L.append("# ==================== Sidebar ====================")
    L.append("sidebar_items = [")
    L.append(f'    pn.pane.Markdown("### {title}\\n\\n'
             f'**{n_rows:,}** rows | **{n_cols}** columns"),')
    L.append("    pn.layout.Divider(),")
    L.append("]")
    L.append("if filter_widgets:")
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
    L.append('    accent_base_color="#e11d48",')
    L.append('    header_background="#be123c",')
    L.append(")")
    L.append("template.servable()")

    return "\n".join(L)


def _generate_panel_code(viz: dict) -> str:
    """Generate a polished Panel dashboard with main chart + pie chart + styled table.

    Produces apps with:
    - Main chart (left) + Pie/donut chart (right) in a row
    - Indicator cards (Count, Total, Mean, Min, Max)
    - Styled Tabulator table with colored text formatters
    - Sidebar controls (chart type, axes, color, filters)
    - Dark FastListTemplate with accent header
    """
    if viz["kind"] == "points":
        return _generate_geo_panel_code(viz)
    if viz["kind"] == "multi":
        return _generate_multi_panel_code(viz)
    if viz["kind"] == "candlestick":
        return _generate_candlestick_panel_code(viz)

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

    # Detect grouping column for pie chart (prefer color, fallback to x if categorical)
    pie_group = None
    if color and color in df_temp.columns and df_temp[color].dtype == "object":
        pie_group = color
    elif df_temp[x_col].dtype == "object":
        pie_group = x_col

    L: list[str] = []

    # ---- imports ----
    L.append("import json")
    L.append("import math")
    L.append("import pandas as pd")
    L.append("import numpy as np")
    L.append("import panel as pn")
    L.append("import holoviews as hv")
    L.append("import hvplot.pandas  # noqa: F401")
    L.append("from bokeh.plotting import figure as bokeh_figure")
    L.append("from bokeh.models import ColumnDataSource")
    L.append("from bokeh.transform import cumsum")
    L.append("from bokeh.palettes import Category10, Category20")
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

    # ---- pie chart builder ----
    L.append("# ==================== Pie Chart ====================")
    L.append("def build_pie(filt, y_val, group_col=None):")
    L.append("    if group_col and group_col in filt.columns:")
    L.append("        agg = filt.groupby(group_col)[y_val].sum().reset_index()")
    L.append("    else:")
    L.append("        agg = filt.head(20)[[filt.columns[0], y_val]].copy()")
    L.append("        group_col = filt.columns[0]")
    L.append("    agg = agg.sort_values(y_val, ascending=False).head(15)")
    L.append("    agg['angle'] = agg[y_val] / agg[y_val].sum() * 2 * math.pi")
    L.append("    agg['pct'] = (agg[y_val] / agg[y_val].sum() * 100).round(1)")
    L.append("    n = len(agg)")
    L.append("    palette = Category20[20] if n > 10 else Category10[max(3, min(n, 10))]")
    L.append("    agg['color'] = [palette[i % len(palette)] for i in range(n)]")
    L.append("    source = ColumnDataSource(agg)")
    L.append("    total = agg[y_val].sum()")
    L.append("    fig = bokeh_figure(")
    L.append("        title=f'Total: {total:,.0f}',")
    L.append("        toolbar_location=None,")
    L.append("        tools='hover',")
    L.append("        tooltips=f'@{group_col}: @{y_val}{{0,0}} (@pct%)',")
    L.append("        x_range=(-0.5, 1.0),")
    L.append("        height=350, width=350,")
    L.append("    )")
    L.append("    fig.annular_wedge(")
    L.append("        x=0, y=1, inner_radius=0.15, outer_radius=0.4,")
    L.append("        start_angle=cumsum('angle', include_zero=True),")
    L.append("        end_angle=cumsum('angle'),")
    L.append("        line_color='white', line_width=2,")
    L.append("        fill_color='color',")
    L.append("        legend_field=group_col,")
    L.append("        source=source,")
    L.append("    )")
    L.append("    fig.axis.visible = False")
    L.append("    fig.grid.grid_line_color = None")
    L.append("    fig.background_fill_alpha = 0")
    L.append("    fig.border_fill_alpha = 0")
    L.append("    fig.outline_line_alpha = 0")
    L.append("    if fig.title:")
    L.append("        fig.title.text_color = '#e2e8f0'")
    L.append("        fig.title.text_font_size = '14px'")
    L.append("    if fig.legend:")
    L.append("        fig.legend.label_text_color = '#94a3b8'")
    L.append("        fig.legend.background_fill_alpha = 0")
    L.append("        fig.legend.border_line_alpha = 0")
    L.append("        fig.legend.label_text_font_size = '10px'")
    L.append("    return fig")
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
    L.append("    y_total = round(float(y_data.sum()), 2) if len(y_data) else 0")
    L.append("    y_mean = round(float(y_data.mean()), 2) if len(y_data) else 0")
    L.append("    y_min = round(float(y_data.min()), 2) if len(y_data) else 0")
    L.append("    y_max = round(float(y_data.max()), 2) if len(y_data) else 0")
    L.append("")
    L.append('    ikw = dict(default_color="currentcolor", font_size="28px", title_size="12px")')
    L.append("    indicators = pn.FlexBox(")
    L.append('        pn.indicators.Number(name="Count", value=n, format="{value:,}", **ikw),')
    L.append('        pn.indicators.Number(name="Total", value=y_total, format="{value:,.0f}", **ikw),')
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

    # pie chart
    L.append("    # Pie / donut chart")
    L.append("    group_col = cc if cc and cc in filt.columns else (x_val if filt[x_val].dtype == 'object' else None)")
    L.append("    if group_col and pd.api.types.is_numeric_dtype(filt[y_val]):")
    L.append("        pie_fig = build_pie(filt, y_val, group_col)")
    L.append("        pie_pane = pn.pane.Bokeh(pie_fig, sizing_mode='fixed', width=380, height=380)")
    L.append("    else:")
    L.append("        pie_pane = pn.Spacer(width=0)")
    L.append("")

    # chart row
    L.append("    chart_row = pn.Row(")
    L.append("        chart_pane,")
    L.append("        pie_pane,")
    L.append("        sizing_mode='stretch_width',")
    L.append("    )")
    L.append("")

    # table with styled formatters
    L.append("    # Styled table")
    L.append("    tab_formatters = {}")
    L.append("    for col in filt.columns:")
    L.append("        if filt[col].dtype == 'object':")
    L.append("            uv = filt[col].unique().tolist()")
    L.append("            lv = [str(v).lower() for v in uv]")
    L.append("            if any(v in lv for v in ['buy', 'sell', 'hold', 'yes', 'no', 'true', 'false']):")
    L.append("                tab_formatters[col] = {'type': 'plaintext'}")
    L.append("    text_align = {col: 'right' for col in filt.columns if pd.api.types.is_numeric_dtype(filt[col])}")
    L.append("    table = pn.widgets.Tabulator(")
    L.append('        filt, show_index=False, page_size=15, pagination="remote",')
    L.append('        sizing_mode="stretch_width", height=300, theme="midnight",')
    L.append("        text_align=text_align,")
    L.append("    )")
    L.append("")

    # Color action-like columns via row formatters
    L.append("    # Color-code action columns")
    L.append("    style_cols = []")
    L.append("    for col in filt.columns:")
    L.append("        if filt[col].dtype == 'object':")
    L.append("            uv = [str(v).lower() for v in filt[col].unique()]")
    L.append("            if any(v in uv for v in ['buy', 'sell', 'hold']):")
    L.append("                style_cols.append(col)")
    L.append("    if style_cols:")
    L.append("        def color_action(val):")
    L.append("            v = str(val).lower()")
    L.append("            if v == 'buy': return 'color: #4ade80; font-weight: bold'")
    L.append("            if v == 'sell': return 'color: #f87171; font-weight: bold'")
    L.append("            if v == 'hold': return 'color: #94a3b8'")
    L.append("            return ''")
    L.append("        styler = filt.style")
    L.append("        for sc in style_cols:")
    L.append("            styler = styler.map(color_action, subset=[sc])")
    L.append("        table = pn.widgets.Tabulator(")
    L.append('            styler, show_index=False, page_size=15, pagination="remote",')
    L.append('            sizing_mode="stretch_width", height=300, theme="midnight",')
    L.append("            text_align=text_align,")
    L.append("        )")
    L.append("")

    L.append("    return pn.Column(")
    L.append("        indicators,")
    L.append("        chart_row,")
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
    L.append('    accent_base_color="#e11d48",')
    L.append('    header_background="#be123c",')
    L.append(")")
    L.append("template.servable()")

    return "\n".join(L)
