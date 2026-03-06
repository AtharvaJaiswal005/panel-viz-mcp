import numpy as np
import pandas as pd
import panel as pn
from bokeh.plotting import figure as bokeh_figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Blues9
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, roc_curve, auc, classification_report, accuracy_score

pn.extension("tabulator", sizing_mode="stretch_width")

# ---- Dark theme helper ----
def style_fig(p):
    p.background_fill_color = "#0a0a0a"
    p.border_fill_color = "#0a0a0a"
    p.outline_line_color = None
    p.title.text_color = "white"
    p.title.text_font_size = "13pt"
    for ax in p.axis:
        ax.axis_label_text_color = "white"
        ax.major_label_text_color = "#ccc"
        ax.axis_line_color = "#333"
        ax.major_tick_line_color = "#333"
        ax.minor_tick_line_color = None
    for g in p.grid:
        g.grid_line_color = "#222"
        g.grid_line_alpha = 0.5
    return p

# ---- Train model ----
def train_model(n_est, depth, tsize):
    data = load_breast_cancer()
    X, y = data.data, data.target
    names = data.feature_names
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=tsize, random_state=42)
    clf = RandomForestClassifier(n_estimators=n_est, max_depth=depth, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]
    cm = confusion_matrix(y_test, y_pred)
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)
    report = classification_report(y_test, y_pred, target_names=["Malignant", "Benign"], output_dict=True)
    acc = accuracy_score(y_test, y_pred)
    return dict(cm=cm, fpr=fpr, tpr=tpr, roc_auc=roc_auc, report=report, acc=acc,
                importances=clf.feature_importances_, names=names)

# ---- Chart builders ----
def make_cm_fig(cm):
    labels = ["Malignant", "Benign"]
    flat = cm.flatten()
    mx = flat.max() if flat.max() > 0 else 1
    xs = [labels[j] for i in range(2) for j in range(2)]
    ys = [labels[i] for i in range(2) for j in range(2)]
    vals = flat.tolist()
    colors = [Blues9[min(int(v / mx * 8), 8)] for v in vals]
    p = bokeh_figure(title="Confusion Matrix", x_range=labels, y_range=list(reversed(labels)),
                     width=420, height=340, toolbar_location=None,
                     min_border_left=70, min_border_bottom=50)
    p.rect(x=xs, y=ys, width=1, height=1, fill_color=colors, line_color="#333")
    p.text(x=xs, y=ys, text=[str(v) for v in vals],
           text_align="center", text_baseline="middle",
           text_color="white", text_font_size="20pt", text_font_style="bold")
    p.xaxis.axis_label = "Predicted"
    p.yaxis.axis_label = "Actual"
    style_fig(p)
    return p

def make_roc_fig(fpr, tpr, roc_auc):
    p = bokeh_figure(title=f"ROC Curve (AUC = {roc_auc:.3f})",
                     width=420, height=340, min_border_left=60)
    p.line(fpr, tpr, color="#3b82f6", line_width=2.5, legend_label="ROC")
    p.line([0, 1], [0, 1], color="gray", line_dash="dashed", legend_label="Random")
    p.xaxis.axis_label = "False Positive Rate"
    p.yaxis.axis_label = "True Positive Rate"
    p.legend.background_fill_alpha = 0
    p.legend.label_text_color = "white"
    p.legend.border_line_alpha = 0
    p.legend.location = "bottom_right"
    style_fig(p)
    return p

def make_feat_fig(names, importances, top_n):
    idx = np.argsort(importances)[::-1][:top_n]
    top_names = [str(names[i])[:20] for i in idx]
    top_vals = [float(importances[i]) for i in idx]
    top_names_r = list(reversed(top_names))
    top_vals_r = list(reversed(top_vals))
    p = bokeh_figure(title=f"Top {top_n} Feature Importances",
                     y_range=top_names_r, width=420, height=340,
                     min_border_left=150, toolbar_location=None)
    p.hbar(y=top_names_r, right=top_vals_r, height=0.6, color="#f97316")
    p.xaxis.axis_label = "Importance"
    style_fig(p)
    return p

