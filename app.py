import streamlit as st
import pandas as pd
import io
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from streamlit_option_menu import option_menu

# ----------------- إعدادات الصفحة -----------------
st.set_page_config(page_title="CO-BODR Engineering Portal", layout="wide", page_icon="🛣️")

# ----------------- تنسيقات CSS -----------------
st.markdown("""
    <style>
    .welcome-banner { text-align: center; animation: fadeInScale 1.5s ease-in-out; margin-bottom: 20px; }
    .welcome-title { font-size: 3.5rem; font-weight: 900; background: -webkit-linear-gradient(45deg, #007bff, #00d2ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; letter-spacing: 2px; }
    .welcome-subtitle { font-size: 1.2rem; color: #6c757d; letter-spacing: 1px; }
    @keyframes fadeInScale { 0% { opacity: 0; transform: translateY(-30px) scale(0.9); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
    .stCard { background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 5px solid #007bff; transition: transform 0.3s; }
    .stCard:hover { transform: translateY(-5px); box-shadow: 0 6px 12px 0 rgba(0,0,0,0.1); }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px 0 rgba(0,0,0,0.05); text-align: center; border: 1px solid #e9ecef; }
    .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
    .metric-label { font-size: 14px; color: #6c757d; }
    
    /* تنسيق خاص للوجو في القائمة الجانبية */
    .sidebar-logo { font-size: 80px; text-align: center; margin-bottom: -20px; }
    </style>
""", unsafe_allow_html=True)

if 'report_data' not in st.session_state: st.session_state.report_data = []

turning_data = {
    'Design Vehicle Type': ['Passenger Car', 'Single-Unit Truck', 'Intercity Bus', 'WB-12 Semitrailer', 'WB-20 Semitrailer'],
    'Symbol': ['P', 'SU-12', 'BUS-12', 'WB-12', 'WB-20'],
    'Min Design Turning Radius (m)': [7.26, 15.60, 12.70, 12.16, 13.66],
    'Centerline Radius (CTR) (m)': [6.40, 14.46, 11.53, 10.97, 12.50],
    'Min Inside Radius (m)': [4.39, 11.09, 7.41, 5.88, 0.59]
}
df_turning = pd.DataFrame(turning_data)
vehicle_images = {'P': 'Passenger Car Turning Radius.png', 'SU-12': 'SU-12 Turning Radius.png', 'BUS-12': 'BUS-12 Turning Radius.png', 'WB-12': 'WB-12 Turning Radius.png', 'WB-20': 'WB-20 Turning Radius.png'}

k_values_data = {
    "Crest": {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124},
    "Sag": {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}
}

