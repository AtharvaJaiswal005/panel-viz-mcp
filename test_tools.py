"""Automated test of all 14 tools + 13 chart types via FastMCP Client."""
import asyncio
import json
from panel_viz_mcp.server import mcp
from fastmcp import Client

async def main():
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        print(f"Tools discovered: {len(tools)}")
        for t in tools:
            print(f"  - {t.name}")
        print()

        # 1. create_viz (bar)
        print("=== 1. create_viz (bar) ===")
        r = await client.call_tool("create_viz", {
            "kind": "bar", "title": "Test Bar",
            "data": {"region": ["East", "West", "North"], "sales": [100, 200, 150]},
            "x": "region", "y": "sales",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        viz_id = result["id"]
        print(f"  action={result['action']}, id={viz_id} - PASS")

        # 2. update_viz
        print("=== 2. update_viz (to line) ===")
        r = await client.call_tool("update_viz", {"viz_id": viz_id, "kind": "line", "title": "Updated Line"})
        result = json.loads(r.content[0].text)
        assert result["action"] == "update" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 3. load_data
        print("=== 3. load_data (CSV) ===")
        r = await client.call_tool("load_data", {
            "file_path": "examples/sample_data.csv", "kind": "bar",
            "x": "region", "y": "sales", "title": "CSV Data",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create"
        csv_viz_id = result["id"]
        print(f"  action={result['action']}, id={csv_viz_id} - PASS")

        # 4. handle_click
        print("=== 4. handle_click ===")
        r = await client.call_tool("handle_click", {
            "viz_id": viz_id, "point_index": 0, "x_value": "East", "y_value": 100.0,
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "insight"
        print(f"  action={result['action']} - PASS")

        # 5. list_vizs
        print("=== 5. list_vizs ===")
        r = await client.call_tool("list_vizs", {})
        result = json.loads(r.content[0].text)
        assert result["action"] == "list" and len(result["visualizations"]) >= 2
        print(f"  count={len(result['visualizations'])} - PASS")

        # 6. create_dashboard
        print("=== 6. create_dashboard ===")
        r = await client.call_tool("create_dashboard", {
            "title": "Test Dashboard",
            "data": {"city": ["NYC", "LA", "CHI", "HOU"], "pop": [8, 4, 3, 2], "state": ["NY", "CA", "IL", "TX"]},
            "x": "city", "y": "pop",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "dashboard"
        assert "figure" in result and "stats" in result and "table" in result
        assert "widget_config" in result and len(result["widget_config"]) > 0
        dash_id = result["id"]
        print(f"  action={result['action']}, widgets={len(result['widget_config'])} - PASS")

        # 7. stream_data
        print("=== 7. stream_data ===")
        r = await client.call_tool("stream_data", {
            "title": "Test Stream", "metric_name": "price", "initial_value": 100.0,
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "stream" and "config" in result
        print(f"  action={result['action']} - PASS")

        # 8. apply_filter
        print("=== 8. apply_filter ===")
        r = await client.call_tool("apply_filter", {
            "viz_id": dash_id, "filters": {"state": "NY"},
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "filter_result"
        assert result["filtered_rows"] == 1
        print(f"  action={result['action']}, filtered_rows={result['filtered_rows']} - PASS")

        # 9. set_theme
        print("=== 9. set_theme ===")
        r = await client.call_tool("set_theme", {"viz_id": viz_id, "theme": "light"})
        result = json.loads(r.content[0].text)
        assert result["action"] == "theme_change" and result["theme"] == "light"
        assert "figure" in result
        print(f"  action={result['action']}, theme={result['theme']} - PASS")

        # 10. create_multi_chart
        print("=== 10. create_multi_chart ===")
        r = await client.call_tool("create_multi_chart", {
            "title": "Multi View",
            "data": {"x": [1, 2, 3, 4], "y": [10, 20, 15, 25], "cat": ["A", "B", "A", "B"]},
            "charts": [
                {"kind": "bar", "x": "cat", "y": "y", "title": "Bar View"},
                {"kind": "line", "x": "x", "y": "y", "title": "Line View"},
            ],
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "multi_chart" and result["chart_count"] == 2
        assert len(result["figures"]) == 2
        print(f"  action={result['action']}, charts={result['chart_count']} - PASS")

        # 11. annotate_viz
        print("=== 11. annotate_viz ===")
        r = await client.call_tool("annotate_viz", {
            "viz_id": viz_id, "annotation_type": "hline",
            "config": {"y_value": 150, "color": "#ef4444", "label": "Target"},
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "update" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 12. export_data
        print("=== 12. export_data ===")
        r = await client.call_tool("export_data", {"viz_id": viz_id, "format": "csv"})
        result = json.loads(r.content[0].text)
        assert result["action"] == "export" and "data" in result
        assert result["format"] == "csv" and len(result["data"]) > 0
        print(f"  action={result['action']}, format={result['format']}, size={len(result['data'])} - PASS")

        # 13. launch_panel (just test error case - stream not supported)
        print("=== 13. launch_panel (error case) ===")
        stream_id = [v["id"] for v in json.loads((await client.call_tool("list_vizs", {})).content[0].text)["visualizations"] if v["kind"] == "stream"][0]
        r = await client.call_tool("launch_panel", {"viz_id": stream_id})
        result = json.loads(r.content[0].text)
        assert result["action"] == "error"
        print(f"  action={result['action']}, msg={result['message'][:40]} - PASS")

        # 14. stop_panel (error case - nothing running)
        print("=== 14. stop_panel (error case) ===")
        r = await client.call_tool("stop_panel", {"viz_id": "nonexistent"})
        result = json.loads(r.content[0].text)
        assert result["action"] == "error"
        print(f"  action={result['action']} - PASS")

        # --- NEW CHART TYPES ---

        # 15. box chart
        print("=== 15. create_viz (box) ===")
        r = await client.call_tool("create_viz", {
            "kind": "box", "title": "Test Box",
            "data": {"group": ["A","A","A","A","B","B","B","B"], "value": [10,20,30,15,40,50,60,45]},
            "x": "group", "y": "value",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 16. violin chart
        print("=== 16. create_viz (violin) ===")
        r = await client.call_tool("create_viz", {
            "kind": "violin", "title": "Test Violin",
            "data": {"group": ["A"]*10 + ["B"]*10, "value": list(range(20))},
            "x": "group", "y": "value",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 17. kde chart
        print("=== 17. create_viz (kde) ===")
        r = await client.call_tool("create_viz", {
            "kind": "kde", "title": "Test KDE",
            "data": {"x": list(range(50)), "value": [i**0.5 + (i % 7) for i in range(50)]},
            "x": "x", "y": "value",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 18. step chart
        print("=== 18. create_viz (step) ===")
        r = await client.call_tool("create_viz", {
            "kind": "step", "title": "Test Step",
            "data": {"x": [1, 2, 3, 4, 5], "y": [10, 15, 13, 17, 20]},
            "x": "x", "y": "y",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 19. heatmap
        print("=== 19. create_viz (heatmap) ===")
        r = await client.call_tool("create_viz", {
            "kind": "heatmap", "title": "Test Heatmap",
            "data": {
                "day": ["Mon", "Mon", "Tue", "Tue", "Wed", "Wed"],
                "hour": ["9am", "2pm", "9am", "2pm", "9am", "2pm"],
                "traffic": [100, 200, 150, 300, 180, 250],
            },
            "x": "day", "y": "hour", "color": "traffic",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 20. hexbin
        print("=== 20. create_viz (hexbin) ===")
        r = await client.call_tool("create_viz", {
            "kind": "hexbin", "title": "Test Hexbin",
            "data": {"x": list(range(100)), "y": [i * 1.5 + (i % 13) for i in range(100)]},
            "x": "x", "y": "y",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # 21. points (geographic - fallback to scatter if no geoviews)
        print("=== 21. create_viz (points/geo) ===")
        r = await client.call_tool("create_viz", {
            "kind": "points", "title": "Test Geo Points",
            "data": {
                "lon": [-73.9, -118.2, -87.6, -95.4],
                "lat": [40.7, 34.1, 41.9, 29.8],
                "city": ["NYC", "LA", "Chicago", "Houston"],
            },
            "x": "lon", "y": "lat", "color": "city",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create" and "figure" in result
        print(f"  action={result['action']} - PASS")

        # --- ORIGINAL BONUS TESTS ---

        # 22. pie chart
        print("=== 22. pie chart ===")
        r = await client.call_tool("create_viz", {
            "kind": "pie", "title": "Test Pie",
            "data": {"fruit": ["Apple", "Banana", "Cherry"], "count": [30, 45, 25]},
            "x": "fruit", "y": "count",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "create"
        print(f"  action={result['action']} - PASS")

        # 23. error handling - bad column
        print("=== 23. bad column (error) ===")
        r = await client.call_tool("create_viz", {
            "kind": "bar", "title": "Bad",
            "data": {"a": [1, 2], "b": [3, 4]},
            "x": "nonexistent", "y": "b",
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "error" and "not found" in result["message"]
        print(f"  action={result['action']} - PASS")

        # 24. annotation on stream (should error)
        print("=== 24. annotation on stream (error) ===")
        r = await client.call_tool("annotate_viz", {
            "viz_id": stream_id, "annotation_type": "hline",
            "config": {"y_value": 100},
        })
        result = json.loads(r.content[0].text)
        assert result["action"] == "error"
        print(f"  action={result['action']} - PASS")

        print(f"\n ALL 24 TESTS PASSED!")

asyncio.run(main())
