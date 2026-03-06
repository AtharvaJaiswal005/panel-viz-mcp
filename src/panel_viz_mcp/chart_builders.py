"""Chart building helpers - Bokeh figure construction, theming, annotations."""

import math

import holoviews as hv
import hvplot.pandas  # noqa: F401 - enables df.hvplot()
import pandas as pd
from bokeh.embed import json_item
from bokeh.models import (
    Arrow,
    BoxAnnotation,
    ColumnDataSource,
    CustomJS,
    FixedTicker,
    HoverTool,
    Label,
    NormalHead,
    NumeralTickFormatter,
    Span,
    TapTool,
)
from bokeh.palettes import Category10
from bokeh.plotting import figure as bokeh_figure
from bokeh.transform import cumsum

from .constants import CHART_PALETTE, CHART_TYPES, MAX_CHART_ROWS
from .themes import THEME_COLORS

hv.extension("bokeh")


def _apply_theme(fig, theme: str = "dark"):
    """Apply theme styling to a Bokeh figure."""
    colors = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    fig.background_fill_alpha = 0
    fig.border_fill_alpha = 0
    fig.outline_line_alpha = 0

    for axis in fig.axis:
        axis.axis_label_text_color = colors["label"]
        axis.major_label_text_color = colors["label"]
        axis.major_tick_line_color = colors["tick"]
        axis.minor_tick_line_color = None
        axis.axis_line_color = colors["tick"]

    for grid in fig.grid:
        grid.grid_line_color = colors["grid"]
        grid.grid_line_alpha = colors["grid_alpha"]

    if fig.title:
        fig.title.text_color = colors["title"]
        fig.title.text_font_size = "14px"

    if fig.legend:
        fig.legend.label_text_color = colors["legend_text"]
        fig.legend.background_fill_alpha = 0
        fig.legend.border_line_alpha = 0


def _build_bokeh_figure(kind: str, df: pd.DataFrame, x: str, y: str,
                        title: str, color: str | None = None,
                        target_id: str = "chart-container",
                        theme: str = "dark"):
    """Build a Bokeh figure using hvPlot/HoloViews and serialize to JSON."""
    if kind not in CHART_TYPES:
        raise ValueError(f"Unsupported chart type: {kind}. Supported: {CHART_TYPES}")

    if x not in df.columns:
        raise ValueError(f"Column '{x}' not found. Available: {list(df.columns)}")
    if y not in df.columns:
        raise ValueError(f"Column '{y}' not found. Available: {list(df.columns)}")
    if color and color not in df.columns:
        raise ValueError(f"Color column '{color}' not found. Available: {list(df.columns)}")

    # Downsample large datasets for rendering performance
    if len(df) > MAX_CHART_ROWS and kind not in ("pie", "heatmap"):
        df = df.sample(n=MAX_CHART_ROWS, random_state=42).sort_index()

    if kind == "pie":
        fig = _build_pie_chart(df, x, y, title, theme)
    elif kind == "candlestick":
        fig = _build_candlestick_chart(df, x, y, title, color, theme)
    else:
        fig = _build_hvplot_chart(kind, df, x, y, title, color)
        _apply_theme(fig, theme)

    # Responsive sizing - fill container width
    fig.sizing_mode = "stretch_width"

    # Format numeric y-axis with thousands separators
    for axis in fig.yaxis:
        if hasattr(axis, "formatter"):
            try:
                axis.formatter = NumeralTickFormatter(format="0,0.[00]")
            except Exception:
                pass

    fig.add_tools(TapTool())
    _add_click_callbacks(fig, x, y)

    return json_item(fig, target_id)


