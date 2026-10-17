import json
from pathlib import Path

import streamlit as st

# Edit these two lines when you publish an update
APP_VERSION = "1.0"
LAST_UPDATED = "17 Oct 2026"

st.set_page_config(
    page_title="Road Engineering Platform",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        [data-testid="collapsedControl"], [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }
        .block-container { padding-top: 1.8rem; max-width: 1150px; }

        /* Hero */
        .hero {
            background: radial-gradient(circle at 85% 20%, rgba(91,155,232,.35) 0%, rgba(91,155,232,0) 45%),
                        linear-gradient(135deg, #14264a 0%, #1F3864 45%, #2E5C9A 100%);
            padding: 3rem 2rem 2.6rem; border-radius: 18px; text-align: center;
            box-shadow: 0 8px 26px rgba(0,0,0,.25); margin-bottom: 1.4rem;
        }
        .hero-title { color: #fff; font-size: 2.8rem; font-weight: 800; letter-spacing: -.8px; line-height: 1.1; }
        .hero-sub { color: rgba(255,255,255,.85); font-size: 1.12rem; margin: .7rem auto 0; max-width: 640px; }
        .hero-tags { margin-top: 1.3rem; }
        .hero-tag { display: inline-block; padding: .25rem .85rem; margin: .15rem .25rem; border-radius: 999px;
                    font-size: .8rem; font-weight: 600; color: #fff; background: rgba(255,255,255,.14);
                    border: 1px solid rgba(255,255,255,.28); }

        /* Info strip */
        .info-card { border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.07);
                     border-radius: 12px; padding: .9rem 1.1rem; height: 100%; }
        .info-label { font-size: .72rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; opacity: .6; }
        .info-value { font-size: 1.02rem; font-weight: 600; margin-top: .2rem; }

        .section-label { font-size: .85rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
                         opacity: .6; margin: 1.8rem 0 .8rem .2rem; }

        /* Tool cards */
        .card-icon { font-size: 2.4rem; line-height: 1; margin-bottom: .45rem; }
        .card-title { font-size: 1.5rem; font-weight: 700; margin-bottom: .3rem; }
        .card-desc { opacity: .8; font-size: .98rem; margin-bottom: .8rem; min-height: 3.3rem; }
        .chips { min-height: 2.4rem; }
        .feat { list-style: none; padding: 0; margin: 0 0 1rem; }
        .feat li { padding: .22rem 0 .22rem 1.5rem; position: relative; font-size: .93rem; }
        .feat li::before { content: "✓"; position: absolute; left: 0; color: #28a745; font-weight: 700; }
        .chip { display: inline-block; padding: .16rem .62rem; margin: 0 .3rem .35rem 0; border-radius: 999px;
                font-size: .75rem; font-weight: 600; background: rgba(46,92,154,.18); color: #5B9BE8;
                border: 1px solid rgba(46,92,154,.45); }

        div.stButton > button { height: 3rem; border-radius: 10px; font-weight: 600; transition: all .2s ease-in-out; }
        div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 14px rgba(0,123,255,.35); }

        /* Workflow */
        .flow { display: flex; gap: .9rem; flex-wrap: wrap; }
        .flow-step { flex: 1 1 180px; border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
                     padding: 1rem 1.1rem; background: rgba(128,128,128,.05); }
        .flow-num { display: inline-flex; align-items: center; justify-content: center; width: 1.9rem; height: 1.9rem;
                    border-radius: 50%; background: #2E5C9A; color: #fff; font-weight: 700; font-size: .9rem; margin-bottom: .5rem; }
        .flow-title { font-weight: 600; margin-bottom: .15rem; }
        .flow-text { font-size: .86rem; opacity: .75; }

        button[kind="primary"], button[data-testid="stBaseButton-primary"] {
            background-color: #2E5C9A !important; border-color: #2E5C9A !important; color: #fff !important; }
        button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
            background-color: #3A70B8 !important; border-color: #3A70B8 !important; }
        .statusbar { display: flex; justify-content: space-between; flex-wrap: wrap; gap: .5rem 1.5rem;
                     border-top: 1px solid rgba(128,128,128,.3); margin-top: 2.5rem; padding-top: .9rem;
                     font-size: .8rem; opacity: .7; }
        .footer { text-align: center; font-size: .8rem; opacity: .6; margin: .8rem 0 .5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- Design code data (shared with BODR)
ROOT = Path(__file__).resolve().parent
SECTIONS = ("k_values", "horizontal", "turning")


@st.cache_data(show_spinner=False)
def load_codes():
    out = {}
    for f in (ROOT / "bodr_data").glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            out[d.get("code", f.stem.upper())] = d
        except Exception:
            pass
    return dict(sorted(out.items(), key=lambda kv: (kv[1].get("order", 99), kv[0])))


CODES = load_codes()

# ---------------------------------------------------------------- Hero
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🛣️ Road Engineering Platform</div>
        <div class="hero-sub">Review road designs and prepare highway design calculations in one place.</div>
        <div class="hero-tags">
            <span class="hero-tag">AASHTO</span><span class="hero-tag">Abu Dhabi (ADM)</span>
            <span class="hero-tag">MOMRA</span><span class="hero-tag">Civil 3D LandXML</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- Info strip
i1, i2, i3 = st.columns(3, gap="medium")
i1.markdown('<div class="info-card"><div class="info-label">Input</div>'
            '<div class="info-value">LandXML from Civil 3D, or manual design inputs</div></div>', unsafe_allow_html=True)
i2.markdown('<div class="info-card"><div class="info-label">Standards</div>'
            '<div class="info-value">AASHTO, Abu Dhabi ADM, MOMRA</div></div>', unsafe_allow_html=True)
i3.markdown('<div class="info-card"><div class="info-label">Output</div>'
            '<div class="info-value">Excel audit report and Word calculation note</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- Tools
st.markdown('<div class="section-label">Tools</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container(border=True):
        st.markdown(
            """
            <div class="card-icon">🔍</div>
            <div class="card-title">Design Checks</div>
            <div class="card-desc">Independent review of a LandXML file against design criteria.</div>
            <ul class="feat">
                <li>Grades, vertical curves (K) and horizontal radii</li>
                <li>Level and angle checks at alignment intersections</li>
                <li>Speed per alignment, with bulk assignment</li>
                <li>Plan view with flagged intersections</li>
                <li>Formatted Excel and text reports</li>
            </ul>
            <div class="chips"><span class="chip">LandXML</span><span class="chip">AASHTO</span><span class="chip">Manual limits</span></div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Design Checks  →", type="primary", use_container_width=True, key="open_checks"):
            st.switch_page("pages/1_Design_Checks.py")

with col2:
    with st.container(border=True):
        st.markdown(
            """
            <div class="card-icon">📄</div>
            <div class="card-title">BODR</div>
            <div class="card-desc">Highway design wizard: choose the design code, enter inputs and get the
            design values.</div>
            <ul class="feat">
                <li>K-values by design speed</li>
                <li>Horizontal radii by speed and superelevation</li>
                <li>Vehicle turning radius</li>
                <li>Design code selector: AASHTO, ADM, MOMRA</li>
                <li>Word calculation note export</li>
            </ul>
            <div class="chips"><span class="chip">AASHTO</span><span class="chip">Abu Dhabi (ADM)</span><span class="chip">MOMRA</span></div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open BODR  →", type="primary", use_container_width=True, key="open_bodr"):
            st.switch_page("pages/2_BODR.py")

# ---------------------------------------------------------------- Quick lookup
st.markdown('<div class="section-label">Quick lookup</div>', unsafe_allow_html=True)
with st.container(border=True):
    avail = [c for c, d in CODES.items() if "k_values" in d or "horizontal" in d]
    if not avail:
        st.info("No design code tables found. Add the `bodr_data` folder to the repository to enable the quick lookup.")
    else:
        q1, q2, q3 = st.columns(3)
        qcode = q1.selectbox("Design code", avail, key="q_code")
        d = CODES[qcode]
        kv, hz = d.get("k_values"), d.get("horizontal")
        speeds = sorted({*(kv["speeds"] if kv else []), *([int(s) for s in hz["radii"]] if hz else [])})
        qspeed = q2.selectbox("Design speed (km/h)", speeds, index=speeds.index(100) if 100 in speeds else 0,
                              key=f"q_speed_{qcode}")
        e_list = hz["e"] if hz else []
        qe = q3.selectbox("Superelevation e (%)", e_list or ["-"],
                          index=e_list.index(0.0) if 0.0 in e_list else 0,
                          key=f"q_e_{qcode}", disabled=not e_list)

        crest = sag = rad = None
        if kv and qspeed in kv["speeds"]:
            i = kv["speeds"].index(qspeed)
            crest, sag = kv["crest"][i], kv["sag"][i]
        if hz and str(qspeed) in hz["radii"] and qe in hz["e"]:
            rad = hz["radii"][str(qspeed)][hz["e"].index(qe)]

        r1, r2, r3 = st.columns(3)
        r1.metric("Min K · crest", "-" if crest is None else crest)
        r2.metric("Min K · sag", "-" if sag is None else sag)
        r3.metric("Min radius (m)", "-" if rad is None else rad)
        notes = []
        if kv:
            notes.append(f"K values: {kv.get('source', '')}")
        if hz:
            notes.append(f"Radius: {hz.get('source', '')}, {hz.get('title', '')}")
        st.caption(" · ".join(notes) + ". A dash means the selected code table does not cover this speed.")

# ---------------------------------------------------------------- Workflow
st.markdown('<div class="section-label">How Design Checks works</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="flow">
        <div class="flow-step"><div class="flow-num">1</div><div class="flow-title">Upload</div>
            <div class="flow-text">Export LandXML from Civil 3D and upload the .xml file.</div></div>
        <div class="flow-step"><div class="flow-num">2</div><div class="flow-title">Set criteria</div>
            <div class="flow-text">Choose AASHTO or manual limits, then assign design speeds.</div></div>
        <div class="flow-step"><div class="flow-num">3</div><div class="flow-title">Run audit</div>
            <div class="flow-text">Grades, curves, intersection levels and angles are checked.</div></div>
        <div class="flow-step"><div class="flow-num">4</div><div class="flow-title">Review &amp; export</div>
            <div class="flow-text">Inspect violations by table or plan view and download the report.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

loaded = " · ".join(
    f"{c} ({sum(1 for k in SECTIONS if k in d)}/{len(SECTIONS)} tables)" for c, d in CODES.items()
) or "none loaded"
st.markdown(
    f'''
    <div class="statusbar">
        <span>Version {APP_VERSION} · Updated {LAST_UPDATED}</span>
        <span>Design codes: {loaded}</span>
    </div>
    <div class="footer">Results are preliminary and must be verified against the governing design code.</div>
    ''',
    unsafe_allow_html=True,
)
