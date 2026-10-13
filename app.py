import streamlit as st
import pandas as pd
import io
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ----------------- إعدادات الصفحة -----------------
st.set_page_config(page_title="CO-BODR Engineering", layout="wide", page_icon="logo.png")

# ----------------- تنسيقات CSS -----------------
st.markdown("""
    <style>
    .welcome-banner { text-align: center; animation: fadeInScale 1.5s ease-in-out; margin-bottom: 20px; }
    .welcome-title { font-size: 3.5rem; font-weight: 900; background: -webkit-linear-gradient(45deg, #007bff, #00d2ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; letter-spacing: 2px; }
    .welcome-subtitle { font-size: 1.2rem; opacity: 0.8; letter-spacing: 1px; }
    @keyframes fadeInScale { 0% { opacity: 0; transform: translateY(-30px) scale(0.9); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
    .stCard { background-color: var(--secondary-background-color); color: var(--text-color); padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 5px solid #007bff; transition: transform 0.3s; }
    .stCard h4, .stCard p { color: var(--text-color) !important; }
    .stCard:hover { transform: translateY(-5px); box-shadow: 0 6px 12px 0 rgba(0,0,0,0.2); }
    .metric-card { background-color: var(--secondary-background-color); color: var(--text-color); padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px 0 rgba(0,0,0,0.1); text-align: center; border: 1px solid var(--faded-text-color); }
    .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
    .metric-label { font-size: 14px; opacity: 0.8; }
    </style>
""", unsafe_allow_html=True)

# ----------------- تهيئة الذاكرة للتقرير -----------------
if 'report_data' not in st.session_state:
    st.session_state.report_data = []

# ----------------- قواعد البيانات المتعددة الأكواد -----------------
# 1. AASHTO Data
aashto_k_crest = {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124}
aashto_k_sag = {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}
aashto_turning = pd.DataFrame({
    'Vehicle': ['Passenger Car', 'Single-Unit Truck', 'Intercity Bus', 'WB-12', 'WB-20'],
    'Symbol': ['P', 'SU-12', 'BUS-12', 'WB-12', 'WB-20'],
    'Min_R': [7.26, 15.60, 12.70, 12.16, 13.66],
    'Inside_R': [4.39, 11.09, 7.41, 5.88, 0.59]
})

# 2. Abu Dhabi (ADM) Data
auh_k_crest = {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124, 140: 161}
auh_k_sag = {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73, 140: 84}
auh_turning = pd.DataFrame({
    'Vehicle': ['Passenger Car', 'Single Unit Truck SU-9', 'Single Unit Truck SU-12', 'City Transit Bus', 'Intermediate Semitrailer WB-12', 'Intermediate Semitrailer WB-15', 'Interstate Semitrailer WB-20', 'Double Trailer WB-33D'],
    'Symbol': ['P', 'SU-9', 'SU-12', 'CITY-BUS', 'WB-12', 'WB-15', 'WB-20', 'WB-33D'],
    'Min_R': [7.26, 12.73, 15.60, 12.50, 12.16, 13.66, 13.66, 18.25],
    'Inside_R': [4.39, 8.64, 11.09, 5.30, 5.88, 5.20, 0.59, 4.19]
})

# 3. MOMRA Data
momra_k_crest = {30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124}
momra_k_sag = {30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}
momra_turning = pd.DataFrame({
    'Vehicle': ['سيارة ركوب صغيرة', 'شاحنة وحدة مفردة', 'حافلة', 'شاحنة بمقطورة متوسطة', 'شاحنة بمقطورة كبيرة'],
    'Symbol': ['P', 'SU', 'BUS-12', 'WB-12', 'WB-20'],
    'Min_R': [7.26, 12.73, 12.70, 12.16, 13.66],
    'Inside_R': [4.39, 8.64, 7.41, 5.88, 0.59]
})


# ----------------- واجهة الاستخدام (UI FLOW) -----------------
st.markdown("""
    <div class="welcome-banner">
        <div class="welcome-title">CO-BODR</div>
        <div class="welcome-subtitle">Advanced Highway Design & Calculation</div>
    </div>
""", unsafe_allow_html=True)

# STEP 1: اختيار الكود
st.markdown("### Step 1: Select Design Code")
selected_code = st.radio("Choose the standard you are designing for:", ["AASHTO", "Abu Dhabi (ADM)", "MOMRA"], horizontal=True)

# STEP 2: اختيار الأداة
st.markdown("---")
st.markdown("### Step 2: Select Calculation Tool")
tools = ["Vertical Curves (K-Value)", "Turning Radius", "Typical Cross-Section"]
selected_tool = st.selectbox("What do you want to calculate?", tools)

# STEP 3: المدخلات والنتائج
st.markdown("---")
st.markdown(f"### Step 3: {selected_tool} Inputs")

