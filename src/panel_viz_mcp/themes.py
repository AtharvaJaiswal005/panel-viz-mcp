"""Theme colors and CSS variables shared across all views."""

# ---------------------------------------------------------------------------
# Bokeh figure theming
# ---------------------------------------------------------------------------
THEME_COLORS = {
    "dark": {
        "label": "#94a3b8",
        "tick": "#475569",
        "grid": "#334155",
        "grid_alpha": 0.5,
        "title": "#e0e0e0",
        "legend_text": "#94a3b8",
    },
    "light": {
        "label": "#374151",
        "tick": "#d1d5db",
        "grid": "#e5e7eb",
        "grid_alpha": 0.8,
        "title": "#111827",
        "legend_text": "#374151",
    },
}

# ---------------------------------------------------------------------------
# CSS variables injected into every HTML resource
# ---------------------------------------------------------------------------
CSS_THEME_VARS = """
    body.theme-dark {
      --bg-body: #0f172a;
      --text-primary: #e0e0e0; --text-secondary: #94a3b8; --text-muted: #64748b;
      --bg-card: rgba(30,41,59,0.6); --bg-surface: rgba(15,23,42,0.5);
      --border: #334155; --accent: #818cf8; --accent-bg: rgba(99,102,241,0.08);
      --error: #f87171; --success: #4ade80; --warning: #f59e0b;
      --btn-bg: #1e293b; --btn-border: #334155; --input-bg: #0f172a;
      --stat-value: #818cf8; --table-header-bg: #1e293b;
    }
    body.theme-light {
      --bg-body: #ffffff;
      --text-primary: #1f2937; --text-secondary: #6b7280; --text-muted: #9ca3af;
      --bg-card: rgba(255,255,255,0.9); --bg-surface: rgba(249,250,251,0.8);
      --border: #e5e7eb; --accent: #6366f1; --accent-bg: rgba(99,102,241,0.06);
      --error: #dc2626; --success: #16a34a; --warning: #d97706;
      --btn-bg: #f9fafb; --btn-border: #d1d5db; --input-bg: #ffffff;
      --stat-value: #6366f1; --table-header-bg: #f3f4f6;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .spinner {
      width: 28px; height: 28px; border: 3px solid var(--border);
      border-top-color: var(--accent); border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .loading {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 10px; min-height: 200px;
      color: var(--text-muted); font-size: 13px;
    }
    .error-box {
      background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
      border-radius: 8px; padding: 20px; text-align: center; margin: 12px 0;
    }
    .error-box .error-title { color: var(--error); font-size: 14px; font-weight: 600; margin-bottom: 6px; }
    .error-box .error-detail { color: var(--text-muted); font-size: 12px; }
    .error-box .error-hint { color: var(--text-muted); font-size: 11px; margin-top: 8px; opacity: 0.7; }
    .sample-notice {
      background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2);
      border-radius: 6px; padding: 6px 12px; font-size: 11px;
      color: var(--warning); text-align: center; margin: 4px 0;
    }
"""
