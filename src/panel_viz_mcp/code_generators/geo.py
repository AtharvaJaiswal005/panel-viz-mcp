"""DeckGL-based Panel app code generator for geographic visualizations."""

import json
import math

import pandas as pd


def _generate_geo_panel_code(viz: dict) -> str:
    """Generate a clean DeckGL Panel app - full-screen 3D map with simple sidebar controls."""
    data_json = json.dumps(viz["data"])
    x_col = viz["x"]
    y_col = viz["y"]
    title = viz["title"]

    df_temp = pd.DataFrame(viz["data"])
    center_lon = round(float(df_temp[x_col].mean()), 4)
    center_lat = round(float(df_temp[y_col].mean()), 4)
    lon_range = float(df_temp[x_col].max() - df_temp[x_col].min())
    lat_range = float(df_temp[y_col].max() - df_temp[y_col].min())
    max_range = max(lon_range, lat_range, 0.01)
    zoom = max(1, min(14, round(8.5 - math.log2(max_range))))
    default_radius = max(500, int(50000 / (2 ** max(0, zoom - 1))))
    n_rows = len(df_temp)

    # Detect numeric columns for elevation scaling
    num_cols = [c for c in df_temp.columns
                if pd.api.types.is_numeric_dtype(df_temp[c]) and c not in (x_col, y_col)]
    cat_cols = [c for c in df_temp.columns
                if df_temp[c].dtype == "object" and c not in (x_col, y_col)]

    L: list[str] = []

    # ---- imports ----
    L.append("import json")
    L.append("import pandas as pd")
    L.append("import panel as pn")
    L.append("")
    L.append('pn.extension("deckgl", sizing_mode="stretch_width")')
    L.append("")

    # ---- data ----
    escaped_data = json.dumps(data_json)  # double-encode for safe embedding
    L.append(f"df = pd.DataFrame(json.loads({escaped_data}))")
    L.append("")

    # ---- sidebar widgets (clean, minimal like gallery) ----
    L.append("# ==================== Controls ====================")
    L.append(f"radius_w = pn.widgets.IntSlider(")
    L.append(f'    name="Radius", start=100, end=100000, value={default_radius}, step=100,')
    L.append(")")
    L.append("elevation_w = pn.widgets.IntSlider(")
    L.append('    name="Elevation", start=1, end=50, value=10, step=1,')
    L.append(")")
    L.append("pitch_w = pn.widgets.IntSlider(")
    L.append('    name="Pitch", start=0, end=60, value=45, step=5,')
    L.append(")")
    L.append("")

    # Add a layer toggle
    L.append("layer_w = pn.widgets.RadioButtonGroup(")
    L.append('    name="Layer", options=["Hexagon", "Scatter"], value="Hexagon",')
    L.append('    button_type="primary",')
    L.append(")")
    L.append("")

    # Add categorical filter if available
    if cat_cols:
        L.append("# Category filter")
        L.append("cat_cols = [c for c in df.columns")
        L.append(f'    if df[c].dtype == "object" and c not in ("{x_col}", "{y_col}")]')
        L.append("filter_widgets = {}")
        L.append("for col in cat_cols:")
        L.append('    opts = ["All"] + sorted(str(v) for v in df[col].unique())')
        L.append('    filter_widgets[col] = pn.widgets.Select(name=col, options=opts, value="All")')
        L.append("")
    else:
        L.append("filter_widgets = {}")
        L.append("")

    # ---- filter helper ----
    L.append("def get_filtered():")
    L.append("    filt = df.copy()")
    L.append("    for col, w in filter_widgets.items():")
    L.append('        if w.value != "All":')
    L.append("            filt = filt[filt[col].astype(str) == w.value]")
    L.append("    return filt")
    L.append("")

    # ---- reactive DeckGL map ----
    L.append("# ==================== DeckGL Map ====================")
    L.append("@pn.depends(layer_w, radius_w, elevation_w, pitch_w,")
    L.append("    *filter_widgets.values())")
    L.append("def deck_map(layer_type, radius, elevation, pitch, *args):")
    L.append("    filtered = get_filtered()")
    L.append("    if filtered.empty:")
    L.append('        return pn.pane.Alert("No data matches filters.", alert_type="warning")')
    L.append('    records = filtered.to_dict("records")')
    L.append("")
    L.append('    if layer_type == "Hexagon":')
    L.append("        layer = {")
    L.append('            "@@type": "HexagonLayer", "data": records,')
    L.append(f'            "getPosition": "@@=[{x_col}, {y_col}]",')
    L.append('            "elevationRange": [0, 3000], "elevationScale": elevation,')
    L.append('            "extruded": True, "radius": radius, "coverage": 0.8,')
    L.append('            "pickable": True, "autoHighlight": True,')
    L.append('            "colorRange": [')
    L.append('                [255, 255, 178], [254, 217, 118], [254, 178, 76],')
    L.append('                [253, 141, 60], [240, 59, 32], [189, 0, 38],')
    L.append('            ],')
    L.append("        }")
    L.append("    else:")
    L.append("        layer = {")
    L.append('            "@@type": "ScatterplotLayer", "data": records,')
    L.append(f'            "getPosition": "@@=[{x_col}, {y_col}]",')
    L.append('            "getRadius": radius, "getFillColor": [130, 140, 248, 200],')
    L.append('            "pickable": True, "radiusMinPixels": 3, "radiusMaxPixels": 40,')
    L.append('            "autoHighlight": True,')
    L.append("        }")
    L.append("")
    L.append("    spec = {")
    L.append("        'initialViewState': {")
    L.append(f"            'longitude': {center_lon}, 'latitude': {center_lat},")
    L.append(f"            'zoom': {zoom}, 'pitch': pitch, 'bearing': 0,")
    L.append("        },")
    L.append("        'mapStyle': 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',")
    L.append("        'layers': [layer],")
    L.append("    }")
    L.append("    return pn.pane.DeckGL(spec, min_height=600, sizing_mode='stretch_both')")
    L.append("")

    # ---- sidebar ----
    L.append("# ==================== Sidebar ====================")
    L.append("sidebar_items = [")
    L.append("    radius_w, elevation_w, pitch_w,")
    L.append("    pn.layout.Divider(),")
    L.append("    layer_w,")
    L.append("]")
    L.append("if filter_widgets:")
    L.append("    sidebar_items.append(pn.layout.Divider())")
    L.append("    sidebar_items.extend(filter_widgets.values())")
    L.append("")

    # ---- template ----
    L.append("# ==================== Template ====================")
    L.append("pn.template.FastListTemplate(")
    L.append(f'    title="{title}",')
    L.append("    sidebar=sidebar_items,")
    L.append("    main=[deck_map],")
    L.append('    theme="dark",')
    L.append('    accent_base_color="#4099da",')
    L.append('    header_background="#2196F3",')
    L.append(").servable()")

    return "\n".join(L)