if selected_tool == "Vertical Curves (K-Value)":
    if selected_code == "AASHTO":
        c_dict, s_dict = aashto_k_crest, aashto_k_sag
    elif selected_code == "Abu Dhabi (ADM)":
        c_dict, s_dict = auh_k_crest, auh_k_sag
    else:
        c_dict, s_dict = momra_k_crest, momra_k_sag
        
    col1, col2 = st.columns(2)
    with col1: curve_type = st.selectbox("Curve Type", ["Crest", "Sag"])
    
    speed_list = list(c_dict.keys()) if curve_type == "Crest" else list(s_dict.keys())
    with col2: speed = st.selectbox("Design Speed [km/h]", speed_list)
    
    req_k = c_dict[speed] if curve_type == "Crest" else s_dict[speed]
    
    st.markdown(f'<div class="metric-card"><div class="metric-label">Required Minimum K-Value ({selected_code})</div><div class="metric-value">{req_k}</div></div>', unsafe_allow_html=True)
    
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'K-Value', 'code': selected_code, 'curve_type': curve_type, 'speed': speed, 'k_value': req_k})
        st.success("Added to Calculation Note!")

elif selected_tool == "Turning Radius":
    if selected_code == "AASHTO":
        df_turn = aashto_turning
    elif selected_code == "Abu Dhabi (ADM)":
        df_turn = auh_turning
    else:
        df_turn = momra_turning
        
    display_names = df_turn['Vehicle'] + " (" + df_turn['Symbol'] + ")"
    selected_display = st.selectbox("Select Design Vehicle:", display_names)
    selected_symbol = selected_display.split("(")[-1].replace(")", "")
    v_data = df_turn[df_turn['Symbol'] == selected_symbol].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">Minimum Design Radius</div><div class="metric-value">{v_data["Min_R"]} m</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">Minimum Inside Radius</div><div class="metric-value">{v_data["Inside_R"]} m</div></div>', unsafe_allow_html=True)
    
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'Turning Radius', 'code': selected_code, 'vehicle_name': v_data['Vehicle'], 'symbol': selected_symbol, 'min_r': v_data['Min_R'], 'inside_r': v_data['Inside_R']})
        st.success("Added to Calculation Note!")

elif selected_tool == "Typical Cross-Section":
    st.info("Design your cross section layer by layer.")
    col1, col2 = st.columns(2)
    with col1: lanes = st.number_input("Number of Lanes (per direction)", min_value=1, max_value=6, value=2)
    with col1: lane_width = st.number_input("Lane Width (m)", min_value=2.5, max_value=4.0, value=3.3, step=0.1)
    with col2: median = st.number_input("Median Width (m)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    with col2: sidewalk = st.number_input("Sidewalk Width (m, per side)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    
    total_width = (lanes * lane_width * 2) + median + (sidewalk * 2)
    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Right-of-Way (ROW) Width</div><div class="metric-value">{round(total_width, 2)} m</div></div>', unsafe_allow_html=True)
    
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({'tool': 'Cross Section', 'code': selected_code, 'lanes': lanes, 'lane_width': lane_width, 'median': median, 'sidewalk': sidewalk, 'total': total_width})
        st.success("Added to Calculation Note!")

# STEP 4: استخراج التقرير
st.markdown("---")
st.markdown("### Step 4: Generate Report")
if st.button("Generate Word Report", use_container_width=True):
    if st.session_state.report_data:
        doc = Document()
        doc.add_heading('CO-BODR - Calculation Note', 0)
        for idx, item in enumerate(st.session_state.report_data):
            doc.add_heading(f"Calculation {idx+1}: {item['tool']} [{item['code']}]", level=1)
            if item['tool'] == 'K-Value':
                doc.add_paragraph(f"Curve Type: {item['curve_type']} | Design Speed: {item['speed']} km/h")
                doc.add_paragraph(f"Required K-Value: {item['k_value']}").bold = True
            elif item['tool'] == 'Turning Radius':
                doc.add_paragraph(f"Vehicle: {item['vehicle_name']} ({item['symbol']})")
                doc.add_paragraph(f"Min Radius: {item['min_r']} m | Inside Radius: {item['inside_r']} m").bold = True
            elif item['tool'] == 'Cross Section':
                doc.add_paragraph(f"Lanes per direction: {item['lanes']} | Lane Width: {item['lane_width']} m")
                doc.add_paragraph(f"Median Width: {item['median']} m | Sidewalks: {item['sidewalk']} m (each side)")
                doc.add_paragraph(f"Total ROW Width: {round(item['total'], 2)} m").bold = True
            doc.add_paragraph("_" * 50)
        
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button("⬇️ Download Calculation Note", data=bio.getvalue(), file_name="Calculation_Note.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
    else:
        st.warning("No data added yet.")
