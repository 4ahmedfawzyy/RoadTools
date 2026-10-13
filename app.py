import streamlit as st
import pandas as pd
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ----------------- إعدادات الصفحة -----------------
st.set_page_config(page_title="CO-BODR Engineering", layout="wide", page_icon="logo.png")

# ----------------- تنسيقات CSS -----------------
st.markdown("""
    <style>
    .wizard-step { background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .step-title { color: #007bff; font-weight: bold; margin-bottom: 15px; }
    .result-box { background-color: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; margin-top: 10px; color: #333;}
    .result-value { font-size: 22px; font-weight: bold; color: #007bff; }
    </style>
""", unsafe_allow_html=True)

# ----------------- الداتا الخاصة بالأكواد -----------------
data = {
    "AASHTO": {
        "k_crest": {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124},
        "k_sag": {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73},
        "vehicles": pd.DataFrame({'Name': ['Passenger Car', 'Single-Unit Truck', 'Intercity Bus', 'WB-12', 'WB-20'], 'Symbol': ['P', 'SU-12', 'BUS-12', 'WB-12', 'WB-20'], 'Min_R': [7.26, 15.60, 12.70, 12.16, 13.66], 'Inside_R': [4.39, 11.09, 7.41, 5.88, 0.59]})
    },
    "Abu Dhabi (ADM)": {
        "k_crest": {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124, 140: 161},
        "k_sag": {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73, 140: 84},
        "vehicles": pd.DataFrame({'Name': ['Passenger Car', 'Single Unit SU-9', 'Single Unit SU-12', 'City Bus', 'WB-12', 'WB-15', 'WB-20'], 'Symbol': ['P', 'SU-9', 'SU-12', 'CITY-BUS', 'WB-12', 'WB-15', 'WB-20'], 'Min_R': [7.26, 12.73, 15.60, 12.50, 12.16, 13.66, 13.66], 'Inside_R': [4.39, 8.64, 11.09, 5.30, 5.88, 5.20, 0.59]})
    },
    "MOMRA": {
        "k_crest": {30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124},
        "k_sag": {30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73},
        "vehicles": pd.DataFrame({'Name': ['سيارة ركوب صغيرة', 'شاحنة وحدة مفردة', 'حافلة', 'شاحنة بمقطورة متوسطة', 'شاحنة بمقطورة كبيرة'], 'Symbol': ['P', 'SU', 'BUS-12', 'WB-12', 'WB-20'], 'Min_R': [7.26, 12.73, 12.70, 12.16, 13.66], 'Inside_R': [4.39, 8.64, 7.41, 5.88, 0.59]})
    }
}

st.title("🛣️ CO-BODR Highway Design Wizard")
st.markdown("---")