def _build_hvplot_chart(kind: str, df: pd.DataFrame, x: str, y: str,
                        title: str, color: str | None = None):
    """Create a chart with hvPlot and convert to Bokeh figure."""
    base = {"title": title, "height": 350, "responsive": True}

    # Standard x/y charts
    simple_methods = {
        "bar": df.hvplot.bar,
        "line": df.hvplot.line,
        "scatter": df.hvplot.scatter,
        "area": df.hvplot.area,
        "step": df.hvplot.step,
    }

    has_grouping = color and color in df.columns

    # Step charts require numeric X - convert categorical to positional integers
    if kind == "step" and not pd.api.types.is_numeric_dtype(df[x]):
        df = df.copy()
        x_labels = df[x].tolist()
        df["_step_x"] = range(len(df))
        kwargs = {**base, "x": "_step_x", "y": y}
        if has_grouping:
            kwargs["by"] = color
        else:
            kwargs["color"] = CHART_PALETTE[0]
        plot = df.hvplot.step(**kwargs)
        # Overlay original labels as x-tick overrides on the rendered figure
        fig = hv.render(plot, backend="bokeh")
        fig.xaxis[0].ticker = FixedTicker(ticks=list(range(len(x_labels))))
        fig.xaxis[0].major_label_overrides = {i: str(v) for i, v in enumerate(x_labels)}
        return fig

    if kind in simple_methods:
        kwargs = {**base, "x": x, "y": y}
        if has_grouping:
            kwargs["by"] = color
        else:
            kwargs["color"] = CHART_PALETTE[0]
            # hover_cols="all" only works without grouping (by= transforms data lengths)
            kwargs["hover_cols"] = "all"
        plot = simple_methods[kind](**kwargs)

    elif kind == "histogram":
        kwargs = {**base, "y": y}
        if has_grouping:
            kwargs["by"] = color
        else:
            kwargs["color"] = CHART_PALETTE[0]
        plot = df.hvplot.hist(**kwargs)

    elif kind == "box":
        kwargs = {**base, "y": y}
        if x and x in df.columns and not pd.api.types.is_numeric_dtype(df[x]):
            kwargs["by"] = x
        kwargs["color"] = CHART_PALETTE[0]
        plot = df.hvplot.box(**kwargs)

    elif kind == "violin":
        kwargs = {**base, "y": y}
        if x and x in df.columns and not pd.api.types.is_numeric_dtype(df[x]):
            kwargs["by"] = x
        kwargs["color"] = CHART_PALETTE[0]
        plot = df.hvplot.violin(**kwargs)

    elif kind == "kde":
        kwargs = {**base, "y": y}
        if has_grouping:
            kwargs["by"] = color
        else:
            kwargs["color"] = CHART_PALETTE[0]
        plot = df.hvplot.kde(**kwargs)

    elif kind == "heatmap":
        kwargs = {**base, "x": x, "y": y}
        if color and color in df.columns:
            kwargs["C"] = color
        plot = df.hvplot.heatmap(**kwargs)

    elif kind == "hexbin":
        kwargs = {**base, "x": x, "y": y}
        plot = df.hvplot.hexbin(**kwargs)

    elif kind == "points":
        # MCP Apps iframe blocks tile images via CSP.
        # Show a preview scatter with a prominent message to use "Open in Panel" for the full map.
        kwargs = {
            **base, "x": x, "y": y, "s": 80,
            "xlabel": "Longitude", "ylabel": "Latitude",
        }
        if color and color in df.columns:
            kwargs["by"] = color
        else:
            kwargs["color"] = CHART_PALETTE[0]
            kwargs["hover_cols"] = "all"
        plot = df.hvplot.scatter(**kwargs)

    else:
        raise ValueError(f"Unsupported chart type: {kind}")

    fig = hv.render(plot, backend="bokeh")

    # Enhance hover tooltips with number formatting
    for tool in fig.tools:
        if isinstance(tool, HoverTool) and tool.tooltips:
            formatted = []
            for label, field in tool.tooltips:
                if field.startswith("@") and pd.api.types.is_numeric_dtype(df.get(label, pd.Series(dtype="object"))):
                    formatted.append((label, f"{field}{{0,0.[00]}}"))
                else:
                    formatted.append((label, field))
            tool.tooltips = formatted

    # For geo points, add coordinate tooltips if not already present
    if kind == "points":
        for tool in fig.tools:
            if isinstance(tool, HoverTool):
                tool.tooltips = [
                    (x, f"@{{{x}}}{{0.0000}}"),
                    (y, f"@{{{y}}}{{0.0000}}"),
                ] + [
                    (label, field) for label, field in (tool.tooltips or [])
                    if label not in (x, y)
                ]
                break

    return fig


def _build_pie_chart(df: pd.DataFrame, names_col: str, values_col: str,
                     title: str, theme: str = "dark"):
    """Build a pie chart using Bokeh directly (hvPlot doesn't support pie)."""
    data = df.groupby(names_col)[values_col].sum().reset_index()
    data["angle"] = data[values_col] / data[values_col].sum() * 2 * math.pi
    data["pct"] = (data[values_col] / data[values_col].sum() * 100).round(1)

    n = len(data)
    colors = CHART_PALETTE[:n] if n <= len(CHART_PALETTE) else list(Category10[min(n, 10)][:n])
    data["color"] = colors

    source = ColumnDataSource(data)

    fig = bokeh_figure(
        title=title,
        toolbar_location=None,
        tools="hover",
        tooltips=f"@{names_col}: @{values_col}{{0,0}} (@pct%)",
        x_range=(-0.5, 1.0),
        height=350,
    )

    fig.wedge(
        x=0, y=1, radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white", line_width=2,
        fill_color="color",
        legend_field=names_col,
        source=source,
    )

    fig.axis.visible = False
    fig.grid.grid_line_color = None
    fig.background_fill_alpha = 0
    fig.border_fill_alpha = 0
    fig.outline_line_alpha = 0

    tc = THEME_COLORS.get(theme, THEME_COLORS["dark"])
    if fig.title:
        fig.title.text_color = tc["title"]
        fig.title.text_font_size = "14px"
    if fig.legend:
        fig.legend.label_text_color = tc["legend_text"]
        fig.legend.background_fill_alpha = 0
        fig.legend.border_line_alpha = 0

    return fig


