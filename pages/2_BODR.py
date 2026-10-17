import datetime
import io
import json
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor

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

    used = list(dict.fromkeys(i.get("code", "AASHTO") for i in items))
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
    f'horizontal curves and turning radii, with a downloadable calculation note</div></div>',
    unsafe_allow_html=True,
)


def metric(label, value):
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>'


def no_table(section):
    st.info(f"No **{section}** table has been loaded for **{code}** yet. "
            f"Add it to `bodr_data/{code.lower()}.json` (see `bodr_data/README.md`).")
    if cd.get("notes"):
        st.caption(cd["notes"])


tab_k, tab_h, tab_t, tab_r = st.tabs([
    "📈 Vertical Curves (K)", "🔄 Horizontal Curves (R)", "📐 Turning Radius",
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
