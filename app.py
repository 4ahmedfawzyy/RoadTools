"""CO-BODR Highway Design Wizard - engine (no Streamlit code in here).

* DATA                  : code tables (AASHTO / Abu Dhabi / MOMRA)
* get_reference_images  : code-table screenshots with a red rectangle on the selected row
* draw_section_2d / 3d  : typical cross-section sketches (PNG bytes)
* build_report          : Word calculation note
"""
import datetime
import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from matplotlib.patches import Patch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIRS = [os.path.join(BASE_DIR, "assets"), BASE_DIR]
ADM = "Abu Dhabi (ADM)"

# --------------------------------------------------------------------------
# DATA
# --------------------------------------------------------------------------
_K_CREST = {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124}
_K_SAG = {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}

DATA = {
    "AASHTO": {
        "k_crest": dict(_K_CREST),
        "k_sag": dict(_K_SAG),
        "vehicles": pd.DataFrame({
            "Name": ["Passenger Car", "Single-Unit Truck", "Intercity Bus", "WB-12", "WB-20"],
            "Symbol": ["P", "SU-12", "BUS-12", "WB-12", "WB-20"],
            "Min_R": [7.26, 15.60, 12.70, 12.16, 13.66],
            "Inside_R": [4.39, 11.09, 7.41, 5.88, 0.59]}),
    },
    ADM: {
        "k_crest": {**_K_CREST, 140: 161},
        "k_sag": {**_K_SAG, 140: 84},
        # Table 2-8
        "vehicles": pd.DataFrame({
            "Name": ["Passenger Car", "Single Unit Truck", "Single Unit Truck", "City Transit Bus",
                     "Intermediate Semitrailer", "Intermediate Semitrailer", "Interstate Semitrailer",
                     "Double Trailer Combination"],
            "Symbol": ["P", "SU-9", "SU-12", "CITY-BUS", "WB-12", "WB-15", "WB-20", "WB-33D"],
            "Min_R": [7.26, 12.73, 15.60, 12.50, 12.16, 13.66, 13.66, 18.25],
            "Inside_R": [4.39, 8.64, 11.09, 5.30, 5.88, 5.20, 0.59, 4.19]}),
        # Table 9-9 (low-speed urban streets, e_max = 4 %)
        "min_radius": {
            30: dict(e=4.0, f=0.28, calc=22.1, design=22),
            40: dict(e=4.0, f=0.23, calc=46.7, design=47),
            50: dict(e=4.0, f=0.19, calc=85.6, design=86),
            60: dict(e=4.0, f=0.17, calc=135.0, design=135),
            70: dict(e=4.0, f=0.15, calc=203.1, design=203)},
        # Clause 6.2.3
        "grade": {
            "uncurbed": dict(label="Uncurbed roadway", value=0.0),
            "curbed_local": dict(label="Curbed - local road / collector", value=0.2),
            "curbed_arterial": dict(label="Curbed - arterial / freeway / expressway", value=0.3)},
    },
    "MOMRA": {
        "k_crest": {k: v for k, v in _K_CREST.items() if k >= 30},
        "k_sag": {k: v for k, v in _K_SAG.items() if k >= 30},
        "vehicles": pd.DataFrame({
            "Name": ["سيارة ركوب صغيرة", "شاحنة وحدة مفردة", "حافلة", "شاحنة بمقطورة متوسطة", "شاحنة بمقطورة كبيرة"],
            "Symbol": ["P", "SU", "BUS-12", "WB-12", "WB-20"],
            "Min_R": [7.26, 12.73, 12.70, 12.16, 13.66],
            "Inside_R": [4.39, 8.64, 7.41, 5.88, 0.59]}),
    },
}

# --------------------------------------------------------------------------
# Screenshots (file names tried in order, in ./assets then next to this file)
# --------------------------------------------------------------------------
ADM_FILES = {
    "k_crest": ["K-Value_Crest.png", "K-Value Crest.png"],
    "k_sag": ["K-Value_Sag.png", "K-Value Sag.png"],
    "grade": ["Min__Grade.png", "Min. Grade.png", "Min Grade.png"],
    "h_radius": ["Min__Horizontal_Radius.png", "Min. Horizontal Radius.png", "Min Horizontal Radius.png"],
    "turning": ["Turning_Radius.png", "Turning Radius.png"],
}