def _build_candlestick_chart(df: pd.DataFrame, x: str, y: str,
                              title: str, color: str | None = None,
                              theme: str = "dark"):
    """Build a candlestick (OHLC) chart using raw Bokeh.

    Expects columns: x (date/index), and auto-detects Open/High/Low/Close
    columns in the data. Falls back to a simple line chart if OHLC not found.
    """
    # Auto-detect OHLC columns (case-insensitive)
    col_map = {c.lower(): c for c in df.columns}
    ohlc = {k: col_map.get(k) for k in ("open", "high", "low", "close")}

    if not all(ohlc.values()):
        # Fallback: just plot y as a line
        fig = bokeh_figure(title=title, height=350, x_axis_type="auto",
                           tools="pan,wheel_zoom,box_zoom,reset,hover")
        fig.line(x=range(len(df)), y=df[y].values, line_color="#818cf8", line_width=2)
        _apply_theme(fig, theme)
        return fig

    o_col, h_col, l_col, c_col = ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"]

    df = df.copy()
    # Create integer index for x-axis
    df["_idx"] = range(len(df))
    df["_up"] = df[c_col] >= df[o_col]

    inc = df[df["_up"]]
    dec = df[~df["_up"]]

    bar_width = 0.6

    fig = bokeh_figure(title=title, height=350,
                       tools="pan,wheel_zoom,box_zoom,reset,hover")

    # Wicks (high-low lines)
    fig.segment(x0="_idx", y0=l_col, x1="_idx", y1=h_col, source=inc, color="#4ade80")
    fig.segment(x0="_idx", y0=l_col, x1="_idx", y1=h_col, source=dec, color="#f87171")

    # Bodies (open-close bars)
    fig.vbar(x="_idx", width=bar_width, top=c_col, bottom=o_col, source=inc,
             fill_color="#4ade80", line_color="#4ade80")
    fig.vbar(x="_idx", width=bar_width, top=o_col, bottom=c_col, source=dec,
             fill_color="#f87171", line_color="#f87171")

    # X-axis labels
    if x in df.columns:
        labels = df[x].astype(str).tolist()
        # Show every Nth label to avoid overlap
        step = max(1, len(labels) // 15)
        overrides = {i: labels[i] for i in range(0, len(labels), step)}
        fig.xaxis[0].ticker = FixedTicker(ticks=list(overrides.keys()))
        fig.xaxis[0].major_label_overrides = overrides
        fig.xaxis[0].major_label_orientation = 0.8

    # Hover
    for tool in fig.tools:
        if isinstance(tool, HoverTool):
            tool.tooltips = [
                (x, f"@{{{x}}}"),
                ("Open", f"@{{{o_col}}}{{0,0.[00]}}"),
                ("High", f"@{{{h_col}}}{{0,0.[00]}}"),
                ("Low", f"@{{{l_col}}}{{0,0.[00]}}"),
                ("Close", f"@{{{c_col}}}{{0,0.[00]}}"),
            ]
            break

    _apply_theme(fig, theme)
    return fig


def _add_click_callbacks(fig, x_col: str, y_col: str):
    """Add click event callbacks to Bokeh figure renderers."""
    for renderer in fig.renderers:
        if hasattr(renderer, "data_source"):
            source = renderer.data_source
            cols = list(source.data.keys())
            x_key = x_col if x_col in source.data else (cols[0] if cols else "x")
            y_key = y_col if y_col in source.data else (cols[1] if len(cols) > 1 else "y")

            callback = CustomJS(
                args=dict(source=source),
                code=(
                    "try {"
                    "const idx = source.selected.indices;"
                    "if (!idx.length) return;"
                    "const i = idx[0];"
                    "const xd = source.data['" + x_key + "'];"
                    "const yd = source.data['" + y_key + "'];"
                    "if (!xd || !yd) return;"
                    "window.dispatchEvent(new CustomEvent('bokeh-tap', {"
                    "  detail: { index: i, xValue: String(xd[i]), yValue: Number(yd[i]) }"
                    "}));"
                    "} catch(e) { console.warn('Click callback error:', e); }"
                ),
            )
            source.selected.js_on_change("indices", callback)
            break


def _build_widget_config(df: pd.DataFrame) -> list[dict]:
    """Build widget configuration for dashboard filter sidebar."""
    widgets = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_min = float(df[col].min())
            col_max = float(df[col].max())
            rng = col_max - col_min
            if rng == 0:
                step = 1.0
            elif pd.api.types.is_integer_dtype(df[col]):
                step = max(1, int(rng / 100))
            else:
                step = round(rng / 100, 4)
            widgets.append({
                "column": col,
                "type": "range",
                "min": col_min,
                "max": col_max,
                "step": step,
            })
        elif pd.api.types.is_string_dtype(df[col]) or df[col].dtype.name == "category":
            unique_vals = sorted(df[col].dropna().unique().tolist())
            if len(unique_vals) <= 50:
                widgets.append({
                    "column": col,
                    "type": "select",
                    "options": unique_vals,
                })
    return widgets


def _add_annotation_to_figure(fig, annotation_type: str, config: dict):
    """Add a Bokeh annotation to a figure."""
    if annotation_type == "hline":
        span = Span(
            location=config.get("y_value", 0),
            dimension="width",
            line_color=config.get("color", "#ef4444"),
            line_dash=config.get("dash", "dashed"),
            line_width=2,
        )
        fig.add_layout(span)
        if config.get("label"):
            label = Label(
                x=10, y=config["y_value"],
                text=config["label"],
                text_color=config.get("color", "#ef4444"),
                text_font_size="11px",
                x_units="screen",
            )
            fig.add_layout(label)

    elif annotation_type == "vline":
        span = Span(
            location=config.get("x_value", 0),
            dimension="height",
            line_color=config.get("color", "#6366f1"),
            line_dash=config.get("dash", "dotted"),
            line_width=2,
        )
        fig.add_layout(span)

    elif annotation_type == "text":
        label = Label(
            x=config.get("x", 0),
            y=config.get("y", 0),
            text=config.get("text", ""),
            text_color=config.get("color", "#e0e0e0"),
            text_font_size=config.get("font_size", "12px"),
        )
        fig.add_layout(label)

    elif annotation_type == "band":
        box = BoxAnnotation(
            bottom=config.get("lower", 0),
            top=config.get("upper", 100),
            fill_color=config.get("color", "#4ade80"),
            fill_alpha=config.get("alpha", 0.1),
        )
        fig.add_layout(box)

    elif annotation_type == "arrow":
        arrow = Arrow(
            end=NormalHead(fill_color=config.get("color", "#f59e0b"), size=10),
            x_start=config.get("x_start", 0),
            y_start=config.get("y_start", 0),
            x_end=config.get("x_end", 1),
            y_end=config.get("y_end", 1),
            line_color=config.get("color", "#f59e0b"),
            line_width=2,
        )
        fig.add_layout(arrow)


def _apply_theme_to_layout(model, theme: str = "dark"):
    """Apply theme to a Bokeh model, recursing into layout children."""
    if hasattr(model, "background_fill_alpha"):
        _apply_theme(model, theme)
        model.sizing_mode = "stretch_width"
    for attr in ("children",):
        children = getattr(model, attr, None)
        if children:
            for child in children:
                if isinstance(child, (list, tuple)):
                    for c in child:
                        _apply_theme_to_layout(c, theme)
                else:
                    _apply_theme_to_layout(child, theme)


def _rebuild_figure_with_annotations(viz: dict, target_id: str = "chart-container"):
    """Rebuild a Bokeh figure from viz store data, including all stored annotations."""
    df = pd.DataFrame(viz["data"])
    theme = viz.get("theme", "dark")

    if viz["kind"] == "pie":
        fig = _build_pie_chart(df, viz["x"], viz["y"], viz["title"], theme)
    else:
        fig = _build_hvplot_chart(viz["kind"], df, viz["x"], viz["y"], viz["title"], viz.get("color"))
        _apply_theme(fig, theme)

    fig.sizing_mode = "stretch_width"
    fig.add_tools(TapTool())
    _add_click_callbacks(fig, viz["x"], viz["y"])

    for ann in viz.get("annotations", []):
        _add_annotation_to_figure(fig, ann["type"], ann["config"])

    return json_item(fig, target_id)
