"""Multi-chart dashboard tool."""

import json
import uuid

import holoviews as hv
import pandas as pd
from bokeh.embed import json_item
from fastmcp.server.apps import AppConfig

from ..app import _viz_store, mcp
from ..chart_builders import _apply_theme_to_layout, _build_bokeh_figure
from ..constants import CHART_PALETTE, MAX_CHART_ROWS, MULTI_URI


@mcp.tool(app=AppConfig(resource_uri=MULTI_URI))
def create_multi_chart(
    title: str,
    data: dict[str, list],
    charts: list[dict],
) -> str:
    """Create a multi-chart dashboard with 2-4 charts showing different views of the same data.

    Args:
        title: Dashboard title
        data: Shared dataset as dictionary of column_name -> list of values
        charts: List of 1-4 chart configs, each with keys: kind, x, y, title (optional), color (optional)
    """
    try:
        if len(charts) < 1 or len(charts) > 4:
            return json.dumps({"action": "error", "message": "Provide 1-4 chart configurations"})

        df = pd.DataFrame(data)
        if len(df) > MAX_CHART_ROWS:
            df = df.sample(n=MAX_CHART_ROWS, random_state=42).sort_index()

        viz_id = str(uuid.uuid4())[:8]

        _viz_store[viz_id] = {
            "id": viz_id,
            "kind": "multi",
            "title": title,
            "data": data,
            "charts": charts,
            "theme": "dark",
        }

        # Try linked brushing via HoloViews Layout
        try:
            ls = hv.link_selections.instance()
            plots = []

            for i, chart_cfg in enumerate(charts):
                kind = chart_cfg.get("kind", "bar")
                cx = chart_cfg.get("x")
                cy = chart_cfg.get("y")
                chart_title = chart_cfg.get("title", f"Chart {i + 1}")
                ccolor = chart_cfg.get("color") or None
                has_group = ccolor and ccolor in df.columns

                base = {"title": chart_title, "height": 300, "responsive": True}
                simple = {"bar", "line", "scatter", "area", "step"}
                pal_color = CHART_PALETTE[i % len(CHART_PALETTE)]

                if kind in simple:
                    kw = {**base, "x": cx, "y": cy}
                    if has_group:
                        kw["by"] = ccolor
                    else:
                        kw["color"] = pal_color
                        kw["hover_cols"] = "all"
                    plot = getattr(df.hvplot, kind)(**kw)
                elif kind == "histogram":
                    kw = {**base, "y": cy, "color": pal_color}
                    plot = df.hvplot.hist(**kw)
                elif kind in ("box", "violin"):
                    kw = {**base, "y": cy, "color": pal_color}
                    if cx and cx in df.columns and not pd.api.types.is_numeric_dtype(df[cx]):
                        kw["by"] = cx
                    plot = getattr(df.hvplot, kind)(**kw)
                elif kind == "kde":
                    kw = {**base, "y": cy, "color": pal_color}
                    plot = df.hvplot.kde(**kw)
                else:
                    kw = {**base, "x": cx, "y": cy, "color": pal_color, "hover_cols": "all"}
                    plot = df.hvplot.scatter(**kw)

                plots.append(ls(plot))

            layout = hv.Layout(plots).cols(min(len(charts), 2))
            bokeh_layout = hv.render(layout, backend="bokeh")
            _apply_theme_to_layout(bokeh_layout, "dark")
            bokeh_layout.sizing_mode = "stretch_width"
            spec = json_item(bokeh_layout, "chart-grid")

            return json.dumps({
                "action": "multi_chart",
                "id": viz_id,
                "title": title,
                "figure": spec,
                "chart_count": len(charts),
                "linked": True,
            })

        except Exception:
            # Fallback: individual charts without linked brushing
            figures = []
            for i, chart_cfg in enumerate(charts):
                kind = chart_cfg.get("kind", "bar")
                cx = chart_cfg.get("x")
                cy = chart_cfg.get("y")
                chart_title = chart_cfg.get("title", f"Chart {i + 1}")
                ccolor = chart_cfg.get("color") or None
                target_id = f"chart-{i}"

                try:
                    spec = _build_bokeh_figure(kind, df, cx, cy, chart_title, ccolor, target_id)
                    figures.append({"index": i, "target_id": target_id, "figure": spec, "title": chart_title})
                except Exception as e:
                    figures.append({"index": i, "target_id": target_id, "error": str(e), "title": chart_title})

            return json.dumps({
                "action": "multi_chart",
                "id": viz_id,
                "title": title,
                "figures": figures,
                "chart_count": len(figures),
                "linked": False,
            })
    except Exception as e:
        return json.dumps({"action": "error", "message": str(e)})
