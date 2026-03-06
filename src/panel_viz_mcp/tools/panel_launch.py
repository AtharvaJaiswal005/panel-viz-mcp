"""Panel server launch and stop tools."""

import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser

from ..app import _panel_servers, _viz_store, mcp
from ..code_generators import _generate_panel_code


def _find_free_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _cleanup_panel_servers():
    """Stop all running Panel servers on exit."""
    for info in _panel_servers.values():
        try:
            info["process"].terminate()
        except Exception:
            pass


atexit.register(_cleanup_panel_servers)


@mcp.tool()
def launch_panel(viz_id: str) -> str:
    """Launch a full interactive Panel dashboard in the browser with live widgets and filtering.

    Args:
        viz_id: ID of a visualization to open as a Panel app
    """
    try:
        if viz_id not in _viz_store:
            return json.dumps({"action": "error", "message": f"Visualization {viz_id} not found"})

        viz = _viz_store[viz_id]
        if viz["kind"] == "stream":
            return json.dumps({"action": "error",
                               "message": "Stream charts cannot be launched as Panel apps yet"})

        if viz_id in _panel_servers:
            info = _panel_servers[viz_id]
            # Check if process is still running
            if info["process"].poll() is None:
                url = info["url"]
                return json.dumps({"action": "panel_launched", "id": viz_id, "url": url,
                                   "message": f"Panel app already running at {url}"})
            else:
                # Process died - clean up and re-launch
                tmp_dir = info.get("tmp_dir")
                if tmp_dir and os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                del _panel_servers[viz_id]

        port = _find_free_port()
        code = _generate_panel_code(viz)

        tmp_dir = tempfile.mkdtemp(prefix="panel_viz_mcp_")
        script_path = os.path.join(tmp_dir, "app.py")
        stderr_path = os.path.join(tmp_dir, "stderr.log")
        with open(script_path, "w") as f:
            f.write(code)

        stderr_file = open(stderr_path, "w", buffering=1)  # line-buffered
        popen_kwargs = dict(
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            stdin=subprocess.DEVNULL,  # don't inherit MCP's stdin
        )
        # On Windows, hide console window but keep handle inheritance working
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(
            [sys.executable, "-m", "panel", "serve", script_path,
             "--port", str(port), "--allow-websocket-origin", "*",
             "--num-procs", "1"],
            **popen_kwargs,
        )

        url = f"http://localhost:{port}/app"
        _panel_servers[viz_id] = {
            "process": process, "port": port, "url": url,
            "tmp_dir": tmp_dir, "stderr_path": stderr_path,
            "stderr_file": stderr_file,
        }

        # Wait for HTTP ready in background thread, then open browser
        def _wait_and_open():
            for _ in range(120):  # up to ~60 seconds (multi-chart apps need longer)
                if process.poll() is not None:
                    # Process died - read stderr for diagnostics
                    stderr_file.close()
                    try:
                        with open(stderr_path) as f:
                            err = f.read()
                        _panel_servers[viz_id]["error"] = err[:2000]
                    except Exception:
                        pass
                    return
                try:
                    req = urllib.request.urlopen(url, timeout=5)
                    req.close()
                    webbrowser.open(url)
                    return
                except Exception:
                    time.sleep(0.5)

        threading.Thread(target=_wait_and_open, daemon=True).start()

        return json.dumps({
            "action": "panel_launched",
            "id": viz_id,
            "url": url,
            "port": port,
            "message": f"Panel app launching at {url} (opens when ready)",
        })
    except Exception as e:
        return json.dumps({"action": "error", "message": f"Failed to launch Panel: {str(e)}"})


@mcp.tool()
def stop_panel(viz_id: str) -> str:
    """Stop a running Panel server.

    Args:
        viz_id: ID of the visualization whose Panel server to stop
    """
    if viz_id not in _panel_servers:
        return json.dumps({"action": "error", "message": f"No Panel server running for {viz_id}"})

    info = _panel_servers[viz_id]
    try:
        info["process"].terminate()
        info["process"].wait(timeout=5)
    except subprocess.TimeoutExpired:
        info["process"].kill()
    except Exception:
        pass

    # Close stderr file handle
    sf = info.get("stderr_file")
    if sf:
        try:
            sf.close()
        except Exception:
            pass

    tmp_dir = info.get("tmp_dir")
    if tmp_dir and os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)

    del _panel_servers[viz_id]

    return json.dumps({"action": "panel_stopped", "id": viz_id, "message": "Panel server stopped"})
