"""Tool for creating custom Panel apps from LLM-written code."""

import ast
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser

from ..app import _panel_servers, mcp
from .panel_launch import _find_free_port

# Allowed top-level modules for create_panel_app code
_ALLOWED_MODULES = frozenset({
    "panel", "pn", "holoviews", "hv", "hvplot", "bokeh", "geoviews", "gv",
    "datashader", "colorcet", "cartopy", "numpy", "np", "pandas", "pd",
    "param", "math", "json", "datetime", "functools", "itertools",
    "collections", "io", "textwrap", "pathlib",
    "scipy", "skimage", "sklearn",
})

# Explicitly blocked dangerous modules
_BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
    "requests", "importlib", "ctypes", "signal", "multiprocessing",
    "threading", "pickle", "shelve", "code", "compile", "compileall",
    "webbrowser", "ftplib", "smtplib", "telnetlib", "xmlrpc",
})


def _check_imports(code: str) -> str | None:
    """Validate imports in code. Returns error message or None if safe."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # Syntax check is done separately

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_MODULES:
                    return f"Blocked import: '{alias.name}' (security restriction)"
                if top not in _ALLOWED_MODULES:
                    return f"Import not allowed: '{alias.name}'. Allowed: panel, holoviews, hvplot, bokeh, geoviews, datashader, colorcet, cartopy, numpy, pandas, param, math, json, datetime"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _BLOCKED_MODULES:
                    return f"Blocked import: 'from {node.module}' (security restriction)"
                if top not in _ALLOWED_MODULES:
                    return f"Import not allowed: 'from {node.module}'. Allowed: panel, holoviews, hvplot, bokeh, geoviews, datashader, colorcet, cartopy, numpy, pandas, param, math, json, datetime"

    # Check for __import__, exec, eval calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("__import__", "exec", "eval", "compile"):
                return f"Blocked call: '{func.id}()' (security restriction)"

    return None


# Launcher script template - runs Panel in a completely independent process
_LAUNCHER_PY = '''
import subprocess, sys, os
script = sys.argv[1]
port = sys.argv[2]
stderr_path = sys.argv[3]

with open(stderr_path, "w") as ef:
    proc = subprocess.Popen(
        [sys.executable, "-m", "panel", "serve", script,
         "--port", port, "--allow-websocket-origin", "*", "--num-procs", "1"],
        stdout=subprocess.DEVNULL, stderr=ef, stdin=subprocess.DEVNULL,
    )
    # Write PID so parent can track it
    pid_path = stderr_path.replace("stderr.log", "panel.pid")
    with open(pid_path, "w") as pf:
        pf.write(str(proc.pid))
    proc.wait()
'''


@mcp.tool()
def create_panel_app(code: str, title: str = "Panel App") -> str:
    """Create and launch a custom interactive Panel app from Python code.

    Write any valid Panel/HoloViews/hvPlot/GeoViews/Datashader Python code.
    The code MUST call .servable() on the final Panel layout.

    Use this tool when you need full creative control over the dashboard -
    custom layouts, datashader rendering, geographic tiles, BoundsXY streams,
    cross-filtering, custom headers, or any Panel feature.

    Available libraries: panel, holoviews, hvplot, geoviews, datashader,
    bokeh, colorcet, cartopy, numpy, pandas.

    Args:
        code: Complete Python code for a Panel app. Must end with .servable()
        title: Title for the app (used for tracking)
    """
    try:
        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            return json.dumps({
                "action": "error",
                "message": f"Syntax error in code: {e.msg} (line {e.lineno})"
            })

        if ".servable()" not in code:
            return json.dumps({
                "action": "error",
                "message": "Code must call .servable() on the final layout"
            })

        # Security: validate imports are from allowed modules only
        import_err = _check_imports(code)
        if import_err:
            return json.dumps({"action": "error", "message": import_err})

        app_id = f"custom_{abs(hash(title)) % 100000:05d}"

        # Stop existing
        if app_id in _panel_servers:
            info = _panel_servers[app_id]
            pid = info.get("panel_pid")
            if pid:
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                       capture_output=True, timeout=5)
                    else:
                        os.kill(pid, 9)
                except Exception:
                    pass
            del _panel_servers[app_id]

        port = _find_free_port()
        tmp_dir = tempfile.mkdtemp(prefix="panel_custom_")
        script_path = os.path.join(tmp_dir, "app.py")
        stderr_path = os.path.join(tmp_dir, "stderr.log")
        launcher_path = os.path.join(tmp_dir, "launcher.py")
        pid_path = os.path.join(tmp_dir, "panel.pid")

        with open(script_path, "w") as f:
            f.write(code)
        with open(launcher_path, "w") as f:
            f.write(_LAUNCHER_PY)

        # Launch via intermediate Python script - fully detached
        popen_kw = dict(
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        if sys.platform == "win32":
            popen_kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kw["start_new_session"] = True

        launcher_proc = subprocess.Popen(
            [sys.executable, launcher_path, script_path, str(port), stderr_path],
            **popen_kw,
        )

        url = f"http://localhost:{port}/app"
        _panel_servers[app_id] = {
            "process": launcher_proc, "port": port, "url": url,
            "tmp_dir": tmp_dir, "stderr_path": stderr_path,
            "pid_path": pid_path, "title": title,
        }

        # Wait for ready + open browser + read Panel PID
        def _wait_and_open():
            for _ in range(120):
                try:
                    req = urllib.request.urlopen(url, timeout=3)
                    req.close()
                    # Read the actual Panel PID
                    try:
                        with open(pid_path) as pf:
                            _panel_servers[app_id]["panel_pid"] = int(pf.read().strip())
                    except Exception:
                        pass
                    webbrowser.open(url)
                    return
                except Exception:
                    time.sleep(0.5)

        threading.Thread(target=_wait_and_open, daemon=True).start()

        return json.dumps({
            "action": "custom_app_launched",
            "id": app_id,
            "url": url,
            "port": port,
            "title": title,
            "lines": code.count("\n") + 1,
            "message": f"Custom Panel app '{title}' launching at {url}",
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": f"Failed: {str(e)}"})