# Old (un-highlighted) pictures, still used for the other codes until their screenshots are added
LEGACY_K = {"MOMRA": {"k_crest": "Min. K-Value Crest.png", "k_sag": "Min. K-Value Sag.png"}}
LEGACY_VEHICLE = {
    "P": ["Min. Turning Radius Passenger Car.png", "Passenger Car Turning Radius.png"],
    "SU": ["Min. Turning Radius SU.png"], "SU-9": ["Min. Turning Radius SU.png"],
    "SU-12": ["Min. Turning Radius SU.png", "SU-12 Turning Radius.png"],
    "CITY-BUS": ["Min. Turning Radius BUS-12.png"], "BUS-12": ["Min. Turning Radius BUS-12.png", "BUS-12 Turning Radius.png"],
    "WB-12": ["Min. Turning Radius WB-12.png", "WB-12 Turning Radius.png"],
    "WB-15": ["Min. Turning Radius WB-20.png"], "WB-20": ["Min. Turning Radius WB-20.png", "WB-20 Turning Radius.png"],
    "WB-33D": ["Min. Turning Radius WB-20.png"],
}


def find_asset(names):
    if isinstance(names, str):
        names = [names]
    for d in ASSET_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


# --------------------------------------------------------------------------
# Red-rectangle geometry (pixel coordinates of the Abu Dhabi screenshots)
# --------------------------------------------------------------------------
K_SPEEDS = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140]
_CREST_Y = [105, 128, 150, 172, 195, 217, 239, 261, 283, 306, 328, 350, 372, 395]
_CREST_X = [22, 133, 276, 396, 524]
_SAG_Y = [105, 130, 154, 178, 202, 225, 249, 273, 297, 321, 345, 368, 392, 416]
_SAG_X = [10, 122, 243, 369, 509]
_TURN_SYMBOLS = ["P", "SU-9", "SU-12", "CITY-BUS", "WB-12", "WB-15", "WB-20", "WB-33D"]
_TURN_Y = [81, 106, 141, 170, 209, 248, 288, 327, 366]
_TURN_X = [12, 139, 222, 325, 428, 530]
_HR_SPEEDS = [30, 40, 50, 60, 70]
_HR_X = [13, 149, 235, 331, 428, 596, 746]
_HR_Y0, _HR_H = 104.9, 19.25
_GRADE_BOXES = {
    "uncurbed": [(70, 103, 935, 213, 3)],
    "curbed_local": [(70, 233, 935, 343, 2), (124, 289, 540, 314, 3)],
    "curbed_arterial": [(70, 233, 935, 343, 2), (544, 289, 932, 314, 3), (124, 321, 258, 343, 3)],
}
RED = (214, 0, 0)


