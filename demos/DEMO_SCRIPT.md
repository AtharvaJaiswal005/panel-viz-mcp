# Demo Recording Script

Record these in **VS Code Copilot Chat** (Agent mode) with panel-viz-mcp MCP enabled.
Use a screen recorder that exports GIF (e.g. ScreenToGif, LICEcap, or OBS + ffmpeg).

## Setup (VS Code Copilot Chat)

1. Clone and install:
   ```bash
   git clone https://github.com/AtharvaJaiswal005/panel-viz-mcp.git
   cd panel-viz-mcp
   pip install -e .
   ```

2. Create `.vscode/mcp.json` in your project folder:
   ```json
   {
     "servers": {
       "panel-viz-mcp": {
         "command": "panel-viz-mcp"
       }
     }
   }
   ```

3. Open the folder in VS Code
4. Open Copilot Chat (**Ctrl+Shift+I**)
5. Switch to **Agent** mode (dropdown at top of chat panel)
6. Verify tools icon shows panel-viz-mcp is connected (15 tools)

---

## GIF 1: Create a Chart (15 sec)

**What to show:** User prompt -> interactive chart appears inline

**Prompt:**
```
Create a bar chart showing quarterly revenue:
Q1: 42000, Q2: 58000, Q3: 71000, Q4: 89000
```

**Actions after chart appears:**
1. Hover over bars (show tooltips)
2. Click a bar (show click insight in status bar)

---

## GIF 2: Dashboard with Filters (20 sec)

**Prompt:**
```
Create a dashboard of this sales data with filters:

Region, Product, Sales, Quarter
North, Widget, 1200, Q1
North, Gadget, 800, Q1
South, Widget, 950, Q2
South, Gadget, 1100, Q2
East, Widget, 1400, Q3
East, Gadget, 600, Q3
West, Widget, 1050, Q4
West, Gadget, 900, Q4
```

**Actions after dashboard appears:**
1. Show the full dashboard (chart + stats + table)
2. Change the Region filter to "North"
3. Watch chart, stats, and table update

---

## GIF 3: Open in Panel (15 sec)

**Start from:** An existing inline chart (after GIF 1 or 2)

**Actions:**
1. Click the "Open in Panel" button in the chart toolbar
2. Browser opens with full Panel app
3. Show the FloatPanel inspector, Tabulator table, filter sidebar
4. Change chart type in the inspector dropdown

---

## GIF 4: Streaming Chart (10 sec)

**Prompt:**
```
Create a live streaming stock price chart starting at $150
```

**Actions:**
1. Watch the chart update in real-time
2. Click pause, then play

---

## GIF 5: Multi-Chart View (10 sec)

**Prompt:**
```
Show me a bar chart and scatter plot of this data side by side:
Name, Score, Hours
Alice, 85, 12
Bob, 92, 15
Carol, 78, 9
Dave, 95, 18
Eve, 88, 14
```

**Actions:**
1. Show the 2-chart grid layout

---

## GIF 6: Geographic Map (15 sec)

**Prompt:**
```
Plot these cities on a map:
City, Lat, Lon, Population
New York, 40.71, -74.01, 8300000
Los Angeles, 34.05, -118.24, 3900000
Chicago, 41.88, -87.63, 2700000
Houston, 29.76, -95.37, 2300000
Phoenix, 33.45, -112.07, 1600000
```

**Actions:**
1. Show the map with city markers
2. Hover to show population tooltips

---

## Recording Tips

- Use dark theme in VS Code (matches chart dark theme)
- Window size: 1280x720 or 1920x1080
- Keep terminal/sidebar hidden for cleaner look
- GIF frame rate: 15-20 fps, max 10MB for Discord
- For LinkedIn video: combine GIFs 1+2+3, add text overlays
- Crop to just the chat panel + chart area (no distractions)
