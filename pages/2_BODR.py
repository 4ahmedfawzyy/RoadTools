import datetime
import io
import json
import uuid
from pathlib import Path

import matplotlib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

st.set_page_config(page_title="CO-BODR Engineering", layout="wide", page_icon="🛣️")

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .block-container { padding-top: 1.6rem; max-width: 1300px; }
        .hero { background: linear-gradient(135deg, #1F3864 0%, #2E5C9A 100%); padding: 1.5rem 2rem;
                border-radius: 14px; margin-bottom: 1.2rem; box-shadow: 0 4px 14px rgba(0,0,0,.18); }
        .hero-title { color: #fff; font-size: 1.9rem; font-weight: 700; line-height: 1.2; }
        .hero-sub { color: rgba(255,255,255,.85); font-size: .98rem; margin-top: .35rem; }
        .metric-card { background: rgba(128,128,128,.08); border: 1px solid rgba(128,128,128,.25);
                       border-radius: 12px; padding: 1rem 1.2rem; text-align: center; }
        .metric-label { font-size: .8rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; opacity: .7; }
        .metric-value { font-size: 2rem; font-weight: 800; color: #5B9BE8; margin-top: .1rem; }
        button[data-baseweb="tab"] { font-weight: 600; }
        /* Blue primary buttons (instead of the default red) */
        button[kind="primary"], button[data-testid="stBaseButton-primary"] {
            background-color: #2E5C9A !important; border-color: #2E5C9A !important; color: #fff !important; }
        button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
            background-color: #3A70B8 !important; border-color: #3A70B8 !important; }
        .disclaimer { font-size: .8rem; opacity: .65; text-align: center; margin: 2rem 0 .5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Data: one JSON file per design code in <repo>/bodr_data (see bodr_data/README.md)
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "bodr_data"
SECTIONS = ("k_values", "horizontal", "turning")


@st.cache_data(show_spinner=False)
def load_codes():
    codes, errors = {}, []
    for f in DATA_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            codes[d.get("code", f.stem.upper())] = d
        except Exception as e:
            errors.append(f"{f.name}: {e}")
    ordered = dict(sorted(codes.items(), key=lambda kv: (kv[1].get("order", 99), kv[0])))
    return ordered, errors


CODES, LOAD_ERRORS = load_codes()


def k_df(cd):
    t = cd["k_values"]
    return pd.DataFrame({"Design Speed (km/h)": t["speeds"], "Crest K": t["crest"], "Sag K": t["sag"]})


def h_df(cd):
    t = cd["horizontal"]
    df = pd.DataFrame({"e (%)": t["e"]})
    for sp, vals in t["radii"].items():
        df[str(sp)] = vals
    return df


def t_df(cd):
    rows = [{"Design Vehicle Type": v["type"], "Symbol": v["symbol"],
             "Min Design Turning Radius (m)": v["min_radius"], "Centerline Radius (CTR) (m)": v["ctr"],
             "Min Inside Radius (m)": v["inside_radius"], "image": v.get("image")} for v in cd["turning"]["vehicles"]]
    return pd.DataFrame(rows)


def image_path(name):
    if not name:
        return None
    for base in (ROOT, Path.cwd()):
        p = base / name
        if p.exists():
            return p
    return None


def pick_index(options, preferred):
    return options.index(preferred) if preferred in options else 0


STRONG = "background-color: #dc3545; color: #ffffff; font-weight: 700"
LIGHT = "background-color: rgba(220,53,69,.18)"


def highlight(df, row_mask, strong_cols=()):
    """Light red on the matching row, solid red on the chosen cell(s)."""
    def style(row):
        if not row_mask(row):
            return [""] * len(row)
        return [STRONG if c in strong_cols else LIGHT for c in row.index]
    return df.style.apply(style, axis=1)


# ----------------------------------------------------------------------------
# Typical cross section (urban): geometry and drawing
# ----------------------------------------------------------------------------
SEG_COLORS = {"lane": "#4a4a4a", "shoulder": "#9a9a9a", "median": "#5aa85a", "footpath": "#d8c27a",
              "verge": "#7cb342", "parking": "#6f7f8f", "kerb": "#222222"}
PAVED = {"lane", "shoulder", "parking"}
BASE_COLOR, SUBBASE_COLOR, SUBGRADE_COLOR = "#8d7f6f", "#b8a98f", "#d6cdbb"
CAR_COLORS = ["#e74c3c", "#3498db", "#ecf0f1", "#f1c40f", "#95a5a6"]


def lane_style(name):
    """Colour and vehicle from the lane name (e.g. 'Bus lane' is red with a bus, 'Cycle lane' is green)."""
    n = name.lower()
    if "bus" in n:
        return "#a63d2f", "bus"
    if "bike" in n or "cycl" in n:
        return "#2f8f5b", None
    return SEG_COLORS["lane"], "car"


def _side_elements(side, p):
    """Elements from the centre outward as dicts."""
    els = []

    def add(name, kind, width, slope, kerb=0.0, **extra):
        els.append(dict(name=name, kind=kind, width=width, slope=slope, kerb=kerb, **extra))

    if p["divided"] and side["inner_sh"] > 0:
        add("Inner shoulder", "shoulder", side["inner_sh"], p["ss"])
    names = side.get("lane_names") or []
    for i, lw in enumerate(side["lane_widths"]):
        nm = (names[i].strip() if i < len(names) and names[i].strip() else f"Lane {i + 1}")
        color, vehicle = lane_style(nm)
        add(nm, "lane", lw, p["sc"], color=color, vehicle=vehicle)
    par = side.get("parking") or {"type": "None", "width": 0.0}
    if par["type"] != "None" and par["width"] > 0:
        add(f"{par['type']} parking", "parking", par["width"], p["sc"], sub=par["type"].lower())
    if side["outer_sh"] > 0:
        add("Outer shoulder", "shoulder", side["outer_sh"], p["ss"])
    if side["footpath"] > 0:
        add("Footpath", "footpath", side["footpath"], -p["sf"], p["kerb"])  # falls toward the road
    if side["verge"] > 0:
        add("Verge", "verge", side["verge"], p["sf"])
    return els


def _build_side(side, p, x0):
    segs, x, y = [], x0, 0.0
    for e in _side_elements(side, p):
        if e["kerb"]:
            segs.append(dict(name="Kerb", kind="kerb", x0=x, y0=y, x1=x, y1=y + e["kerb"], width=0.0, slope=None))
            y += e["kerb"]
        y1 = y - e["slope"] / 100 * e["width"]
        seg = {k: v for k, v in e.items() if k != "kerb"}
        seg.update(x0=x, y0=y, x1=x + e["width"], y1=y1)
        segs.append(seg)
        x, y = x + e["width"], y1
    return segs


def _mirror(segs):
    return [dict(s, x0=-s["x1"], y0=s["y1"], x1=-s["x0"], y1=s["y0"]) for s in reversed(segs)]


def build_section(p):
    """Return the segments of the whole section from left to right."""
    x0 = p["median"] / 2 if p["divided"] else 0.0
    right = _build_side(p["right"], p, x0)
    left = _mirror(_build_side(p["right"] if p["mirror"] else p["left"], p, x0))
    mid = []
    if p["divided"] and x0 > 0:
        mid = [dict(name="Median", kind="median", x0=-x0, y0=0.0, x1=x0, y1=0.0, width=2 * x0, slope=0.0)]
    return left + mid + right


def section_totals(segs):
    def w(kinds):
        return sum(s["width"] for s in segs if s["kind"] in kinds)
    return {
        "lanes": sum(1 for s in segs if s["kind"] == "lane"),
        "carriageway": w({"lane"}),
        "paved": w({"lane", "shoulder"}),
        "parking": w({"parking"}),
        "median": w({"median"}),
        "footpath": w({"footpath"}),
        "overall": w(set(SEG_COLORS) - {"kerb"}),
    }


def layer_list(layers):
    """[(label, thickness_mm)] for the layers that exist (thickness > 0)."""
    layers = layers or {}
    return [(lab, layers.get(k, 0)) for k, lab in (("asphalt", "Asphalt"), ("base", "Base"), ("subbase", "Subbase"))
            if layers.get(k, 0) > 0]


def crossfall_text(s):
    if s["slope"] is None:
        return "-"
    return f"{abs(s['slope']):.1f} (to road)" if s["kind"] == "footpath" else f"{s['slope']:.1f}"


# ---- 2D vehicles (true proportions, drawn end-on or from the side) ----------
def _vehicle_end(ax, xc, yb, kind, front, color):
    from matplotlib.patches import Polygon, Rectangle
    z = 5
    if kind == "bus":
        w = 2.5
        ax.add_patch(Rectangle((xc - w / 2, yb + 0.35), w, 2.65, fc=color, ec="black", lw=0.6, zorder=z))
        ax.add_patch(Rectangle((xc - w / 2 + 0.15, yb + 1.5), w - 0.3, 1.1, fc="#cfe8f7", ec="black", lw=0.4, zorder=z + 1))
        ly = yb + 0.6
    else:
        w = 1.8
        ax.add_patch(Rectangle((xc - w / 2, yb + 0.25), w, 0.7, fc=color, ec="black", lw=0.6, zorder=z))
        ax.add_patch(Polygon([(xc - 0.7, yb + 0.95), (xc + 0.7, yb + 0.95), (xc + 0.55, yb + 1.45),
                              (xc - 0.55, yb + 1.45)], fc=color, ec="black", lw=0.6, zorder=z))
        ax.add_patch(Polygon([(xc - 0.55, yb + 1.0), (xc + 0.55, yb + 1.0), (xc + 0.45, yb + 1.38),
                              (xc - 0.45, yb + 1.38)], fc="#cfe8f7", ec="black", lw=0.3, zorder=z + 1))
        ly = yb + 0.5
    for sx in (-1, 1):
        ax.add_patch(Rectangle((xc + sx * w / 2 - (0.3 if sx > 0 else 0), yb), 0.3, 0.5, fc="#111111", zorder=z + 1))
        ax.add_patch(Rectangle((xc + sx * (w / 2 - 0.35) - 0.15, ly), 0.3, 0.16,
                               fc="#fff3a0" if front else "#ff3b30", ec="black", lw=0.2, zorder=z + 2))


def _vehicle_side(ax, xc, yb, length, color):
    from matplotlib.patches import Circle, Polygon, Rectangle
    k = length / 4.5
    z = 5
    ax.add_patch(Rectangle((xc - 2.25 * k, yb + 0.3), 4.5 * k, 0.7, fc=color, ec="black", lw=0.6, zorder=z))
    ax.add_patch(Polygon([(xc - 1.0 * k, yb + 1.0), (xc + 0.9 * k, yb + 1.0), (xc + 0.5 * k, yb + 1.5),
                          (xc - 0.7 * k, yb + 1.5)], fc=color, ec="black", lw=0.6, zorder=z))
    ax.add_patch(Polygon([(xc - 0.8 * k, yb + 1.05), (xc + 0.75 * k, yb + 1.05), (xc + 0.45 * k, yb + 1.42),
                          (xc - 0.6 * k, yb + 1.42)], fc="#cfe8f7", ec="black", lw=0.3, zorder=z + 1))
    for dx in (-1.4, 1.4):
        ax.add_patch(Circle((xc + dx * k, yb + 0.32), 0.32, fc="#111111", ec="#777777", lw=0.5, zorder=z + 1))


def draw_section(segs, ve=3.0, layers=None, vehicles=True):
    """2D sketch (matplotlib). Heights of the ground and layers are exaggerated by `ve`; vehicles are not."""
    from matplotlib.patches import Patch
    layers = layers or {}
    ta, tb, tsb = (layers.get(k, 0) / 1000 for k in ("asphalt", "base", "subbase"))
    thick = ta + tb + tsb

    fig = plt.figure(figsize=(12, 5.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.1, 1.6], hspace=0.04)
    ax, lab = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    xmin = min(min(s["x0"], s["x1"]) for s in segs)
    xmax = max(max(s["x0"], s["x1"]) for s in segs)
    total = max(xmax - xmin, 1e-6)
    ymin = min(min(s["y0"], s["y1"]) for s in segs)
    ymax = max(max(s["y0"], s["y1"]) for s in segs)
    yb = (ymin - max(thick, 0.45) - 0.25) * ve  # bottom of the drawing

    for s in segs:
        if s["kind"] == "kerb":
            continue
        xs_ = [s["x0"], s["x1"], s["x1"], s["x0"]]
        top0, top1 = s["y0"] * ve, s["y1"] * ve
        col = s.get("color") or SEG_COLORS[s["kind"]]
        if s["kind"] in PAVED and thick > 0:
            ax.fill(xs_, [top0, top1, yb, yb], color=SUBGRADE_COLOR, lw=0)
            for t, c in ((ta, col), (tb, BASE_COLOR), (tsb, SUBBASE_COLOR)):
                if t <= 0:
                    continue
                b0, b1 = top0 - t * ve, top1 - t * ve
                ax.fill(xs_, [top0, top1, b1, b0], color=c, lw=0)
                top0, top1 = b0, b1
        else:
            ax.fill(xs_, [top0, top1, yb, yb], color=col, lw=0)

    pts = [(segs[0]["x0"], segs[0]["y0"])] + [(s["x1"], s["y1"]) for s in segs]
    ax.plot([p[0] for p in pts], [p[1] * ve for p in pts], color="black", lw=1.6, zorder=4)

    for a, b in zip(segs, segs[1:]):  # lane dividers
        if a["kind"] == "lane" and b["kind"] == "lane":
            ax.plot([a["x1"]] * 2, [a["y1"] * ve, a["y1"] * ve - max(ta, 0.15) * ve], ls=":", color="white", lw=0.9, zorder=4)
    if not any(s["kind"] == "median" for s in segs):
        ax.annotate("CL", (0, 0), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8)

    has_vehicle = False
    if vehicles:
        n_car = 0
        for s in segs:
            xc, yb_s = (s["x0"] + s["x1"]) / 2, (s["y0"] + s["y1"]) / 2 * ve
            front = xc < 0  # right-hand traffic: left side comes toward the viewer
            if s["kind"] == "lane" and s.get("vehicle"):
                _vehicle_end(ax, xc, yb_s, s["vehicle"], front, CAR_COLORS[n_car % len(CAR_COLORS)])
                n_car, has_vehicle = n_car + 1, True
            elif s["kind"] == "parking" and s.get("sub") == "parallel" and s["width"] >= 1.9:
                _vehicle_end(ax, xc, yb_s, "car", front, CAR_COLORS[n_car % len(CAR_COLORS)])
                n_car, has_vehicle = n_car + 1, True
            elif s["kind"] == "parking" and s.get("sub") == "perpendicular" and s["width"] >= 3.0:
                _vehicle_side(ax, xc, yb_s, min(4.5, s["width"] * 0.92), CAR_COLORS[n_car % len(CAR_COLORS)])
                n_car, has_vehicle = n_car + 1, True

    top = ymax * ve + (3.8 if has_vehicle else 0.06 * total)
    ax.plot([xmin - 0.03 * total, xmax + 0.03 * total], [yb - 0.02 * total, top], alpha=0)  # sets the extent
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    if thick > 0:
        handles = [Patch(color="#4a4a4a", label=f"Asphalt {layers['asphalt']:g} mm")] if ta > 0 else []
        handles += [Patch(color=BASE_COLOR, label=f"Base {layers['base']:g} mm")] if tb > 0 else []
        handles += [Patch(color=SUBBASE_COLOR, label=f"Subbase {layers['subbase']:g} mm")] if tsb > 0 else []
        handles.append(Patch(color=SUBGRADE_COLOR, label="Subgrade"))
        ax.legend(handles=handles, loc="upper right", fontsize=7, frameon=False)
    fig.canvas.draw()

    lab.set_xlim(ax.get_xlim())
    lab.set_ylim(0, 1)
    lab.axis("off")
    for s in segs:
        if s["kind"] == "kerb" or s["width"] <= 0.01:
            continue
        xm = (s["x0"] + s["x1"]) / 2
        fall = f"{abs(s['slope']):.1f}%" if s["slope"] is not None and s["kind"] != "median" else ""
        if s["width"] / total < 0.0075 * len(s["name"]):  # long names on narrow elements are rotated
            lab.text(xm, 0.98, f"{s['name']}  {s['width']:.2f}  {fall}".strip(), ha="center", va="top",
                     rotation=90, fontsize=7)
        else:
            lab.text(xm, 0.98, f"{s['name']}\n{s['width']:.2f} m" + (f"\n{fall}" if fall else ""),
                     ha="center", va="top", fontsize=8)
    lab.annotate("", xy=(xmin, 0.13), xytext=(xmax, 0.13), arrowprops=dict(arrowstyle="<->", lw=1.2))
    lab.text((xmin + xmax) / 2, 0.07, f"Total width {total:.2f} m", ha="center", va="top", fontsize=9, weight="bold")
    fig.suptitle(f"Typical cross section · ground and layers exaggerated x{ve:g}", fontsize=9, y=0.93)
    return fig


# ---- 3D ---------------------------------------------------------------------
_BI = [0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1]
_BJ = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 2, 6]
_BK = [2, 3, 6, 7, 5, 4, 6, 7, 7, 4, 6, 5]


def _box(x0, x1, y0, y1, z0, z1, color):
    return go.Mesh3d(x=[x0, x1, x1, x0, x0, x1, x1, x0], y=[y0, y0, y1, y1, y0, y0, y1, y1],
                     z=[z0, z0, z0, z0, z1, z1, z1, z1], i=_BI, j=_BJ, k=_BK, color=color,
                     flatshading=True, hoverinfo="skip", showlegend=False)


def make_3d(segs, ve=3.0, layers=None, vehicles=True, length=30.0):
    layers = layers or {}
    ta, tb, tsb = (layers.get(k, 0) / 1000 for k in ("asphalt", "base", "subbase"))
    fig = go.Figure()
    for s in segs:
        col = s.get("color") or SEG_COLORS[s["kind"]]
        fig.add_trace(go.Mesh3d(
            x=[s["x0"], s["x1"], s["x1"], s["x0"]], y=[0, 0, length, length],
            z=[s["y0"] * ve, s["y1"] * ve, s["y1"] * ve, s["y0"] * ve],
            i=[0, 0], j=[1, 2], k=[2, 3], color=col, flatshading=True,
            hoverinfo="text", hovertext=f"{s['name']}: {s['width']:.2f} m", showlegend=False))
        if s["kind"] in PAVED and s["kind"] != "kerb":  # layers on the front face
            top0, top1 = s["y0"] * ve, s["y1"] * ve
            for t, c in ((ta, "#2b2b2b"), (tb, BASE_COLOR), (tsb, SUBBASE_COLOR)):
                if t <= 0:
                    continue
                b0, b1 = top0 - t * ve, top1 - t * ve
                fig.add_trace(go.Mesh3d(x=[s["x0"], s["x1"], s["x1"], s["x0"]], y=[0, 0, 0, 0],
                                        z=[top0, top1, b1, b0], i=[0, 0], j=[1, 2], k=[2, 3], color=c,
                                        flatshading=True, hoverinfo="skip", showlegend=False))
                top0, top1 = b0, b1
    for a, b in zip(segs, segs[1:]):  # lane dividers
        if a["kind"] == "lane" and b["kind"] == "lane":
            z = a["y1"] * ve + 0.01
            fig.add_trace(go.Scatter3d(x=[a["x1"]] * 2, y=[0, length], z=[z, z], mode="lines",
                                       line=dict(color="white", width=3, dash="dash"),
                                       hoverinfo="skip", showlegend=False))
    px = [segs[0]["x0"]] + [s["x1"] for s in segs]
    pz = [segs[0]["y0"] * ve] + [s["y1"] * ve for s in segs]
    fig.add_trace(go.Scatter3d(x=px, y=[0] * len(px), z=pz, mode="lines", line=dict(color="black", width=4),
                               hoverinfo="skip", showlegend=False))
    if vehicles:  # simple box vehicles at true size
        n = 0
        for s in segs:
            xc, zb = (s["x0"] + s["x1"]) / 2, (s["y0"] + s["y1"]) / 2 * ve
            yc = 6 + 12 * (n % 2)
            color = CAR_COLORS[n % len(CAR_COLORS)]
            if s["kind"] == "lane" and s.get("vehicle") == "bus":
                fig.add_trace(_box(xc - 1.25, xc + 1.25, yc - 5.5, yc + 5.5, zb + 0.3, zb + 3.1, color))
            elif (s["kind"] == "lane" and s.get("vehicle") == "car") or (
                    s["kind"] == "parking" and s.get("sub") == "parallel" and s["width"] >= 1.9):
                fig.add_trace(_box(xc - 0.9, xc + 0.9, yc - 2.25, yc + 2.25, zb + 0.25, zb + 0.95, color))
                fig.add_trace(_box(xc - 0.7, xc + 0.7, yc - 1.2, yc + 1.2, zb + 0.95, zb + 1.45, "#cfe8f7"))
            elif s["kind"] == "parking" and s.get("sub") == "perpendicular" and s["width"] >= 3.0:
                half = min(2.25, s["width"] * 0.46)
                fig.add_trace(_box(xc - half, xc + half, yc - 0.9, yc + 0.9, zb + 0.25, zb + 0.95, color))
                fig.add_trace(_box(xc - half * 0.6, xc + half * 0.4, yc - 0.7, yc + 0.7, zb + 0.95, zb + 1.45, "#cfe8f7"))
            else:
                continue
            n += 1
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0),
                      scene=dict(aspectmode="data", xaxis_title="Offset (m)",
                                 yaxis=dict(visible=False), zaxis=dict(visible=False),
                                 camera=dict(eye=dict(x=0.15, y=-1.7, z=0.8))))
    return fig


# ----------------------------------------------------------------------------
# Report model
# ----------------------------------------------------------------------------
if "report_data" not in st.session_state:
    st.session_state.report_data = []


def add_item(item):
    for existing in st.session_state.report_data:
        if {k: v for k, v in existing.items() if k != "id"} == item:
            st.toast("Already in the report.", icon="ℹ️")
            return
    st.session_state.report_data.append({"id": uuid.uuid4().hex, **item})
    st.toast("Added to the calculation note.", icon="✅")


def remove_item(item_id):
    st.session_state.report_data = [i for i in st.session_state.report_data if i["id"] != item_id]


def clear_items():
    st.session_state.report_data = []


def describe(item):
    if item["tool"] == "Cross Section":
        tot = section_totals(build_section(item["params"]))
        return (f"🧱 **Typical cross section** · {item['name']}",
                f"{tot['lanes']} lanes · carriageway {tot['carriageway']:.2f} m · "
                f"total width {tot['overall']:.2f} m")
    code = item.get("code", "AASHTO")
    if item["tool"] == "K-Value":
        return (f"📈 **K-value** · {code} · {item['curve_type']} · {item['speed']} km/h",
                f"Required minimum K = **{item['k_value']}**")
    if item["tool"] == "Horizontal Radius":
        return (f"🔄 **Horizontal radius** · {code} · Vd {item['speed']} km/h · e = {item['e_val']}%",
                f"Minimum radius R = **{item['radius']} m**")
    return (f"📐 **Turning radius** · {code} · {item['vehicle_name']} ({item['symbol']})",
            f"Min design radius **{item['min_r']} m** · CTR {item['ctr']} m · inside radius {item['inside_r']} m")


# ----------------------------------------------------------------------------
# Word calculation note
# ----------------------------------------------------------------------------
def _shade(cell, fill):
    cell._tc.get_or_add_tcPr().append(parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls("w"), fill)))