def _highlight(path, boxes, scale=3):
    """Draw red rectangles (x0, y0, x1, y1, thickness) on a screenshot; returns PNG bytes."""
    im = Image.open(path).convert("RGB")
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1, t in boxes:
        d.rectangle([x0 * scale, y0 * scale, x1 * scale, y1 * scale], outline=RED, width=t * 2)
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def _row_boxes(speed, ys, xs, value_col):
    i = K_SPEEDS.index(speed)
    y0, y1 = ys[i], ys[i + 1]
    return [(xs[0] + 1, y0 + 1, xs[-1] - 1, y1 - 1, 2),
            (xs[value_col] + 2, y0 + 2, xs[value_col + 1] - 2, y1 - 2, 3)]


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def get_reference_images(code, speed, symbol, grade_key=None):
    """Returns {key: dict(title, caption, bytes|None, highlighted, missing)} for the report and the UI."""
    out = {}

    def add(key, title, caption, path, boxes=None, legacy=False):
        if path is None:
            out[key] = dict(title=title, caption=caption, bytes=None, highlighted=False,
                            missing=ADM_FILES.get(key, [""])[0] if code == ADM else "")
        elif boxes:
            out[key] = dict(title=title, caption=caption, bytes=_highlight(path, boxes), highlighted=True, missing=None)
        else:
            out[key] = dict(title=title, caption=caption, bytes=_read(path), highlighted=False, missing=None)

    if code == ADM:
        if speed in K_SPEEDS:
            p = find_asset(ADM_FILES["k_crest"])
            add("k_crest", "Table 6-2: K Values for Crest Vertical Curves",
                f"Highlighted: design speed {speed} km/h.", p, _row_boxes(speed, _CREST_Y, _CREST_X, 3) if p else None)
            p = find_asset(ADM_FILES["k_sag"])
            add("k_sag", "Table 6-6: K Values for Sag Vertical Curves",
                f"Highlighted: design speed {speed} km/h.", p, _row_boxes(speed, _SAG_Y, _SAG_X, 3) if p else None)
        if grade_key in _GRADE_BOXES:
            p = find_asset(ADM_FILES["grade"])
            add("grade", "Clause 6.2.3: Minimum Grades", "Highlighted: applicable road type.",
                p, _GRADE_BOXES[grade_key] if p else None)
        if speed in _HR_SPEEDS:
            p = find_asset(ADM_FILES["h_radius"])
            i = _HR_SPEEDS.index(speed)
            y0 = _HR_Y0 + _HR_H * i
            boxes = [(_HR_X[0] + 1, y0, _HR_X[-1] - 1, y0 + _HR_H, 2),
                     (_HR_X[5] + 2, y0 + 1, _HR_X[6] - 2, y0 + _HR_H - 1, 3)]
            add("h_radius", "Table 9-9: Minimum Radii on Low-Speed Urban Streets",
                f"Highlighted: design speed {speed} km/h.", p, boxes if p else None)
        if symbol in _TURN_SYMBOLS:
            p = find_asset(ADM_FILES["turning"])
            i = _TURN_SYMBOLS.index(symbol)
            y0, y1 = _TURN_Y[i], _TURN_Y[i + 1]
            boxes = [(_TURN_X[0] + 1, y0 + 1, _TURN_X[-1] - 1, y1 - 1, 2),
                     (_TURN_X[2] + 2, y0 + 2, _TURN_X[3] - 2, y1 - 2, 3),
                     (_TURN_X[4] + 2, y0 + 2, _TURN_X[5] - 2, y1 - 2, 3)]
            add("turning", "Table 2-8: Minimum Turning Radii of Design Vehicles",
                f"Highlighted: design vehicle {symbol}.", p, boxes if p else None)
    else:
        legacy = LEGACY_K.get(code, {})
        for key, title in (("k_crest", "Crest K-Value (code reference)"), ("k_sag", "Sag K-Value (code reference)")):
            if key in legacy:
                p = find_asset(legacy[key])
                if p:
                    add(key, title, "Code reference table.", p)
        for n in LEGACY_VEHICLE.get(symbol, []):
            p = find_asset(n)
            if p:
                add("turning", "Vehicle Turning Path (code reference)", "Code reference figure.", p)
                break
    return out


# --------------------------------------------------------------------------
# Cross-section sketches
# --------------------------------------------------------------------------
COLORS = {"sw": "#aab2b8", "park": "#e0a030", "lane": "#3b4450", "median": "#6fbf73"}
NAMES = {"sw": "Sidewalk / Shoulder", "park": "Parking", "lane": "Lane", "median": "Median"}
SHORT = {"sw": "SW", "park": "Park", "lane": "Lane", "median": "Median"}


def section_items(p):
    items = [("sw", p["l_sw"]), ("park", p["l_park"])]
    items += [("lane", p["l_width"])] * int(p["l_lanes"])
    items.append(("median", p["median"]))
    items += [("lane", p["r_width"])] * int(p["r_lanes"])
    items += [("park", p["r_park"]), ("sw", p["r_sw"])]
    return [(k, w) for k, w in items if w > 0]


def section_total(p):
    return sum(w for _, w in section_items(p))


def _to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _empty_fig(msg):
    fig, ax = plt.subplots(figsize=(8, 1.5))
    ax.text(0.5, 0.5, msg, ha="center", va="center")
    ax.axis("off")
    return _to_png(fig)