horizontal_data = {
    'e (%)': [-6.0, -5.0, -4.0, -3.0, -2.0, -1.5, 0.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
    '20': [11, 10, 10, 10, 10, 9, 9, 9, 9, 8, 8, 8, 8, 7, 7, 7, 7, 7, 7],
    '30': [32, 31, 30, 28, 27, 27, 25, 24, 24, 23, 22, 21, 21, 20, 20, 19, 19, 18, 18],
    '40': [74, 70, 66, 63, 60, 59, 55, 51, 50, 48, 47, 45, 43, 42, 41, 39, 38, 37, 36],
    '50': [151, 141, 131, 123, 116, 113, 104, 96, 94, 89, 86, 82, 79, 76, 73, 70, 68, 66, 64],
    '60': [258, 236, 218, 202, 189, 183, 167, 153, 149, 142, 135, 129, 123, 118, 113, 109, 105, 101, 98],
    '70': [429, 386, 351, 322, 297, 286, 257, 234, 227, 214, 203, 193, 184, 175, 168, 161, 154, 148, 143]
}
df_horizontal = pd.DataFrame(horizontal_data)

def generate_word_report():
    doc = Document()
    doc.add_heading('CO-BODR - Calculation Note', 0)
    if not st.session_state.report_data:
        doc.add_paragraph("No data added to the report yet.")
        return doc
    for item in st.session_state.report_data:
        if item['tool'] == 'K-Value':
            doc.add_heading('1. Vertical Alignment (K-Value)', level=1)
            doc.add_paragraph(f"Curve Type: {item['curve_type']} | Design Speed: {item['speed']} km/h")
            doc.add_paragraph(f"Required Minimum K-Value: {item['k_value']}").bold = True
            doc.add_paragraph("_" * 50)
        elif item['tool'] == 'Turning Radius':
            doc.add_heading('2. Turning Radius Check', level=1)
            doc.add_paragraph(f"Design Vehicle: {item['vehicle_name']} ({item['symbol']})")
            doc.add_paragraph(f"Minimum Design Turning Radius: {item['min_r']} m").bold = True
            img_path = vehicle_images.get(item['symbol'])
            if img_path and os.path.exists(img_path): doc.add_picture(img_path, width=Inches(5.5))
            doc.add_paragraph("_" * 50)
        elif item['tool'] == 'Horizontal Radius':
            doc.add_heading('3. Horizontal Alignment (Low-Speed Urban)', level=1)
            doc.add_paragraph(f"Design Speed: {item['speed']} km/h | Superelevation (e): {item['e_val']}%")
            p = doc.add_paragraph()
            p.add_run(f"Minimum Curve Radius (R): {item['radius']} m").bold = True
            doc.add_heading('AASHTO Table 3-13a (Reference):', level=2)
            table = doc.add_table(rows=1, cols=len(df_horizontal.columns))
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for i, column in enumerate(df_horizontal.columns): hdr_cells[i].text = column if column == 'e (%)' else f"Vd={column}km/h"
            for index, row in df_horizontal.iterrows():
                row_cells = table.add_row().cells
                for i, column in enumerate(df_horizontal.columns): row_cells[i].text = str(row[column])
                if row['e (%)'] == float(item['e_val']):
                    for cell in row_cells:
                        shading_elm = parse_xml(r'<w:shd {} w:fill="FFCCCC"/>'.format(nsdecls('w')))
                        cell._tc.get_or_add_tcPr().append(shading_elm)
            doc.add_paragraph("_" * 50)
    return doc

# ----------------- القائمة الجانبية -----------------
with st.sidebar:
    # استخدام نص CSS كبير كلوجو بدلاً من الروابط الخارجية لضمان ظهوره دائماً
    st.markdown('<div class="sidebar-logo">🛣️</div>', unsafe_allow_html=True)
    st.title("CO-BODR")
    
    selected_tool = option_menu(
        menu_title="Main Menu",
        options=["Home", "Vertical Curves (K)", "Horizontal Curves (R)", "Turning Radius"],
        icons=["house", "bezier2", "sign-turn-right", "truck"],
        menu_icon="cast", default_index=0,
        styles={"nav-link-selected": {"background-color": "#007bff"}}
    )
    st.markdown("---")
    st.markdown("### 📄 Report Center")
    if st.button("Generate Word Report", use_container_width=True):
        if st.session_state.report_data:
            doc = generate_word_report()
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button("⬇️ Download Calculation Note", data=bio.getvalue(), file_name="Calculation_Note.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        else:
            st.warning("No data added yet.")

# ----------------- الصفحات -----------------
if selected_tool == "Home":
    st.markdown("""
        <div class="welcome-banner">
            <div class="welcome-title">WELCOME TO CO-BODR</div>
            <div class="welcome-subtitle">Advanced Highway Design & Calculation Portal</div>
        </div>
    """, unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=2000&q=80", use_container_width=True)
    st.write("") 
    st.markdown('<div class="stCard"><h4>Select a tool from the sidebar to begin your AASHTO calculations.</h4></div>', unsafe_allow_html=True)

elif selected_tool == "Vertical Curves (K)":
    st.title("🛣️ Vertical Curves (K-Value)")
    col1, col2 = st.columns(2)
    with col1: curve_type = st.selectbox("Curve Type", ["Crest", "Sag"])
    with col2: speed = st.selectbox("Design Speed [km/h]", list(k_values_data[curve_type].keys()), index=10)
    req_k = k_values_data[curve_type][speed]
    st.markdown(f'<div class="metric-card"><div class="metric-label">Required Minimum K-Value</div><div class="metric-value">{req_k}</div></div>', unsafe_allow_html=True)
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'K-Value', 'curve_type': curve_type, 'speed': speed, 'k_value': req_k})
        st.success("Added to Calculation Note!")

elif selected_tool == "Horizontal Curves (R)":
    st.title("🔄 Horizontal Curves (Low-Speed Urban)")
    st.markdown('<div class="stCard"><p>Based on AASHTO Table 3-13a: Minimum Radii for Low-Speed Urban Streets</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: v_design = st.selectbox("Design Speed (Vd) [km/h]", ['20', '30', '40', '50', '60', '70'], index=3)
    with col2: e_val = st.selectbox("Superelevation (e) [%]", df_horizontal['e (%)'].tolist(), index=6)
    radius = df_horizontal[df_horizontal['e (%)'] == e_val][v_design].values[0]
    st.markdown(f'<div class="metric-card"><div class="metric-label">Minimum Curve Radius (R)</div><div class="metric-value">{radius} m</div></div>', unsafe_allow_html=True)
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'Horizontal Radius', 'speed': v_design, 'e_val': str(e_val), 'radius': radius})
        st.success(f"Radius ({radius}m) added to Calculation Note!")

elif selected_tool == "Turning Radius":
    st.title("📐 Minimum Turning Radius")
    display_names = df_turning['Design Vehicle Type'] + " (" + df_turning['Symbol'] + ")"
    selected_display = st.selectbox("Select Design Vehicle:", display_names)
    selected_symbol = selected_display.split("(")[-1].replace(")", "")
    v_data = df_turning[df_turning['Symbol'] == selected_symbol].iloc[0]
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">Min Radius</div><div class="metric-value">{v_data["Min Design Turning Radius (m)"]} m</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">CTR</div><div class="metric-value">{v_data["Centerline Radius (CTR) (m)"]} m</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">Inside Radius</div><div class="metric-value">{v_data["Min Inside Radius (m)"]} m</div></div>', unsafe_allow_html=True)
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'Turning Radius', 'vehicle_name': v_data['Design Vehicle Type'], 'symbol': selected_symbol, 'min_r': v_data['Min Design Turning Radius (m)'], 'ctr': v_data['Centerline Radius (CTR) (m)'], 'inside_r': v_data['Min Inside Radius (m)']})
        st.success("Added to Calculation Note!")
