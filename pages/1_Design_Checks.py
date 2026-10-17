import hashlib
import io
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import nearest_points

try:
    from defusedxml import ElementTree as ET  # safe against malicious XML
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET

st.set_page_config(page_title="Road Design Review & Checker Tool", page_icon="🔍", layout="wide")

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .block-container { padding-top: 1.6rem; max-width: 1400px; }
        .hero {
            background: linear-gradient(135deg, #1F3864 0%, #2E5C9A 100%);
            padding: 1.5rem 2rem; border-radius: 14px; margin-bottom: 1.4rem;
            box-shadow: 0 4px 14px rgba(0,0,0,.18);
        }
        .hero-title { color: #fff; font-size: 1.9rem; font-weight: 700; line-height: 1.2; }
        .hero-sub { color: rgba(255,255,255,.85); font-size: .98rem; margin-top: .35rem; }
        .step-title { display: flex; align-items: center; gap: .65rem; font-size: 1.2rem;
                      font-weight: 600; margin: .1rem 0 .7rem; }
        .step-badge { background: #2E5C9A; color: #fff; min-width: 1.8rem; height: 1.8rem; border-radius: 50%;
                      display: inline-flex; align-items: center; justify-content: center; font-size: .92rem; }
        .sub-title { font-size: 1rem; font-weight: 600; margin: 1rem 0 .4rem; opacity: .9; }
        [data-testid="stMetric"] { background: rgba(128,128,128,.08); border: 1px solid rgba(128,128,128,.22);
                                   border-radius: 10px; padding: .7rem 1rem; }
        [data-testid="stMetricLabel"] { opacity: .75; }
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

if st.sidebar.button("🏠 Home", use_container_width=True, type="primary"):
    st.switch_page("app.py")

# ----------------------------------------------------------------------------
# Criteria
# ----------------------------------------------------------------------------
AASHTO_DB = {
    20: {"min_radius": 15, "max_grade": {"Level": 9, "Rolling": 10, "Mountainous": 12}, "k_crest": 1, "k_sag": 3},
    30: {"min_radius": 25, "max_grade": {"Level": 8, "Rolling": 9, "Mountainous": 11}, "k_crest": 2, "k_sag": 4},
    40: {"min_radius": 45, "max_grade": {"Level": 7, "Rolling": 8, "Mountainous": 10}, "k_crest": 4, "k_sag": 6},
    50: {"min_radius": 85, "max_grade": {"Level": 6, "Rolling": 7, "Mountainous": 8}, "k_crest": 7, "k_sag": 11},
    60: {"min_radius": 125, "max_grade": {"Level": 5, "Rolling": 6, "Mountainous": 7}, "k_crest": 11, "k_sag": 18},
    70: {"min_radius": 175, "max_grade": {"Level": 4, "Rolling": 5, "Mountainous": 6}, "k_crest": 17, "k_sag": 23},
    80: {"min_radius": 230, "max_grade": {"Level": 4, "Rolling": 5, "Mountainous": 6}, "k_crest": 26, "k_sag": 30},
    90: {"min_radius": 300, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 39, "k_sag": 38},
    100: {"min_radius": 435, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 52, "k_sag": 45},
    110: {"min_radius": 570, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 75, "k_sag": 58},
    120: {"min_radius": 750, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 105, "k_sag": 73},
}
SPEEDS = list(AASHTO_DB.keys())

st.sidebar.markdown("## ⚙️ Settings")

with st.sidebar.expander("📏 Design criteria", expanded=True):
    criteria_mode = st.radio("Criteria mode", ["Use Code Standards (AASHTO)", "Manual Custom Limits"])
    manual_limits = {}
    if criteria_mode == "Manual Custom Limits":
        st.caption("Enter your project design limits:")
        manual_limits["max_grade"] = st.number_input("Max longitudinal slope (%)", value=5.0, step=0.5, format="%.2f")
        manual_limits["min_radius"] = st.number_input("Min horizontal radius (m)", value=230.0, step=10.0, format="%.2f")
        manual_limits["min_k_crest"] = st.number_input("Min K-value (crest)", value=26.0, step=1.0, format="%.2f")
        manual_limits["min_k_sag"] = st.number_input("Min K-value (sag)", value=30.0, step=1.0, format="%.2f")

with st.sidebar.expander("📈 Vertical alignment checks", expanded=False):
    chk_min_grade = st.checkbox("Check minimum grade (drainage)", value=False)
    min_grade_val = st.number_input("Min grade (%)", value=0.3, step=0.1, format="%.2f", disabled=not chk_min_grade)
    chk_vc_len = st.checkbox("Check min vertical curve length (0.6 × V)", value=True,
                             help="Uses the design speed selected in Step 1.")
    break_tol = st.number_input("Grade break without curve: flag if A > (%)", value=1.0, step=0.1, format="%.2f")

with st.sidebar.expander("🔀 Intersection checks", expanded=False):
    snap_tol = st.number_input("Plan snap tolerance (m)", value=0.05, step=0.01, format="%.2f",
                               help="Lines closer than this are treated as touching (T-junction endpoints).")
    level_tol = st.number_input("Max level difference (m)", value=0.05, step=0.01, format="%.3f")
    chk_angle = st.checkbox("Check intersection angle", value=True)
    min_angle = st.number_input("Min intersection angle (°)", value=60.0, step=5.0, min_value=0.0, max_value=180.0,
                                format="%.1f", disabled=not chk_angle,
                                help="Two crossing alignments form an angle and its supplement (e.g. 70° and 110°). "
                                     "The check passes if either one is inside the range.")
    max_angle = st.number_input("Max intersection angle (°)", value=90.0, step=5.0, min_value=0.0, max_value=180.0,
                                format="%.1f", disabled=not chk_angle,
                                help="Upper limit of the accepted range (up to 180°), e.g. 60° to 120° or 75° to 105°.")
    if chk_angle and min_angle > max_angle:
        st.error("Min angle must not exceed max angle.")


# ----------------------------------------------------------------------------
# LandXML parsing (cached, returns plain data only)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Parsing LandXML...")
def parse_landxml(data: bytes):
    root = ET.fromstring(data)
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    k = 1.0
    units = "metric"
    u = root.find("Units")
    if u is not None and len(u):
        child = u[0]
        if child.tag.lower() == "imperial":
            lin = child.get("linearUnit", "foot").lower()
            k = 0.3048006096 if "survey" in lin else 0.3048
            units = "imperial (converted to metric)"

    def pt(el, tag):
        e = el.find(tag)
        if e is None or not e.text:
            return None
        v = e.text.split()
        return (float(v[1]) * k, float(v[0]) * k)  # LandXML is "northing easting" -> (E, N)

    import math

    aligns, used = [], {}
    for al in root.iter("Alignment"):
        name = al.get("name", "Unnamed")
        used[name] = used.get(name, 0) + 1
        if used[name] > 1:
            name = f"{name}#{used[name]}"

        sta = float(al.get("staStart", 0)) * k
        elems, hcurves = [], []
        cg = al.find("CoordGeom")
        if cg is not None:
            for el in cg:
                if el.tag not in ("Line", "Curve", "Spiral"):
                    continue
                s, e = pt(el, "Start"), pt(el, "End")
                if s is None or e is None:
                    continue
                pts = [s, e]
                length = float(el.get("length", 0)) * k
                if el.tag == "Line":
                    pass
                elif el.tag == "Curve":
                    c = pt(el, "Center")
                    if c is not None:
                        r = math.hypot(s[0] - c[0], s[1] - c[1])
                        a0 = math.atan2(s[1] - c[1], s[0] - c[0])
                        a1 = math.atan2(e[1] - c[1], e[0] - c[0])
                        cw = el.get("rot", "ccw").lower() == "cw"
                        if cw and a1 > a0:
                            a1 -= 2 * math.pi
                        if not cw and a1 < a0:
                            a1 += 2 * math.pi
                        n = max(int(abs(a1 - a0) * r / 1.0), 4)
                        pts = [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n),
                                c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
                        hcurves.append({"sta": sta, "radius": float(el.get("radius", r / k)) * k, "length": length})
                else:  # Spiral: coarse polyline through the PI
                    pi = pt(el, "PI")
                    if pi is not None:
                        pts = [s, pi, e]
                if length <= 0:
                    length = LineString(pts).length
                elems.append({"pts": pts, "sta0": sta, "len": length, "type": el.tag})
                sta += length

        pvis = []
        for pr in al.findall("Profile"):
            for pa in pr.findall("ProfAlign"):  # design profile only, ProfSurf is existing ground
                cand = []
                for e in pa:
                    if e.tag in ("PVI", "ParaCurve", "UnsymParaCurve", "CircCurve") and e.text:
                        v = e.text.split()
                        if e.tag == "UnsymParaCurve":
                            L = (float(e.get("lengthIn", 0)) + float(e.get("lengthOut", 0))) * k
                        else:
                            L = float(e.get("length", 0)) * k
                        cand.append({"sta": float(v[0]) * k, "elev": float(v[1]) * k, "L": L, "type": e.tag})
                if len(cand) >= 2:
                    pvis = cand
                    break
            if pvis:
                break

        aligns.append({"name": name, "sta_start": float(al.get("staStart", 0)) * k,
                       "elems": elems, "hcurves": hcurves, "pvis": pvis})
    return {"units": units, "alignments": aligns}


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def build_geometry(aligns):
    geo = {}
    for a in aligns:
        parts = [(LineString(e["pts"]), e["sta0"], e["len"]) for e in a["elems"] if len(e["pts"]) >= 2]
        geo[a["name"]] = {
            "parts": parts,
            "multi": MultiLineString([p[0] for p in parts]) if parts else None,
        }
    return geo


def _points_of(g):
    if g.is_empty:
        return []
    if g.geom_type == "Point":
        return [g]
    if hasattr(g, "geoms"):
        out = []
        for sub in g.geoms:
            out += _points_of(sub)
        return out
    return []  # collinear overlaps (lines) are skipped


def station_of(geo_entry, p):
    best = min(geo_entry["parts"], key=lambda t: t[0].distance(p))
    ls, sta0, length = best
    frac = ls.project(p) / ls.length if ls.length else 0
    return sta0 + frac * length


def find_intersections(aligns, geo, snap):
    rows = []
    names = [a["name"] for a in aligns if geo[a["name"]]["multi"] is not None]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            ga, gb = geo[a]["multi"], geo[b]["multi"]
            if ga.intersects(gb):
                pts = _points_of(ga.intersection(gb))
            elif ga.distance(gb) <= snap:
                p1, p2 = nearest_points(ga, gb)
                pts = [Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)]
            else:
                pts = []
            kept = []
            for p in pts:  # de-duplicate points within 1 m
                if all(p.distance(q) > 1.0 for q in kept):
                    kept.append(p)
            for p in kept:
                rows.append({"Alignment A": a, "Alignment B": b,
                             "Easting": round(p.x, 3), "Northing": round(p.y, 3)})
    return rows


# ----------------------------------------------------------------------------
# Profile helpers
# ----------------------------------------------------------------------------
def _g(p0, p1):
    d = p1["sta"] - p0["sta"]
    return (p1["elev"] - p0["elev"]) / d if d else 0.0


def elev_at(sta, pvis):
    if len(pvis) < 2 or sta < pvis[0]["sta"] - 0.01 or sta > pvis[-1]["sta"] + 0.01:
        return None
    sta = min(max(sta, pvis[0]["sta"]), pvis[-1]["sta"])
    for k in range(1, len(pvis) - 1):
        p, L = pvis[k], pvis[k]["L"]
        if L > 0:
            bvc = p["sta"] - L / 2
            if bvc <= sta <= p["sta"] + L / 2:
                gin, gout = _g(pvis[k - 1], p), _g(p, pvis[k + 1])
                x = sta - bvc
                return p["elev"] - gin * L / 2 + gin * x + (gout - gin) * x * x / (2 * L)
    for i in range(len(pvis) - 1):
        p0, p1 = pvis[i], pvis[i + 1]
        if p0["sta"] <= sta <= p1["sta"]:
            return p0["elev"] + _g(p0, p1) * (sta - p0["sta"])
    return None


# ----------------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------------
def check_tangents_and_vcurves(name, pvis, lim):
    tang, vcs = [], []
    for i in range(len(pvis) - 1):
        p0, p1 = pvis[i], pvis[i + 1]
        if p1["sta"] - p0["sta"] <= 0:
            continue
        g = _g(p0, p1) * 100
        status = "Pass"
        if abs(g) > lim["max_grade"]:
            status = f"Violation (exceeds max {lim['max_grade']}%)"
        elif chk_min_grade and abs(g) < min_grade_val:
            status = f"Violation (below min {min_grade_val}%)"
        tang.append({"Alignment": name, "Start Station": round(p0["sta"], 2), "End Station": round(p1["sta"], 2),
                     "Grade (%)": round(g, 3), "Max Allowed (%)": lim["max_grade"], "Status": status})

    for i in range(1, len(pvis) - 1):
        p0, p1, p2 = pvis[i - 1], pvis[i], pvis[i + 1]
        g1, g2 = _g(p0, p1) * 100, _g(p1, p2) * 100
        A = abs(g2 - g1)
        if A < 0.1:
            continue
        kind = "Crest" if g1 > g2 else "Sag"
        L = p1["L"]
        req_k = lim["min_k_crest"] if kind == "Crest" else lim["min_k_sag"]
        row = {"Alignment": name, "PVI Station": round(p1["sta"], 2), "Type": kind, "A (%)": round(A, 2),
               "L (m)": round(L, 2), "K": None, "Required K": req_k, "Status": "Pass"}
        if L <= 0:
            row["Status"] = (f"Violation (grade break, A={A:.2f}% with no curve)" if A > break_tol
                             else "Warning (no vertical curve)")
        else:
            K = L / A
            row["K"] = round(K, 1)
            if K < req_k:
                row["Status"] = f"Violation (K {K:.1f} < {req_k})"
            elif chk_vc_len and lim.get("speed") and L < 0.6 * lim["speed"]:
                row["Status"] = f"Warning (L {L:.0f} m < 0.6V = {0.6 * lim['speed']:.0f} m)"
        vcs.append(row)
    return tang, vcs


def check_horizontal(name, hcurves, lim):
    rows = []
    for c in hcurves:
        ok = c["radius"] >= lim["min_radius"]
        rows.append({"Alignment": name, "Start Station": round(c["sta"], 2), "Radius (m)": round(c["radius"], 2),
                     "Min Required (m)": lim["min_radius"],
                     "Status": "Pass" if ok else f"Violation (R {c['radius']:.0f} < {lim['min_radius']})"})
    return rows


def bearing_at(geo_entry, p):
    """Azimuth (degrees from north, clockwise) of the alignment at the point nearest to p."""
    ls = min(geo_entry["parts"], key=lambda t: t[0].distance(p))[0]
    d = ls.project(p)
    coords = list(ls.coords)
    acc, last = 0.0, None
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg == 0:
            continue
        last = (x0, y0, x1, y1)
        if acc + seg >= d - 1e-9:
            break
        acc += seg
    if last is None:
        return None
    return math.degrees(math.atan2(last[2] - last[0], last[3] - last[1])) % 360


def check_angles(inter_df, geo):
    rows = []
    for _, r in inter_df.iterrows():
        a, b = r["Alignment A"], r["Alignment B"]
        p = Point(r["Easting"], r["Northing"])
        b1, b2 = bearing_at(geo[a], p), bearing_at(geo[b], p)
        row = {"Alignment A": a, "Station A": round(station_of(geo[a], p), 2), "Bearing A (°)": None,
               "Alignment B": b, "Station B": round(station_of(geo[b], p), 2), "Bearing B (°)": None,
               "Intersection Angle (°)": None, "Supplementary (°)": None, "Min Allowed (°)": min_angle, "Max Allowed (°)": max_angle}
        if b1 is None or b2 is None:
            row["Status"] = "Warning (direction could not be determined)"
        else:
            diff = abs(b1 - b2) % 360
            if diff > 180:
                diff = 360 - diff
            ang = min(diff, 180 - diff)  # acute angle
            supp = 180 - ang             # the other angle formed by the same two lines
            row.update({"Bearing A (°)": round(b1, 2), "Bearing B (°)": round(b2, 2),
                        "Intersection Angle (°)": round(ang, 2), "Supplementary (°)": round(supp, 2)})
            in_range = (min_angle - 1e-6 <= ang <= max_angle + 1e-6) or (min_angle - 1e-6 <= supp <= max_angle + 1e-6)
            row["Status"] = "Pass" if in_range else (
                f"Violation (angles {ang:.1f}° / {supp:.1f}° outside {min_angle:.1f}°-{max_angle:.1f}°)")
        row.update({"Easting": r["Easting"], "Northing": r["Northing"]})
        rows.append(row)
    return rows


def check_levels(inter_df, geo, aligns_by_name):
    rows = []
    for _, r in inter_df.iterrows():
        a, b = r["Alignment A"], r["Alignment B"]
        p = Point(r["Easting"], r["Northing"])
        sa, sb = station_of(geo[a], p), station_of(geo[b], p)
        za = elev_at(sa, aligns_by_name[a]["pvis"])
        zb = elev_at(sb, aligns_by_name[b]["pvis"])
        row = {"Alignment A": a, "Station A": round(sa, 2), "Level A": None if za is None else round(za, 3),
               "Alignment B": b, "Station B": round(sb, 2), "Level B": None if zb is None else round(zb, 3),
               "Δ Level (m)": None}
        if za is None or zb is None:
            row["Status"] = "Warning (no design profile at this station)"
        else:
            d = abs(za - zb)
            row["Δ Level (m)"] = round(d, 3)
            row["Status"] = "Pass" if d <= level_tol else f"Violation (levels differ by {d:.3f} m, tol {level_tol} m)"
        row.update({"Easting": r["Easting"], "Northing": r["Northing"]})
        rows.append(row)
    return rows


def build_excel(audit):
    """Formatted Excel report: summary sheet + one styled sheet per check table."""
    from xlsxwriter.utility import xl_col_to_name

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        wb = w.book
        title_f = wb.add_format({"bold": True, "font_size": 16, "font_color": "#1F3864"})
        note_f = wb.add_format({"italic": True, "font_color": "#555555"})
        hdr = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1F3864", "border": 1,
                             "align": "center", "valign": "vcenter", "text_wrap": True})
        txt = wb.add_format({"border": 1, "valign": "vcenter"})
        n2 = wb.add_format({"border": 1, "valign": "vcenter", "num_format": "0.00"})
        n3 = wb.add_format({"border": 1, "valign": "vcenter", "num_format": "0.000"})
        cnt = wb.add_format({"border": 1, "align": "center"})
        red = wb.add_format({"bg_color": "#F8D7DA", "font_color": "#721C24"})
        amber = wb.add_format({"bg_color": "#FFF3CD", "font_color": "#856404"})
        green = wb.add_format({"bg_color": "#D4EDDA", "font_color": "#155724"})

        # Summary sheet (first tab)
        ws = wb.add_worksheet("Summary")
        w.sheets["Summary"] = ws
        ws.write(0, 0, "LandXML Design Audit Report", title_f)
        ws.write(1, 0, "Preliminary check based on simplified criteria. Verify against the governing design code.", note_f)
        for c, h in enumerate(["Check", "Total", "Pass", "Warnings", "Violations"]):
            ws.write(3, c, h, hdr)
        r = 4
        for name, df in audit.items():
            st_ = df["Status"] if not df.empty else pd.Series(dtype=str)
            ws.write(r, 0, name, txt)
            ws.write(r, 1, len(st_), cnt)
            ws.write(r, 2, int((st_ == "Pass").sum()), cnt)
            ws.write(r, 3, int(st_.str.startswith("Warning").sum()), cnt)
            ws.write(r, 4, int(st_.str.startswith("Violation").sum()), cnt)
            r += 1
        ws.conditional_format(4, 3, r - 1, 3, {"type": "cell", "criteria": ">", "value": 0, "format": amber})
        ws.conditional_format(4, 4, r - 1, 4, {"type": "cell", "criteria": ">", "value": 0, "format": red})
        ws.set_column(0, 0, 24)
        ws.set_column(1, 4, 12)

        for name, df in audit.items():
            sheet = name[:31]
            if df.empty:
                e = wb.add_worksheet(sheet)
                w.sheets[sheet] = e
                e.write(0, 0, "Nothing to check.", note_f)
                continue
            df.to_excel(w, sheet_name=sheet, index=False)
            sh = w.sheets[sheet]
            sh.set_row(0, 32)
            for c, col in enumerate(df.columns):
                sh.write(0, c, col, hdr)
                longest = max([len(str(col))] + [len(str(v)) for v in df[col].head(300)])
                width = min(max(longest + 3, 12), 55)
                if pd.api.types.is_float_dtype(df[col]):
                    fmt = n3 if any(k in col for k in ("Level", "Δ", "Grade", "Easting", "Northing")) else n2
                elif pd.api.types.is_numeric_dtype(df[col]):
                    fmt = n2
                else:
                    fmt = txt
                sh.set_column(c, c, width, fmt)
            sh.freeze_panes(1, 0)
            sh.autofilter(0, 0, len(df), len(df.columns) - 1)
            sc = xl_col_to_name(list(df.columns).index("Status"))
            area = (1, 0, len(df), len(df.columns) - 1)
            sh.conditional_format(*area, {"type": "formula", "criteria": f'=LEFT(${sc}2,9)="Violation"', "format": red})
            sh.conditional_format(*area, {"type": "formula", "criteria": f'=LEFT(${sc}2,7)="Warning"', "format": amber})
            sh.conditional_format(*area, {"type": "formula", "criteria": f'=${sc}2="Pass"', "format": green})
            sh.set_landscape()
            sh.fit_to_pages(1, 0)
    return buf