# ================= STEP 1: SELECT CODE =================
st.markdown('<div class="wizard-step">', unsafe_allow_html=True)
st.markdown('<h3 class="step-title">1. Select Design Code</h3>', unsafe_allow_html=True)
selected_code = st.radio("Reference Standard:", ["AASHTO", "Abu Dhabi (ADM)", "MOMRA"], horizontal=True, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

active_data = data[selected_code]

# ================= STEP 2: SELECT SPEED =================
st.markdown('<div class="wizard-step">', unsafe_allow_html=True)
st.markdown('<h3 class="step-title">2. Select Design Speed</h3>', unsafe_allow_html=True)
speed_options = list(active_data["k_crest"].keys())
selected_speed = st.selectbox("Speed (km/h):", speed_options)

req_k_crest = active_data["k_crest"].get(selected_speed, "N/A")
req_k_sag = active_data["k_sag"].get(selected_speed, "N/A")

c1, c2 = st.columns(2)
c1.markdown(f'<div class="result-box">Crest K-Value<br><span class="result-value">{req_k_crest}</span></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="result-box">Sag K-Value<br><span class="result-value">{req_k_sag}</span></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ================= STEP 3: SELECT VEHICLE =================
st.markdown('<div class="wizard-step">', unsafe_allow_html=True)
st.markdown('<h3 class="step-title">3. Select Design Vehicle</h3>', unsafe_allow_html=True)
df_v = active_data["vehicles"]
display_names = df_v['Name'] + " (" + df_v['Symbol'] + ")"
selected_v = st.selectbox("Vehicle Type:", display_names)

v_symbol = selected_v.split("(")[-1].replace(")", "")
v_row = df_v[df_v['Symbol'] == v_symbol].iloc[0]

c1, c2 = st.columns(2)
c1.markdown(f'<div class="result-box">Min Turning Radius<br><span class="result-value">{v_row["Min_R"]} m</span></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="result-box">Inside Radius<br><span class="result-value">{v_row["Inside_R"]} m</span></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ================= STEP 4: TYPICAL CROSS SECTION =================
st.markdown('<div class="wizard-step">', unsafe_allow_html=True)
st.markdown('<h3 class="step-title">4. Typical Cross Section (Asymmetric)</h3>', unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([1, 0.5, 1])
with col_left:
    st.markdown("#### ⬅️ Left Direction")
    l_lanes = st.number_input("Number of Lanes (Left)", min_value=0, max_value=6, value=2)
    l_width = st.number_input("Lane Width (m) (Left)", min_value=2.0, max_value=4.0, value=3.3, step=0.1)
    l_sw = st.number_input("Sidewalk/Shoulder (Left)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)

with col_mid:
    st.markdown("#### 🟩 Median")
    median = st.number_input("Median Width (m)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)

with col_right:
    st.markdown("#### ➡️ Right Direction")
    r_lanes = st.number_input("Number of Lanes (Right)", min_value=0, max_value=6, value=2)
    r_width = st.number_input("Lane Width (m) (Right)", min_value=2.0, max_value=4.0, value=3.6, step=0.1)
    r_sw = st.number_input("Sidewalk/Shoulder (Right)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)

l_total = (l_lanes * l_width)
r_total = (r_lanes * r_width)
total_row = l_sw + l_total + median + r_total + r_sw

# رسمة تفاعلية للقطاع العرضي بنسب حقيقية
st.markdown(f"**Total ROW Width: <span style='color:#007bff; font-size:20px;'>{round(total_row, 2)} m</span>**", unsafe_allow_html=True)

diagram_html = f"""
<div style="display: flex; width: 100%; height: 80px; text-align: center; color: white; font-weight: bold; font-family: sans-serif; border-radius: 8px; overflow: hidden; margin-top: 10px;">
    <div style="flex: {max(l_sw, 0.1)}; background-color: #95a5a6; display: flex; align-items: center; justify-content: center; border-right: 2px solid white;">SW<br>{l_sw}m</div>
    <div style="flex: {max(l_total, 0.1)}; background-color: #34495e; display: flex; align-items: center; justify-content: center; border-right: 2px dashed white;">Left Lanes<br>{round(l_total,2)}m</div>
    <div style="flex: {max(median, 0.1)}; background-color: #2ecc71; display: flex; align-items: center; justify-content: center;">Median<br>{median}m</div>
    <div style="flex: {max(r_total, 0.1)}; background-color: #34495e; display: flex; align-items: center; justify-content: center; border-left: 2px dashed white;">Right Lanes<br>{round(r_total,2)}m</div>
    <div style="flex: {max(r_sw, 0.1)}; background-color: #95a5a6; display: flex; align-items: center; justify-content: center; border-left: 2px solid white;">SW<br>{r_sw}m</div>
</div>
"""
st.markdown(diagram_html, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ================= STEP 5: GENERATE REPORT =================
st.markdown('<div class="wizard-step">', unsafe_allow_html=True)
st.markdown('<h3 class="step-title">5. Generate Calculation Note</h3>', unsafe_allow_html=True)

if st.button("📄 Download Word Report", use_container_width=True, type="primary"):
    doc = Document()
    doc.add_heading('CO-BODR - Highway Design Report', 0)
    
    doc.add_heading('1. Project Design Criteria', level=1)
    doc.add_paragraph(f"Design Code: {selected_code}")
    doc.add_paragraph(f"Design Speed: {selected_speed} km/h")
    doc.add_paragraph(f"Required Crest K-Value: {req_k_crest}")
    doc.add_paragraph(f"Required Sag K-Value: {req_k_sag}")
    
    doc.add_heading('2. Vehicle Turning Radius', level=1)
    doc.add_paragraph(f"Design Vehicle: {v_row['Name']} ({v_row['Symbol']})")
    doc.add_paragraph(f"Minimum Design Radius: {v_row['Min_R']} m")
    doc.add_paragraph(f"Minimum Inside Radius: {v_row['Inside_R']} m")
    
    doc.add_heading('3. Typical Cross Section', level=1)
    doc.add_paragraph(f"Left Direction: {l_lanes} Lanes @ {l_width}m | Sidewalk: {l_sw}m")
    doc.add_paragraph(f"Median Width: {median} m")
    doc.add_paragraph(f"Right Direction: {r_lanes} Lanes @ {r_width}m | Sidewalk: {r_sw}m")
    p = doc.add_paragraph()
    p.add_run(f"Total Right-of-Way (ROW) Width: {round(total_row, 2)} m").bold = True
    
    bio = io.BytesIO()
    doc.save(bio)
    st.download_button("⬇️ Click Here to Download Report", data=bio.getvalue(), file_name="COBODR_Report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
st.markdown('</div>', unsafe_allow_html=True)
