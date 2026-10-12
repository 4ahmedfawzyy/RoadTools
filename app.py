import streamlit as st
import pandas as pd
import io
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ----------------- إعدادات الصفحة -----------------
st.set_page_config(page_title="Road Design Toolkit", layout="wide")

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

# أسماء ملفات الصور المرتبطة بكل رمز
vehicle_images = {
    'P': 'Passenger Car Turning Radius.png',
    'SU-12': 'SU-12 Turning Radius.png',
    'BUS-12': 'BUS-12 Turning Radius.png',
    'WB-12': 'WB-12 Turning Radius.png',
    'WB-20': 'WB-20 Turning Radius.png'
}

# بيانات K-Value (AASHTO)
k_values_data = {
    "Crest": {20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124},
    "Sag": {20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73}
}

# ----------------- دالة إنشاء ملف Word -----------------
def generate_word_report():
    doc = Document()
    doc.add_heading('Road Design - Calculation Note', 0)
    
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
            
            # إدراج صورة العربة إذا كانت موجودة
            img_path = vehicle_images.get(item['symbol'])
            if img_path and os.path.exists(img_path):
                doc.add_picture(img_path, width=Inches(5.5))
                doc.add_paragraph(f"Figure: Turning path for {item['symbol']}")
            
            # رسم جدول AASHTO وتظليل الصف باللون الأحمر
            doc.add_heading('AASHTO Table 2-2a (Reference):', level=2)
            table = doc.add_table(rows=1, cols=len(df_turning.columns))
            table.style = 'Table Grid'
            
            # إضافة العناوين
            hdr_cells = table.rows[0].cells
            for i, column in enumerate(df_turning.columns):
                hdr_cells[i].text = column
                
            # إضافة البيانات وتظليل الصف المطلوب
            for index, row in df_turning.iterrows():
                row_cells = table.add_row().cells
                for i, column in enumerate(df_turning.columns):
                    row_cells[i].text = str(row[column])
                
                # إذا كان هذا هو صف المركبة المختارة، لونه بالأحمر الفاتح
                if row['Symbol'] == item['symbol']:
                    for cell in row_cells:
                        shading_elm = parse_xml(r'<w:shd {} w:fill="FFCCCC"/>'.format(nsdecls('w')))
                        cell._tc.get_or_add_tcPr().append(shading_elm)
            doc.add_paragraph("_" * 50)

    return doc

# ----------------- واجهة المستخدم القائمة الجانبية -----------------
st.sidebar.title("🛠️ Road Design Toolkit")
st.sidebar.markdown("---")
selected_tool = st.sidebar.radio("Select Tool:", ["🛣️ K-Value Calculator", "🔄 Turning Radius"])
st.sidebar.markdown("---")

# زر تحميل التقرير في القائمة الجانبية
st.sidebar.subheader("📄 Report Generator")
if st.sidebar.button("Generate Word Report"):
    if st.session_state.report_data:
        doc = generate_word_report()
        bio = io.BytesIO()
        doc.save(bio)
        st.sidebar.download_button(
            label="⬇️ Download Calculation Note",
            data=bio.getvalue(),
            file_name="Calculation_Note.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        st.sidebar.warning("Add some calculations to the report first!")

# ----------------- أداة K-Value -----------------
if selected_tool == "🛣️ K-Value Calculator":
    st.title("🛣️ Vertical Curves (K-Value)")
    
    col1, col2 = st.columns(2)
    with col1:
        curve_type = st.selectbox("Curve Type", ["Crest", "Sag"])
    with col2:
        speed = st.selectbox("Design Speed [km/h]", list(k_values_data[curve_type].keys()), index=10)
    
    required_k = k_values_data[curve_type][speed]
    st.info(f"### Required Minimum K: **{required_k}**")
    
    if st.button("➕ Add to Report"):
        st.session_state.report_data.append({
            'tool': 'K-Value', 'curve_type': curve_type, 'speed': speed, 'k_value': required_k
        })
        st.success("Added to Calculation Note!")

# ----------------- أداة Turning Radius -----------------
elif selected_tool == "🔄 Turning Radius":
    st.title("🔄 Minimum Turning Radius")
    
    # قائمة بأسماء المركبات ورموزها
    display_names = df_turning['Design Vehicle Type'] + " (" + df_turning['Symbol'] + ")"
    selected_display = st.selectbox("Select Design Vehicle:", display_names)
    
    # استخراج الرمز من الاختيار
    selected_symbol = selected_display.split("(")[-1].replace(")", "")
    
    # جلب بيانات المركبة المختارة
    vehicle_data = df_turning[df_turning['Symbol'] == selected_symbol].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Min Design Turning Radius", f"{vehicle_data['Min Design Turning Radius (m)']} m")
    col2.metric("Centerline Radius (CTR)", f"{vehicle_data['Centerline Radius (CTR) (m)']} m")
    col3.metric("Min Inside Radius", f"{vehicle_data['Min Inside Radius (m)']} m")
    
    if st.button("➕ Add to Report"):
        st.session_state.report_data.append({
            'tool': 'Turning Radius',
            'vehicle_name': vehicle_data['Design Vehicle Type'],
            'symbol': selected_symbol,
            'min_r': vehicle_data['Min Design Turning Radius (m)'],
            'ctr': vehicle_data['Centerline Radius (CTR) (m)'],
            'inside_r': vehicle_data['Min Inside Radius (m)']
        })
        st.success(f"{selected_symbol} data added to Calculation Note!")
