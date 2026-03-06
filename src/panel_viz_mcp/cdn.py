"""BokehJS CDN script tags - computed once at import time."""

import bokeh

BOKEH_VERSION = bokeh.__version__
_BOKEH_BASE = "https://cdn.bokeh.org/bokeh/release"

BOKEH_SCRIPTS = "\n".join(
    f'  <script src="{_BOKEH_BASE}/bokeh-{ext}{BOKEH_VERSION}.min.js" crossorigin="anonymous"></script>'
    for ext in ["", "gl-", "widgets-", "tables-"]
)

BOKEH_SCRIPTS_WITH_API = "\n".join(
    f'  <script src="{_BOKEH_BASE}/bokeh-{ext}{BOKEH_VERSION}.min.js" crossorigin="anonymous"></script>'
    for ext in ["", "gl-", "widgets-", "tables-", "api-"]
)