def draw_section_2d(p):
    items = section_items(p)
    W = sum(w for _, w in items)
    if W <= 0:
        return _empty_fig("Add at least one element to see the section")
    fig, ax = plt.subplots(figsize=(12, 3.8), dpi=150)
    x = 0.0
    for kind, w in items:
        h = 0.6 if kind in ("sw", "median") else 0.0
        ax.add_patch(Rectangle((x, -0.5), w, 0.5 + h, fc=COLORS[kind], ec="#222", lw=0.8))
        label = SHORT[kind] if w < 2.0 else NAMES[kind]
        if w >= 1.0:
            ax.text(x + w / 2, h + 0.12, label, ha="center", va="bottom", fontsize=8, color="#222")
        # segment dimension
        ax.annotate("", xy=(x, -0.95), xytext=(x + w, -0.95),
                    arrowprops=dict(arrowstyle="<->", lw=0.8, color="#555", shrinkA=0, shrinkB=0))
        ax.text(x + w / 2, -1.05, f"{w:g}", ha="center", va="top", fontsize=8, color="#333")
        x += w
    # centre line
    xcl = p["l_sw"] + p["l_park"] + p["l_lanes"] * p["l_width"] + p["median"] / 2
    if p["l_lanes"] == 0 or p["r_lanes"] == 0:
        xcl = None
    if xcl is not None:
        ax.plot([xcl, xcl], [-0.5, 1.5], ls="-.", lw=0.9, color="#c0392b")
        ax.text(xcl, 1.55, "C/L", ha="center", va="bottom", fontsize=8, color="#c0392b")
    # overall dimension
    ax.annotate("", xy=(0, -1.95), xytext=(W, -1.95),
                arrowprops=dict(arrowstyle="<->", lw=1.1, color="#007bff", shrinkA=0, shrinkB=0))
    ax.text(W / 2, -2.05, f"Total ROW = {W:.2f} m", ha="center", va="top", fontsize=10,
            color="#007bff", fontweight="bold")
    ax.text(0, -2.75, "Dimensions in metres. Vertical scale exaggerated.", fontsize=7, color="#777", va="top")
    ax.set_xlim(-0.5, W + 0.5)
    ax.set_ylim(-2.9, 2.1)
    ax.axis("off")
    return _to_png(fig)


def _box(ax, x0, x1, y0, y1, z0, z1, color):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [[v[i] for i in f] for f in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
                                          (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4))]
    ax.add_collection3d(Poly3DCollection(faces, facecolors=color, edgecolors="#222", linewidths=0.4))


def draw_section_3d(p, length=18.0):
    items = section_items(p)
    W = sum(w for _, w in items)
    if W <= 0:
        return _empty_fig("Add at least one element to see the section")
    fig = plt.figure(figsize=(10, 5.4), dpi=130)
    ax = fig.add_subplot(111, projection="3d")
    x, lanes_seen, marks = 0.0, 0, []
    for i, (kind, w) in enumerate(items):
        top = 0.45 if kind in ("sw", "median") else 0.0
        _box(ax, x, x + w, 0, length, -0.3, top, COLORS[kind])
        x += w
        if kind == "lane":
            lanes_seen += 1
            nxt = items[i + 1][0] if i + 1 < len(items) else None
            if nxt == "lane":
                marks.append((x, lanes_seen == p["l_lanes"]))   # (x, opposing directions meet)
    for mx, solid in marks:                                   # lane markings as thin boxes on top
        if solid:
            _box(ax, mx - 0.08, mx + 0.08, 0, length, 0, 0.03, "#f1c40f")
        else:
            y = 0.0
            while y < length:
                _box(ax, mx - 0.06, mx + 0.06, y, min(y + 1.5, length), 0, 0.03, "white")
                y += 4.5
    ax.set_xlim(0, W)
    ax.set_ylim(0, length)
    ax.set_zlim(-0.4, 1.0)
    try:
        ax.set_box_aspect((W, length, max(2.0, W * 0.12)), zoom=1.5)
    except TypeError:
        ax.set_box_aspect((W, length, max(2.0, W * 0.12)))
    ax.view_init(elev=24, azim=-68)
    ax.set_axis_off()
    present = []
    for k, _ in items:
        if k not in present:
            present.append(k)
    fig.legend(handles=[Patch(fc=COLORS[k], ec="#222", label=NAMES[k]) for k in present],
               loc="lower center", ncol=len(present), frameon=False, fontsize=9)
    fig.suptitle(f"Total ROW = {W:.2f} m", fontsize=11, color="#007bff", fontweight="bold")
    return _to_png(fig)