def _fill(cell, text, bold=False, size=9, color=None, center=True):
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _table(doc, headers, rows, strong=(), light_rows=()):
    """strong: (row, col) cells in solid red; light_rows: row indexes in light red."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    for c, h in enumerate(headers):
        _fill(t.rows[0].cells[c], h, bold=True, color="FFFFFF")
        _shade(t.rows[0].cells[c], "1F3864")
    for r, row in enumerate(rows):
        cells = t.add_row().cells
        for c, val in enumerate(row):
            is_strong = (r, c) in strong
            _fill(cells[c], val, bold=is_strong, color="FFFFFF" if is_strong else None)
            if is_strong:
                _shade(cells[c], "DC3545")
            elif r in light_rows:
                _shade(cells[c], "F8D7DA")
    return t


def _source(doc, table_info):
    p = doc.add_paragraph(f"Source: {table_info.get('source', '-')}")
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(9)


def build_docx(items, codes, project="", prepared_by=""):
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)
    doc.add_heading("CO-BODR - Calculation Note", 0)

    used = list(dict.fromkeys(i.get("code", "AASHTO") for i in items if i["tool"] != "Cross Section"))
    info = doc.add_table(rows=0, cols=2)
    info.style = "Table Grid"
    for label, value in (("Project", project or "-"), ("Prepared by", prepared_by or "-"),
                         ("Date", datetime.date.today().strftime("%d %B %Y")),
                         ("Design code", ", ".join(used) if used else "-")):
        cells = info.add_row().cells
        _fill(cells[0], label, bold=True, size=10, center=False)
        _shade(cells[0], "E7EEF8")
        _fill(cells[1], value, size=10, center=False)
    doc.add_paragraph()

    if not items:
        doc.add_paragraph("No data added to the report yet.")
        return doc

    n = 0
    for code in used:
        cd = codes.get(code, {})
        ks = [i for i in items if i.get("code", "AASHTO") == code and i["tool"] == "K-Value"]
        hs = [i for i in items if i.get("code", "AASHTO") == code and i["tool"] == "Horizontal Radius"]
        ts = [i for i in items if i.get("code", "AASHTO") == code and i["tool"] == "Turning Radius"]

        if ks:
            n += 1
            doc.add_heading(f"{n}. Vertical Alignment (K-Value) - {code}", level=1)
            _table(doc, ["Curve type", "Design speed (km/h)", "Required minimum K"],
                   [[i["curve_type"], i["speed"], i["k_value"]] for i in ks])
            doc.add_paragraph()
            if "k_values" in cd:
                _source(doc, cd["k_values"])
                df = k_df(cd)
                speeds = list(df["Design Speed (km/h)"])
                rows = [[r["Design Speed (km/h)"], r["Crest K"], r["Sag K"]] for _, r in df.iterrows()]
                strong = {(speeds.index(i["speed"]), 1 if i["curve_type"] == "Crest" else 2)
                          for i in ks if i["speed"] in speeds}
                _table(doc, ["Design speed (km/h)", "Crest K", "Sag K"], rows, strong=strong,
                       light_rows={r for r, _ in strong})
                doc.add_paragraph()

        if hs:
            n += 1
            doc.add_heading(f"{n}. Horizontal Alignment - {code}", level=1)
            _table(doc, ["Design speed (km/h)", "Superelevation e (%)", "Minimum radius R (m)"],
                   [[i["speed"], i["e_val"], i["radius"]] for i in hs])
            doc.add_paragraph()
            if "horizontal" in cd:
                _source(doc, cd["horizontal"])
                df = h_df(cd)
                es = [float(e) for e in df["e (%)"]]
                cols = list(df.columns)
                rows = [[r[c] for c in cols] for _, r in df.iterrows()]
                strong = {(es.index(float(i["e_val"])), cols.index(str(i["speed"])))
                          for i in hs if float(i["e_val"]) in es and str(i["speed"]) in cols}
                _table(doc, ["e (%)"] + [f"Vd = {c} km/h" for c in cols[1:]], rows, strong=strong,
                       light_rows={r for r, _ in strong})
                doc.add_paragraph()

        if ts:
            n += 1
            doc.add_heading(f"{n}. Turning Radius Check - {code}", level=1)
            _table(doc, ["Design vehicle", "Symbol", "Min design radius (m)", "CTR (m)", "Min inside radius (m)"],
                   [[i["vehicle_name"], i["symbol"], i["min_r"], i["ctr"], i["inside_r"]] for i in ts])
            doc.add_paragraph()
            if "turning" in cd:
                _source(doc, cd["turning"])
                imgs = {v["symbol"]: v.get("image") for v in cd["turning"]["vehicles"]}
                for sym in dict.fromkeys(i["symbol"] for i in ts):
                    path = image_path(imgs.get(sym))
                    if path:
                        doc.add_paragraph(f"Design vehicle {sym}:")
                        doc.add_picture(str(path), width=Inches(5.5))

    xs = [i for i in items if i["tool"] == "Cross Section"]
    if xs:
        n += 1
        doc.add_heading(f"{n}. Typical Cross Section", level=1)
        for it in xs:
            segs = build_section(it["params"])
            tot = section_totals(segs)
            doc.add_paragraph().add_run(it["name"]).bold = True
            _table(doc, ["Element", "Width (m)", "Cross-fall (%)"],
                   [[s["name"], f"{s['width']:.2f}", crossfall_text(s)] for s in segs if s["kind"] != "kerb"])
            doc.add_paragraph()
            _table(doc, ["Lanes", "Carriageway (m)", "Paved incl. shoulders (m)", "Total width (m)"],
                   [[tot["lanes"], f"{tot['carriageway']:.2f}", f"{tot['paved']:.2f}", f"{tot['overall']:.2f}"]])
            doc.add_paragraph()
            lay = layer_list(it["params"].get("layers"))
            if lay:
                _table(doc, ["Pavement layer", "Thickness (mm)"], [[lab, f"{t:g}"] for lab, t in lay]
                       + [["Total", f"{sum(t for _, t in lay):g}"]])
                doc.add_paragraph()
            fig = draw_section(segs, it["params"]["ve"], it["params"].get("layers"),
                               it["params"].get("vehicles", True))
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            doc.add_picture(buf, width=Inches(6.3))
            doc.add_paragraph()

    note = doc.add_paragraph("Preliminary values taken from the tool tables. Verify against the governing design code.")
    note.runs[0].italic = True
    note.runs[0].font.size = Pt(9)
    return doc


def docx_bytes(items, codes, project, prepared_by):
    bio = io.BytesIO()
    build_docx(items, codes, project, prepared_by).save(bio)
    return bio.getvalue()


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
if st.sidebar.button("🏠 Home", use_container_width=True, type="primary"):
    st.switch_page("app.py")
st.sidebar.markdown("## 🛣️ CO-BODR")

if not CODES:
    st.error(f"No design code data found in `{DATA_DIR}`. Add the `bodr_data` folder from the project files.")
    st.stop()


def code_label(c):
    n = sum(1 for s in SECTIONS if s in CODES[c])
    return f"{c}  ({n}/{len(SECTIONS)} tables)" if n else f"{c}  (no tables yet)"


code = st.sidebar.selectbox("📘 Design code", list(CODES), format_func=code_label)
cd = CODES[code]
st.sidebar.metric("Items in report", len(st.session_state.report_data))
st.sidebar.caption("Add results with the ➕ buttons, then open the **Report** tab to download the calculation note.")
for err in LOAD_ERRORS:
    st.sidebar.warning(f"Could not read {err}")

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
st.markdown(
    f'<div class="hero"><div class="hero-title">🛣️ CO-BODR · Highway Design Wizard</div>'
    f'<div class="hero-sub">Design code: <b>{cd.get("full_name", code)}</b> · design values for vertical curves, '
    f'horizontal curves, turning radii and typical cross sections, with a downloadable calculation note</div></div>',
    unsafe_allow_html=True,
)


def metric(label, value):
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>'


def no_table(section):
    st.info(f"No **{section}** table has been loaded for **{code}** yet. "
            f"Add it to `bodr_data/{code.lower()}.json` (see `bodr_data/README.md`).")
    if cd.get("notes"):
        st.caption(cd["notes"])


tab_k, tab_h, tab_t, tab_x, tab_r = st.tabs([
    "📈 Vertical Curves (K)", "🔄 Horizontal Curves (R)", "📐 Turning Radius", "🧱 Cross Section",
    f"🧾 Report ({len(st.session_state.report_data)})",
])

# ---- Vertical curves -----------------------------------------------------------
with tab_k:
    if "k_values" not in cd:
        no_table("K-value")
    else:
        dfk = k_df(cd)
        speeds = list(dfk["Design Speed (km/h)"])
        c1, c2 = st.columns(2)
        curve_type = c1.selectbox("Curve type", ["Crest", "Sag"])
        speed = c2.selectbox("Design speed [km/h]", speeds, index=pick_index(speeds, 100))
        req_k = dfk.loc[dfk["Design Speed (km/h)"] == speed, f"{curve_type} K"].values[0]
        req_k = int(req_k) if float(req_k).is_integer() else float(req_k)

        st.markdown(metric("Required minimum K-value", req_k), unsafe_allow_html=True)
        st.write("")
        if st.button("➕ Add to report", type="primary", key="add_k"):
            add_item({"code": code, "tool": "K-Value", "curve_type": curve_type, "speed": int(speed), "k_value": req_k})

        st.markdown(f"##### Reference table · {cd['k_values'].get('source', '')}")
        st.dataframe(highlight(dfk, lambda r: r["Design Speed (km/h)"] == speed, [f"{curve_type} K"]),
                     hide_index=True, use_container_width=True, height=35 * (len(dfk) + 1) + 3)

# ---- Horizontal curves ---------------------------------------------------------
with tab_h:
    if "horizontal" not in cd:
        no_table("horizontal radius")
    else:
        dfh = h_df(cd)
        h_speeds = [c for c in dfh.columns if c != "e (%)"]
        e_list = dfh["e (%)"].tolist()
        st.caption(f"{cd['horizontal'].get('source', '')}: {cd['horizontal'].get('title', '')}")
        c1, c2 = st.columns(2)
        v_design = c1.selectbox("Design speed (Vd) [km/h]", h_speeds, index=pick_index(h_speeds, "50"))
        e_val = c2.selectbox("Superelevation (e) [%]", e_list, index=pick_index(e_list, 0.0))
        radius = dfh.loc[dfh["e (%)"] == e_val, v_design].values[0]
        radius = int(radius) if float(radius).is_integer() else float(radius)

        st.markdown(metric("Minimum curve radius (R)", f"{radius} m"), unsafe_allow_html=True)
        st.write("")
        if st.button("➕ Add to report", type="primary", key="add_h"):
            add_item({"code": code, "tool": "Horizontal Radius", "speed": v_design, "e_val": str(e_val),
                      "radius": radius})

        st.markdown(f"##### {cd['horizontal'].get('source', 'Table')}")
        show = dfh.rename(columns={c: f"{c} km/h" for c in h_speeds})
        st.dataframe(
            highlight(show, lambda r: r["e (%)"] == e_val, [f"{v_design} km/h"]).format({"e (%)": "{:.1f}"}),
            hide_index=True, use_container_width=True, height=35 * (len(show) + 1) + 3)

# ---- Turning radius ------------------------------------------------------------
with tab_t:
    if "turning" not in cd:
        no_table("turning radius")
    else:
        dft = t_df(cd)
        names = dft["Design Vehicle Type"] + " (" + dft["Symbol"] + ")"
        selected_display = st.selectbox("Design vehicle", names)
        selected_symbol = selected_display.split("(")[-1].replace(")", "")
        v = dft[dft["Symbol"] == selected_symbol].iloc[0]

        m1, m2, m3 = st.columns(3)
        m1.markdown(metric("Min design radius", f"{v['Min Design Turning Radius (m)']} m"), unsafe_allow_html=True)
        m2.markdown(metric("Centerline radius (CTR)", f"{v['Centerline Radius (CTR) (m)']} m"), unsafe_allow_html=True)
        m3.markdown(metric("Min inside radius", f"{v['Min Inside Radius (m)']} m"), unsafe_allow_html=True)
        st.write("")
        if st.button("➕ Add to report", type="primary", key="add_t"):
            add_item({"code": code, "tool": "Turning Radius", "vehicle_name": v["Design Vehicle Type"],
                      "symbol": selected_symbol, "min_r": float(v["Min Design Turning Radius (m)"]),
                      "ctr": float(v["Centerline Radius (CTR) (m)"]), "inside_r": float(v["Min Inside Radius (m)"])})

        img = image_path(v["image"])
        if img:
            st.image(str(img), caption=f"{selected_symbol} turning path", width=620)
        st.markdown(f"##### Design vehicles · {cd['turning'].get('source', '')}")
        st.dataframe(highlight(dft.drop(columns=["image"]), lambda r: r["Symbol"] == selected_symbol,
                               ["Min Design Turning Radius (m)"]).format(precision=2),
                     hide_index=True, use_container_width=True)

# ---- Typical cross section -------------------------------------------------------
with tab_x:
    st.caption("Urban typical cross section. The sketch updates as you change the inputs. "
               "Widths in metres, cross-falls in % (positive = falls away from the centre). "
               "Lane 1 is the lane nearest the centre line or median. "
               "Name a lane 'Bus lane' or 'Cycle lane' and it gets its own colour and vehicle.")
    col_in, col_out = st.columns([1, 1.5], gap="large")

    with col_in:
        xs_name = st.text_input("Section name", "Typical Section A", key="xs_name")
        with st.expander("General", expanded=True):
            divided = st.toggle("Divided carriageway (with median)", value=True, key="xs_div")
            median = st.number_input("Median width (m)", 0.0, 30.0, 3.0, 0.1, key="xs_med", disabled=not divided)
        mirror = st.checkbox("Same on both sides (mirror the right side)", value=True, key="xs_mirror")

        def side_inputs(label, key, expanded):
            with st.expander(label, expanded=expanded):
                n = int(st.number_input("Number of lanes", 1, 6, 2, 1, key=f"xs_{key}_lanes"))
                same = st.checkbox("Same width for all lanes", value=True, key=f"xs_{key}_same")
                common = st.number_input("Lane width (m)", 2.5, 5.0, 3.5, 0.05, key=f"xs_{key}_lw",
                                         disabled=not same)
                names, widths = [], []
                for i in range(n):
                    c1, c2 = st.columns([3, 2])
                    names.append(c1.text_input(f"Lane {i + 1} name", f"Lane {i + 1}", key=f"xs_{key}_ln{i}"))
                    if same:
                        widths.append(common)
                    else:
                        widths.append(c2.number_input(f"Lane {i + 1} width (m)", 2.5, 5.0, 3.5, 0.05,
                                                      key=f"xs_{key}_lw{i}"))
                ptype = st.selectbox("Parking", ["None", "Parallel", "Perpendicular"], key=f"xs_{key}_ptype")
                pwidth = st.number_input("Parking width / depth (m)", 1.0, 8.0, 2.5 if ptype != "Perpendicular" else 5.0,
                                         0.1, key=f"xs_{key}_pw_{ptype}", disabled=ptype == "None")
                inner = st.number_input("Inner shoulder (m)", 0.0, 6.0, 0.0, 0.1, key=f"xs_{key}_in",
                                        disabled=not divided)
                outer = st.number_input("Outer shoulder (m)", 0.0, 6.0, 0.0, 0.1, key=f"xs_{key}_out")
                foot = st.number_input("Footpath (m)", 0.0, 8.0, 2.0, 0.1, key=f"xs_{key}_foot")
                verge = st.number_input("Verge / landscape strip (m)", 0.0, 10.0, 0.0, 0.1, key=f"xs_{key}_verge")
            return {"lane_widths": [float(x) for x in widths], "lane_names": names,
                    "parking": {"type": ptype, "width": float(pwidth) if ptype != "None" else 0.0},
                    "inner_sh": inner, "outer_sh": outer, "footpath": foot, "verge": verge}

        right_side = side_inputs("Right side", "r", True)
        left_side = right_side if mirror else side_inputs("Left side", "l", True)

        with st.expander("Pavement layers (set 0 if a layer does not exist)", expanded=False):
            t_asp = st.number_input("Asphalt thickness (mm)", 0, 1000, 100, 10, key="xs_asp")
            t_base = st.number_input("Base thickness (mm)", 0, 1500, 200, 10, key="xs_base")
            t_sub = st.number_input("Subbase thickness (mm)", 0, 1500, 300, 10, key="xs_sub")
            st.caption("Layers are drawn under lanes, shoulders and parking. Values are placeholders, not from a design code.")

        with st.expander("Cross-falls", expanded=False):
            sc = st.number_input("Carriageway and parking cross-fall (%)", 0.0, 8.0, 2.0, 0.1, key="xs_sc")
            ss = st.number_input("Shoulder cross-fall (%)", 0.0, 10.0, 2.0, 0.1, key="xs_ss")
            sf = st.number_input("Footpath / verge cross-fall (%)", 0.0, 8.0, 2.0, 0.1, key="xs_sf")
            kerb = st.number_input("Kerb height at footpath (m)", 0.0, 0.5, 0.15, 0.01, key="xs_kerb")

        view = st.radio("View", ["2D section", "3D view"], horizontal=True, key="xs_view")
        vehicles = st.toggle("Show vehicles", value=True, key="xs_veh")
        ve = st.slider("Height exaggeration (display only)", 1, 10, 3, key="xs_ve")

    layers = {"asphalt": int(t_asp), "base": int(t_base), "subbase": int(t_sub)}
    params = {"divided": bool(divided), "median": float(median), "mirror": bool(mirror),
              "right": right_side, "left": left_side, "sc": float(sc), "ss": float(ss), "sf": float(sf),
              "kerb": float(kerb), "ve": int(ve), "layers": layers, "vehicles": bool(vehicles)}
    segs = build_section(params)
    tot = section_totals(segs)

    with col_out:
        if not segs:
            st.info("Add at least one lane to see the section.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Lanes", tot["lanes"])
            m2.metric("Carriageway (m)", f"{tot['carriageway']:.2f}")
            m3.metric("Paved incl. shoulders (m)", f"{tot['paved']:.2f}")
            m4, m5, m6 = st.columns(3)
            m4.metric("Median (m)", f"{tot['median']:.2f}")
            m5.metric("Parking (m)", f"{tot['parking']:.2f}")
            m6.metric("Footpaths (m)", f"{tot['footpath']:.2f}")
            m7, m8, _ = st.columns(3)
            m7.metric("Total width (m)", f"{tot['overall']:.2f}")
            m8.metric("Pavement depth (mm)", f"{sum(t for _, t in layer_list(layers)):g}")

            if view == "2D section":
                fig2d = draw_section(segs, ve, layers, vehicles)
                st.pyplot(fig2d, use_container_width=True)
                plt.close(fig2d)
            else:
                st.plotly_chart(make_3d(segs, ve, layers, vehicles), use_container_width=True)

            with st.expander("Element table"):
                st.dataframe(pd.DataFrame([{"Element": s["name"], "Width (m)": round(s["width"], 2),
                                            "Cross-fall (%)": crossfall_text(s)}
                                           for s in segs if s["kind"] != "kerb"]),
                             hide_index=True, use_container_width=True)
            if st.button("➕ Add to report", type="primary", key="add_x"):
                add_item({"tool": "Cross Section", "name": xs_name.strip() or "Typical section", "params": params})

# ---- Report ----------------------------------------------------------------------
with tab_r:
    items = st.session_state.report_data
    p1, p2 = st.columns(2)
    project = p1.text_input("Project name", key="proj_name")
    prepared_by = p2.text_input("Prepared by", key="proj_by")

    if not items:
        st.info("Nothing in the report yet. Use the ➕ Add to report buttons in the other tabs.")
    else:
        for it in items:
            title, detail = describe(it)
            with st.container(border=True):
                a, b = st.columns([8, 1])
                a.markdown(f"{title}  \n{detail}")
                b.button("🗑️", key=f"rm_{it['id']}", on_click=remove_item, args=(it["id"],),
                         help="Remove from report", use_container_width=True)
        d1, d2 = st.columns([3, 1])
        try:
            d1.download_button("⬇️ Download calculation note (Word)", docx_bytes(items, CODES, project, prepared_by),
                               "Calculation_Note.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               type="primary", use_container_width=True)
        except Exception as e:  # keep the page usable if the note cannot be built
            d1.error(f"Could not build the Word file: {e}")
        d2.button("Clear all", on_click=clear_items, use_container_width=True)

st.markdown('<div class="disclaimer">⚠️ Preliminary values from the tool tables. '
            'Verify against the governing design code.</div>', unsafe_allow_html=True)