def make_table(report):
    rows = []
    for key, label in [("Malignant", "Malignant"), ("Benign", "Benign"),
                        ("macro avg", "Macro Avg"), ("weighted avg", "Weighted Avg")]:
        r = report[key]
        rows.append({"Class": label, "Precision": round(r["precision"], 3),
                      "Recall": round(r["recall"], 3), "F1": round(r["f1-score"], 3),
                      "Support": int(r["support"])})
    df = pd.DataFrame(rows)
    return pn.widgets.Tabulator(df, theme="midnight", height=300,
                                 sizing_mode="stretch_width", show_index=False)

# ---- Initial train ----
res = train_model(100, 10, 0.3)

# ---- Panes ----
cm_pane = pn.pane.Bokeh(make_cm_fig(res["cm"]))
roc_pane = pn.pane.Bokeh(make_roc_fig(res["fpr"], res["tpr"], res["roc_auc"]))
feat_pane = pn.pane.Bokeh(make_feat_fig(res["names"], res["importances"], 10))
table_pane = pn.Column(make_table(res["report"]))

# ---- Sidebar ----
n_est_w = pn.widgets.IntSlider(name="Trees", start=50, end=500, step=50, value=100)
depth_w = pn.widgets.IntSlider(name="Max Depth", start=2, end=20, value=10)
tsize_w = pn.widgets.FloatSlider(name="Test Size", start=0.1, end=0.5, step=0.05, value=0.3)
topn_w = pn.widgets.IntSlider(name="Top Features", start=5, end=20, value=10)
train_btn = pn.widgets.Button(name="Retrain Model", button_type="success", sizing_mode="stretch_width")

acc_ind = pn.indicators.Number(name="Accuracy", value=round(res["acc"] * 100), format="{value}%",
                                font_size="24pt", default_color="white")
prec_ind = pn.indicators.Number(name="Precision", value=round(res["report"]["weighted avg"]["precision"] * 100),
                                 format="{value}%", font_size="24pt", default_color="white")
rec_ind = pn.indicators.Number(name="Recall", value=round(res["report"]["weighted avg"]["recall"] * 100),
                                format="{value}%", font_size="24pt", default_color="white")
f1_ind = pn.indicators.Number(name="F1 Score", value=round(res["report"]["weighted avg"]["f1-score"] * 100),
                               format="{value}%", font_size="24pt", default_color="white")

def on_train(event):
    r = train_model(n_est_w.value, depth_w.value, tsize_w.value)
    cm_pane.object = make_cm_fig(r["cm"])
    roc_pane.object = make_roc_fig(r["fpr"], r["tpr"], r["roc_auc"])
    feat_pane.object = make_feat_fig(r["names"], r["importances"], topn_w.value)
    table_pane.clear()
    table_pane.append(make_table(r["report"]))
    acc_ind.value = round(r["acc"] * 100)
    prec_ind.value = round(r["report"]["weighted avg"]["precision"] * 100)
    rec_ind.value = round(r["report"]["weighted avg"]["recall"] * 100)
    f1_ind.value = round(r["report"]["weighted avg"]["f1-score"] * 100)

train_btn.on_click(on_train)

sidebar = pn.Column(
    pn.pane.Markdown("### Model Settings"),
    n_est_w, depth_w, tsize_w, topn_w,
    pn.layout.Divider(),
    train_btn,
    pn.layout.Divider(),
    pn.pane.Markdown("### Metrics"),
    acc_ind, prec_ind, rec_ind, f1_ind,
    width=280,
)

# ---- Layout ----
grid = pn.GridSpec(sizing_mode="stretch_both", min_height=700)
grid[0, 0] = cm_pane
grid[0, 1] = roc_pane
grid[1, 0] = feat_pane
grid[1, 1] = table_pane

pn.template.FastListTemplate(
    title="ML Model Evaluator",
    sidebar=[sidebar],
    main=[grid],
    header_background="#7c3aed",
    accent_base_color="#7c3aed",
    theme="dark",
    theme_toggle=False,
).servable()