def color_rows(s):
    v = str(s["Status"])
    if v.startswith("Violation"):
        return ["background-color: #f8d7da; color: #721c24"] * len(s)
    if v.startswith("Warning"):
        return ["background-color: #fff3cd; color: #856404"] * len(s)
    return ["background-color: #d4edda; color: #155724"] * len(s)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def step_header(num, title):
    badge = f'<span class="step-badge">{num}</span>' if num else ""
    st.markdown(f'<div class="step-title">{badge}{title}</div>', unsafe_allow_html=True)


def count_status(df):
    if df.empty:
        return 0, 0
    return (int(df["Status"].str.startswith("Violation").sum()),
            int(df["Status"].str.startswith("Warning").sum()))


st.markdown(
    '<div class="hero"><div class="hero-title">🛣️ Road Design Review &amp; Checker</div>'
    '<div class="hero-sub">Independent review of LandXML files exported from Civil 3D against design standards</div></div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    step_header("", "📂 Project file")
    uploaded_file = st.file_uploader("Upload LandXML file (.xml)", type=["xml"], label_visibility="collapsed")

if uploaded_file is None:
    st.info("💡 Upload a LandXML (.xml) file exported from Civil 3D to begin. You will then set the design "
            "criteria and speeds, review the detected intersections, and run the audit.")
    st.stop()

raw = uploaded_file.getvalue()
fhash = hashlib.md5(raw).hexdigest()
if st.session_state.get("file_hash") != fhash:
    st.session_state["file_hash"] = fhash
    st.session_state.pop("audit", None)

try:
    parsed = parse_landxml(raw)
except Exception as e:
    st.error(f"Error processing LandXML file: {e}")
    st.stop()

aligns = parsed["alignments"]
if not aligns:
    st.error("No <Alignment> elements found in this file.")
    st.stop()

by_name = {a["name"]: a for a in aligns}
geo = build_geometry(aligns)
names = [a["name"] for a in aligns]
no_profile = [a["name"] for a in aligns if len(a["pvis"]) < 2]
no_geom = [a["name"] for a in aligns if geo[a["name"]]["multi"] is None]

inter_rows = find_intersections(aligns, geo, snap_tol)
inter_df = pd.DataFrame(inter_rows, columns=["Alignment A", "Alignment B", "Easting", "Northing"])

st.caption(f"📄 **{uploaded_file.name}** · {len(raw) / 1024:,.0f} KB")
m = st.columns(5)
m[0].metric("Alignments", len(aligns))
m[1].metric("With design profile", len(aligns) - len(no_profile))
m[2].metric("Horizontal curves", sum(len(a["hcurves"]) for a in aligns))
m[3].metric("Intersections", len(inter_df))
m[4].metric("Units", parsed["units"].split(" ")[0].capitalize())
if no_profile:
    st.warning("No design profile (ProfAlign) found for: " + ", ".join(no_profile))
if no_geom:
    st.warning("No horizontal geometry (CoordGeom) found for: " + ", ".join(no_geom))

# --- Step 1: criteria ---------------------------------------------------------
with st.container(border=True):
    step_header(1, "Design criteria &amp; speeds")
    if criteria_mode == "Use Code Standards (AASHTO)":
        terrain = st.selectbox("🌍 Project terrain type", ["Level", "Rolling", "Mountainous"], index=0)
    else:
        st.info("Using the manual limits from the sidebar. The design speed below is used for the "
                "minimum vertical curve length check (0.6 × V).")

    speed_mode = st.radio("🚦 Design speed assignment",
                          ["Single Global Speed for All Alignments", "Different Speed for Each Alignment"],
                          horizontal=True)
    if speed_mode.startswith("Single"):
        gspeed = st.selectbox("Global design speed (km/h)", SPEEDS, index=6)
        speed_map = {n: gspeed for n in names}
    else:
        speed_key, ver_key = f"speeds_{fhash}", f"speedver_{fhash}"
        sel_key, bulk_key = f"sel_{fhash}", f"bulk_{fhash}"
        st.session_state.setdefault(speed_key, {n: 80 for n in names})
        st.session_state.setdefault(ver_key, 0)

        def _apply_bulk():
            d = dict(st.session_state[speed_key])
            for n in st.session_state.get(sel_key, []):
                d[n] = st.session_state[bulk_key]
            st.session_state[speed_key] = d
            st.session_state[ver_key] += 1  # new editor key so the table reloads with the new speeds
            st.session_state[sel_key] = []

        def _select_all():
            st.session_state[sel_key] = list(names)

        with st.expander("⚡ Assign one speed to several alignments at once", expanded=True):
            st.multiselect("Alignments", names, key=sel_key)
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.selectbox("Speed (km/h)", SPEEDS, index=6, key=bulk_key)
            c2.button("Select all", on_click=_select_all, use_container_width=True)
            c3.button("Apply to selected", on_click=_apply_bulk, type="primary", use_container_width=True)

        cur = st.session_state[speed_key]
        edited = st.data_editor(
            pd.DataFrame({"Alignment": names, "Design Speed (km/h)": [cur.get(n, 80) for n in names]}),
            column_config={"Design Speed (km/h)": st.column_config.SelectboxColumn(options=SPEEDS, required=True)},
            disabled=["Alignment"], hide_index=True, use_container_width=True,
            key=f"speed_{fhash}_{st.session_state[ver_key]}",
        )
        speed_map = dict(zip(edited["Alignment"], edited["Design Speed (km/h)"]))
        st.session_state[speed_key] = speed_map  # remember individual edits

    def get_limits(n):
        sp = int(speed_map.get(n, 80))
        if criteria_mode == "Use Code Standards (AASHTO)":
            std = AASHTO_DB[sp]
            return {"max_grade": std["max_grade"][terrain], "min_radius": std["min_radius"],
                    "min_k_crest": std["k_crest"], "min_k_sag": std["k_sag"], "speed": sp}
        return {**manual_limits, "speed": sp}

    src_label = f"AASHTO, {terrain} terrain" if criteria_mode == "Use Code Standards (AASHTO)" else "Manual custom limits"
    st.markdown(f'<div class="sub-title">📋 Applied design criteria · {src_label}</div>', unsafe_allow_html=True)
    by_speed = {}
    for n in names:
        by_speed.setdefault(int(speed_map.get(n, 80)), []).append(n)
    crit_rows = []
    for sp in sorted(by_speed):
        lim = get_limits(by_speed[sp][0])
        crit_rows.append({
            "Design Speed (km/h)": sp,
            "Max Grade (%)": lim["max_grade"],
            "Min Grade (%)": min_grade_val if chk_min_grade else None,
            "Min Horizontal Radius (m)": lim["min_radius"],
            "Min K (Crest)": lim["min_k_crest"],
            "Min K (Sag)": lim["min_k_sag"],
            "Min Vertical Curve Length (m)": round(0.6 * sp, 1) if chk_vc_len else None,
            "Alignments": ", ".join(by_speed[sp]),
        })
    st.dataframe(pd.DataFrame(crit_rows).style.format(precision=2, na_rep="-"),
                 use_container_width=True, hide_index=True)
    extra = [f"Level difference at intersections ≤ {level_tol} m"]
    if chk_angle:
        extra.append(f"Intersection angle between {min_angle:.1f}° and {max_angle:.1f}°")
    if not chk_min_grade:
        extra.append("Min grade check is off")
    st.caption(" • ".join(extra))

# --- Step 2: intersections ------------------------------------------------------
with st.container(border=True):
    step_header(2, "At-grade intersections")
    if inter_df.empty:
        st.info("No plan intersections found between alignments.")
    else:
        st.caption("All detected crossings are treated as at-grade junctions: the two design levels must match "
                   "within the tolerance, and the intersection angle must fall inside the min-max range "
                   "set in the sidebar.")
        st.dataframe(inter_df, use_container_width=True, hide_index=True, height=min(300, 38 + 35 * len(inter_df)))

# --- Step 3: run -----------------------------------------------------------------
with st.container(border=True):
    step_header(3, "Run audit")
    run_clicked = st.button("🚀 Run Design Audit", type="primary", use_container_width=True)

if run_clicked:
    hz, tg, vc = [], [], []
    for a in aligns:
        lim = get_limits(a["name"])
        hz += check_horizontal(a["name"], a["hcurves"], lim)
        if len(a["pvis"]) >= 2:
            t, v = check_tangents_and_vcurves(a["name"], a["pvis"], lim)
            tg += t
            vc += v
    lv = check_levels(inter_df, geo, by_name) if len(inter_df) else []
    ag = check_angles(inter_df, geo) if (chk_angle and len(inter_df)) else []
    st.session_state["audit"] = {
        "Horizontal Curves": pd.DataFrame(hz), "Tangent Grades": pd.DataFrame(tg),
        "Vertical Curves": pd.DataFrame(vc), "Alignment Levels": pd.DataFrame(lv),
        "Intersection Angles": pd.DataFrame(ag),
    }

audit = st.session_state.get("audit")
if audit:
    st.markdown("")
    step_header("", "📊 Audit results")

    nonempty = [d["Status"] for d in audit.values() if not d.empty]
    all_status = pd.concat(nonempty, ignore_index=True) if nonempty else pd.Series(dtype=str)
    n_pass = int((all_status == "Pass").sum())
    n_warn = int(all_status.str.startswith("Warning").sum())
    n_viol = int(all_status.str.startswith("Violation").sum())

    if n_viol:
        st.error(f"**{n_viol} violation(s)** found across {len(all_status)} checks. Review the tabs below.")
    elif n_warn:
        st.warning(f"No violations, but **{n_warn} warning(s)** need review.")
    else:
        st.success(f"All {len(all_status)} checks passed.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total checks", len(all_status))
    c2.metric("✅ Pass", n_pass)
    c3.metric("⚠️ Warnings", n_warn)
    c4.metric("❌ Violations", n_viol)
    only_issues = st.toggle("Show violations and warnings only", value=False)

    icons = {"Horizontal Curves": "↔️", "Tangent Grades": "📐", "Vertical Curves": "📈",
             "Alignment Levels": "🔀", "Intersection Angles": "🧭"}
    labels = []
    for title, df in audit.items():
        nv, nw = count_status(df)
        labels.append(f"{icons[title]} {title} ({len(df)})" + (f" 🔴{nv}" if nv else "") + (f" 🟡{nw}" if nw else ""))
    tabs = st.tabs(labels + ["🗺️ Plan view", "📥 Export"])

    for tab, (title, df) in zip(tabs, audit.items()):
        with tab:
            if df.empty:
                st.caption("Nothing to check.")
                continue
            view = df[df["Status"] != "Pass"] if only_issues else df
            if view.empty:
                st.success("No violations or warnings in this table.")
                continue
            st.dataframe(view.style.apply(color_rows, axis=1).format(precision=3, na_rep=""),
                         use_container_width=True, hide_index=True)

    with tabs[len(audit)]:
        fig = go.Figure()
        for a in aligns:
            xs = [p[0] for e in a["elems"] for p in e["pts"]]
            ys = [p[1] for e in a["elems"] for p in e["pts"]]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=a["name"]))
        marks = {}
        for tname, label in (("Alignment Levels", "Level"), ("Intersection Angles", "Angle")):
            for _, r in audit.get(tname, pd.DataFrame(columns=["Status"])).iterrows():
                mk = marks.setdefault((r["Alignment A"], r["Alignment B"], r["Easting"], r["Northing"]),
                                      {"rank": 0, "lines": []})
                rank = 2 if r["Status"].startswith("Violation") else 1 if r["Status"].startswith("Warning") else 0
                mk["rank"] = max(mk["rank"], rank)
                mk["lines"].append(f"{label}: {r['Status']}")
        if marks:
            palette = {0: "#28a745", 1: "#ffc107", 2: "#dc3545"}
            fig.add_trace(go.Scatter(
                x=[k[2] for k in marks], y=[k[3] for k in marks], mode="markers", name="Intersections",
                marker=dict(size=12, color=[palette[v["rank"]] for v in marks.values()],
                            line=dict(width=1, color="black")),
                text=[f"{k[0]} × {k[1]}<br>" + "<br>".join(v["lines"]) for k, v in marks.items()],
                hoverinfo="text"))
        fig.update_layout(height=600, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis=dict(scaleanchor="x", scaleratio=1, title="Northing (m)"),
                          xaxis=dict(title="Easting (m)"),
                          legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Intersection markers: green = pass, amber = warning, red = violation (worst of level and angle checks).")

    with tabs[len(audit) + 1]:
        report = ("--- LandXML Design Audit Report ---\n(Preliminary check - verify against the governing code.)\n\n")
        for title, df in audit.items():
            report += f"{title}:\n" + (df.to_string(index=False) if not df.empty else "none") + "\n\n"
        col1, col2 = st.columns(2)
        col1.download_button("📄 Download text report", report, "LandXML_Audit_Report.txt", "text/plain",
                             use_container_width=True)
        col2.download_button("📊 Download Excel report", build_excel(audit).getvalue(), "LandXML_Audit_Report.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True, type="primary")
        st.caption("The Excel report has a summary sheet plus one formatted sheet per check table.")

st.markdown('<div class="disclaimer">⚠️ Preliminary check based on simplified criteria. '
            'Results must be verified against the governing design code.</div>', unsafe_allow_html=True)
