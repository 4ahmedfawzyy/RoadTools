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
st.set_page_config(page_title="Highway Engineering Portal", layout="wide", page_icon="🛣️")

# ----------------- تنسيقات CSS مخصصة (لتحسين التصميم) -----------------
st.markdown("""
    <style>
    /* تنسيق الكروت (Cards) للنتائج والترحيب */
    .stCard {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border-left: 5px solid #007bff;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.05);
        text-align: center;
        border: 1px solid #e9ecef;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #007bff;
    }
    .metric-label {
        font-size: 14px;
        color: #6c757d;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- تهيئة الذاكرة للتقرير -----------------
if 'report_data' not in st.session_state:
    st.session_state.report_data = []

# ----------------- قواعد البيانات (AASHTO) -----------------
# بيانات Turning Radius
turning_data = {
    'Design Vehicle Type': [
        'Passenger Car', 'Single-Unit Truck', 'Single-Unit Truck (Three Axle)', 
        'Intercity Bus', 'Intercity Bus', 'City Transit Bus',
        'Conventional School Bus', 'Large School Bus', 'Articulated Bus',
        'Intermediate Semitrailer', 'Interstate Semitrailer', 'Interstate Semitrailer',
        'Double Bottom Combination', 'Rocky Mtn Double', 'Triple Semitrailer',
        'Turnpike Double', 'Motor Home', 'Car and Camper Trailer',
        'Car and Boat Trailer', 'Motor Home and Boat Trailer'
    ],
    'Symbol': [
        'P', 'SU-9', 'SU-12', 'BUS-12', 'BUS-14', 'CITY-BUS', 'S-BUS11', 'S-BUS12', 
        'A-BUS', 'WB-12', 'WB-19', 'WB-20', 'WB-20D', 'WB-28D', 'WB-30T', 'WB-33D', 
        'MH', 'P/T', 'P/B', 'MH/B'
    ],
    'Min Design Turning Radius (m)': [
        7.26, 12.73, 15.60, 12.70, 13.40, 12.80, 11.75, 11.92, 12.00, 12.16, 
        13.66, 13.66, 13.67, 24.98, 13.67, 18.25, 12.11, 10.03, 7.26, 15.19
    ],
    'Centerline Radius (CTR) (m)': [
        6.40, 11.58, 14.46, 11.53, 12.25, 11.52, 10.64, 10.79, 10.82, 10.97, 
        12.50, 12.50, 12.47, 23.77, 12.47, 17.04, 10.97, 9.14, 6.40, 14.02
    ],
    'Min Inside Radius (m)': [
        4.39, 8.64, 11.09, 7.41, 7.54, 7.45, 7.25, 7.71, 6.49, 5.88, 
        2.25, 0.59, 5.83, 16.94, 2.96, 4.19, 7.92, 5.58, 2.44, 10.67
    ]
}
df_turning = pd.DataFrame(turning_data)

# أسماء ملفات الصور
vehicle_images = {
    'P': 'Passenger Car Turning Radius.png',
    'SU-12': 'SU-12 Turning Radius.png',
    'BUS-12': 'BUS-12 Turning Radius.png',
    'WB-12': 'WB-12 Turning Radius.png',
    'WB-20': 'WB-20 Turning Radius.png'
}

# بيانات K-Value
k_values_data = {
    "Crest": {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124},
    "Sag": {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}
}

# ----------------- دالة إنشاء ملف Word -----------------
def generate_word_report():
    doc = Document()
    doc.add_heading('Highway Engineering - Calculation Note', 0)
    
    if not st.session_state.report_data:
        doc.add_paragraph("No data added to the report yet.")
        return doc

    for item in st.session_state.report_data:
        if item['tool'] == 'K-Value':
            doc.add_heading('1. Vertical Alignment (K-Value)', level=1)
            doc.add_paragraph(f"Curve Type: {item['curve_type']}")
            doc.add_paragraph(f"Design Speed: {item['speed']} km/h")
            p = doc.add_paragraph()
            p.add_run(f"Required Minimum K-Value: {item['k_value']}").bold = True
            doc.add_paragraph("_" * 50)
            
        elif item['tool'] == 'Turning Radius':
            doc.add_heading('2. Horizontal Alignment (Turning Radius)', level=1)
            doc.add_paragraph(f"Design Vehicle: {item['vehicle_name']} ({item['symbol']})")
            p = doc.add_paragraph()
            p.add_run(f"Minimum Design Turning Radius: {item['min_r']} m\n").bold = True
            p.add_run(f"Centerline Turning Radius (CTR): {item['ctr']} m\n")
            p.add_run(f"Minimum Inside Radius: {item['inside_r']} m")
            
            img_path = vehicle_images.get(item['symbol'])
            if img_path and os.path.exists(img_path):
                doc.add_picture(img_path, width=Inches(5.5))
                doc.add_paragraph(f"Figure: Turning path for {item['symbol']}")
            
            doc.add_heading('AASHTO Table 2-2a (Reference):', level=2)
            table = doc.add_table(rows=1, cols=len(df_turning.columns))
            table.style = 'Table Grid'
            
            hdr_cells = table.rows[0].cells
            for i, column in enumerate(df_turning.columns):
                hdr_cells[i].text = column
                
            for index, row in df_turning.iterrows():
                row_cells = table.add_row().cells
                for i, column in enumerate(df_turning.columns):
                    row_cells[i].text = str(row[column])
                
                if row['Symbol'] == item['symbol']:
                    for cell in row_cells:
                        shading_elm = parse_xml(r'<w:shd {} w:fill="FFCCCC"/>'.format(nsdecls('w')))
                        cell._tc.get_or_add_tcPr().append(shading_elm)
            doc.add_paragraph("_" * 50)
    return doc

# ----------------- القائمة الجانبية الاحترافية -----------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3272/3272089.png", width=100) # صورة تعبيرية للطرق
    st.title("Ahmed's Portal")
    
    selected_tool = option_menu(
        menu_title="Main Menu",
        options=["Home", "K-Value Calculator", "Turning Radius"],
        icons=["house", "bezier2", "arrow-repeat"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "18px"},
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#007bff"},
        }
    )
    
    st.markdown("---")
    st.markdown("### 📄 Report Center")
    if st.button("Generate Word Report", use_container_width=True):
        if st.session_state.report_data:
            doc = generate_word_report()
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(
                label="⬇️ Download Calculation Note",
                data=bio.getvalue(),
                file_name="Calculation_Note.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:
            st.warning("No data added yet.")

# ----------------- محتوى الصفحات -----------------

# 1. الصفحة الرئيسية (Home)
if selected_tool == "Home":
    st.title("Welcome to Highway Engineering Portal")
    st.markdown("""
        <div class="stCard">
            <h4>Engineering Tools at Your Fingertips</h4>
            <p>This portal is designed to streamline road design calculations according to <strong>AASHTO</strong> standards. 
            Select a tool from the sidebar to begin your calculations, add results to your report, and generate a comprehensive Word document with a single click.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class="stCard">
                <h5>🛣️ Vertical Alignment</h5>
                <p>Calculate the required Minimum K-Value for Crest and Sag vertical curves based on design speed.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="stCard">
                <h5>🔄 Horizontal Alignment</h5>
                <p>Determine Minimum Turning Radii and generate turning paths for various AASHTO design vehicles.</p>
            </div>
        """, unsafe_allow_html=True)

# 2. أداة K-Value
elif selected_tool == "K-Value Calculator":
    st.title("🛣️ Vertical Curves (K-Value)")
    
    st.markdown('<div class="stCard">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        curve_type = st.selectbox("Select Curve Type", ["Crest", "Sag"])
    with col2:
        speed = st.selectbox("Design Speed [km/h]", list(k_values_data[curve_type].keys()), index=10)
    st.markdown('</div>', unsafe_allow_html=True)
    
    required_k = k_values_data[curve_type][speed]
    
    st.markdown(f"""
        <div class="metric-card" style="margin-bottom: 20px;">
            <div class="metric-label">Required Minimum K-Value</div>
            <div class="metric-value">{required_k}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({
            'tool': 'K-Value', 'curve_type': curve_type, 'speed': speed, 'k_value': required_k
        })
        st.success("Successfully added to your Calculation Note!")

# 3. أداة Turning Radius
elif selected_tool == "Turning Radius":
    st.title("🔄 Minimum Turning Radius")
    
    st.markdown('<div class="stCard">', unsafe_allow_html=True)
    display_names = df_turning['Design Vehicle Type'] + " (" + df_turning['Symbol'] + ")"
    selected_display = st.selectbox("Select Design Vehicle:", display_names)
    st.markdown('</div>', unsafe_allow_html=True)
    
    selected_symbol = selected_display.split("(")[-1].replace(")", "")
    vehicle_data = df_turning[df_turning['Symbol'] == selected_symbol].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Min Design Turning Radius</div><div class="metric-value">{vehicle_data['Min Design Turning Radius (m)']} m</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Centerline Radius (CTR)</div><div class="metric-value">{vehicle_data['Centerline Radius (CTR) (m)']} m</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Min Inside Radius</div><div class="metric-value">{vehicle_data['Min Inside Radius (m)']} m</div></div>""", unsafe_allow_html=True)
    
    st.write("") # مسافة فارغة
    if st.button("➕ Add to Report", type="primary"):
        st.session_state.report_data.append({
            'tool': 'Turning Radius',
            'vehicle_name': vehicle_data['Design Vehicle Type'],
            'symbol': selected_symbol,
            'min_r': vehicle_data['Min Design Turning Radius (m)'],
            'ctr': vehicle_data['Centerline Radius (CTR) (m)'],
            'inside_r': vehicle_data['Min Inside Radius (m)']
        })
        st.success(f"Data for {selected_symbol} has been added to your Calculation Note!")