# --------------------------------------------------------------------------
# Word report
# --------------------------------------------------------------------------
def _table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, header):
        c.text = ""
        run = c.paragraphs[0].add_run(h)
        run.bold = True
    for r in rows:
        cells = t.add_row().cells
        for c, v in zip(cells, r):
            c.text = str(v)
    return t


def _picture(doc, data, width, caption=None):
    doc.add_picture(io.BytesIO(data), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(caption)
        run.italic = True
        run.font.size = Pt(9)


def _add_reference(doc, img):
    if img is None:
        return
    if img["bytes"]:
        _picture(doc, img["bytes"], 5.9, f"{img['title']} - {img['caption']}")
    else:
        doc.add_paragraph(f"[Reference screenshot not found: {img['missing']}]")


def build_report(*, project, designer, code, speed, k_crest, k_sag, veh, grade_label, grade_value,
                 radius, images, sections):
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(0.9)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    logo = find_asset(["logo.png"])
    if logo:
        doc.add_picture(logo, width=Inches(1.3))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_heading("Highway Design Calculation Note", 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    info = doc.add_paragraph(f"Project Name: {project}\nDesigned By: {designer}\n"
                             f"Date: {datetime.datetime.now():%Y-%m-%d}\nCode Reference: {code}")
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    n = 1
    doc.add_heading(f"{n}. Vertical Alignment (K-Values)", 1)
    _table(doc, ["Design Speed", "Crest K-Value", "Sag K-Value"], [[f"{speed} km/h", k_crest, k_sag]])
    doc.add_paragraph()
    _add_reference(doc, images.get("k_crest"))
    _add_reference(doc, images.get("k_sag"))

    if grade_label is not None:
        n += 1
        doc.add_heading(f"{n}. Minimum Longitudinal Grade", 1)
        _table(doc, ["Road Type", "Minimum Grade"], [[grade_label, f"{grade_value:.1f} %"]])
        doc.add_paragraph()
        _add_reference(doc, images.get("grade"))

    if radius is not None:
        n += 1
        doc.add_heading(f"{n}. Minimum Horizontal Radius", 1)
        _table(doc, ["Design Speed", "e max", "f max", "Calculated R min (m)", "Design R (m)"],
               [[f"{speed} km/h", f"{radius['e']:.1f} %", radius["f"], radius["calc"], radius["design"]]])
        doc.add_paragraph()
        _add_reference(doc, images.get("h_radius"))

    n += 1
    doc.add_heading(f"{n}. Vehicle Turning Radius", 1)
    _table(doc, ["Design Vehicle", "Min Design Radius (m)", "Min Inside Radius (m)"],
           [[f"{veh['Name']} ({veh['Symbol']})", veh["Min_R"], veh["Inside_R"]]])
    doc.add_paragraph()
    _add_reference(doc, images.get("turning"))

    n += 1
    doc.add_heading(f"{n}. Typical Cross Sections", 1)
    if not sections:
        doc.add_paragraph("No cross sections were added.")
    for cs in sections:
        doc.add_heading(f"Section: {cs['name']}", 2)
        _table(doc, ["Element", "Details"], [
            ["Left Direction", f"{cs['l_lanes']} lanes @ {cs['l_width']} m, parking {cs['l_park']} m, "
                               f"sidewalk/shoulder {cs['l_sw']} m"],
            ["Median", f"{cs['median']} m"],
            ["Right Direction", f"{cs['r_lanes']} lanes @ {cs['r_width']} m, parking {cs['r_park']} m, "
                                f"sidewalk/shoulder {cs['r_sw']} m"],
            ["Total ROW Width", f"{cs['total_row']:.2f} m"]])
        doc.add_paragraph()
        _picture(doc, cs["png2d"], 6.3, "2D section")
        _picture(doc, cs["png3d"], 5.2, "3D view")

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
