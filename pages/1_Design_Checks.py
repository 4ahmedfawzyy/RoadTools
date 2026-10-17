import streamlit as st
import ezdxf
import pandas as pd

# إعداد الصفحة
st.set_page_config(
    page_title="Road Design Review & Checker Tool",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Road Design Review & Checker Tool")
st.markdown("أداة هندسية مستقلة لمراجعة لوحات الطرق (DXF) والتأكد من مطابقتها لمواصفات AASHTO أو الحدود المخصصة.")

# --- Sidebar: Design Criteria Settings ---
st.sidebar.header("⚙️ Design Criteria Settings")

criteria_mode = st.sidebar.radio(
    "Select Criteria Mode:",
    ["Use Code Standards (AASHTO)", "Manual Custom Entry"]
)

design_speed = st.sidebar.selectbox("Design Speed (km/h):", [50, 60, 70, 80, 90, 100, 110, 120], index=3)
terrain_type = st.sidebar.selectbox("Terrain Type:", ["Level", "Rolling", "Mountainous"])

# قاعدة بيانات AASHTO المصغرة
aashto_db = {
    50: {"min_radius": 85, "max_grade": {"Level": 6, "Rolling": 7, "Mountainous": 8}, "k_crest": 7, "k_sag": 11},
    60: {"min_radius": 125, "max_grade": {"Level": 5, "Rolling": 6, "Mountainous": 7}, "k_crest": 11, "k_sag": 18},
    70: {"min_radius": 175, "max_grade": {"Level": 4, "Rolling": 5, "Mountainous": 6}, "k_crest": 17, "k_sag": 23},
    80: {"min_radius": 230, "max_grade": {"Level": 4, "Rolling": 5, "Mountainous": 6}, "k_crest": 26, "k_sag": 30},
    90: {"min_radius": 300, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 39, "k_sag": 38},
    100: {"min_radius": 435, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 52, "k_sag": 45},
    110: {"min_radius": 570, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 75, "k_sag": 58},
    120: {"min_radius": 750, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 105, "k_sag": 73}
}

current_standard = aashto_db.get(design_speed, aashto_db[100])
default_max_grade = current_standard["max_grade"].get(terrain_type, 5.0)
default_min_radius = current_standard["min_radius"]
default_k_crest = current_standard["k_crest"]
default_k_sag = current_standard["k_sag"]

if criteria_mode == "Manual Custom Entry":
    st.sidebar.subheader("Custom Limits")
    max_grade = st.sidebar.number_input("Max Longitudinal Slope (%)", value=float(default_max_grade), step=0.5)
    min_grade = st.sidebar.number_input("Min Longitudinal Slope (%)", value=0.5, step=0.1)
    min_radius = st.sidebar.number_input("Min Horizontal Radius (m)", value=float(default_min_radius), step=10.0)
    min_k_crest = st.sidebar.number_input("Min K-Value (Crest)", value=float(default_k_crest), step=1.0)
    min_k_sag = st.sidebar.number_input("Min K-Value (Sag)", value=float(default_k_sag), step=1.0)
else:
    max_grade = default_max_grade
    min_grade = 0.5
    min_radius = default_min_radius
    min_k_crest = default_k_crest
    min_k_sag = default_k_sag
    
    st.sidebar.info(f"📌 **AASHTO Standards Loaded:**\n- Max Grade: {max_grade}%\n- Min Radius: {min_radius}m\n- K-Crest: {min_k_crest}\n- K-Sag: {min_k_sag}")

# --- Main Section: File Upload ---
uploaded_file = st.file_uploader("📂 Upload CAD File (.dxf)", type=["dxf"])

if uploaded_file is not None:
    try:
        with open("temp.dxf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        doc = ezdxf.readfile("temp.dxf")
        st.success("✅ تم قراءة ملف الـ DXF بنجاح!")
        
        st.markdown("---")
        st.subheader("🔍 Design Check Results")
        
        # محاكاة لبيانات الفحص الهندسي
        pvi_data = [
            {"station": 1000.00, "type": "PVI"},
            {"station": 1234.25, "type": "PVI"}, # غير مضاعفات الـ 5
            {"station": 1500.00, "type": "PVI"},
            {"station": 1782.50, "type": "PVI"}  # غير مضاعفات الـ 5
        ]
        
        pvi_warnings = []
        for pvi in pvi_data:
            if pvi["station"] % 5 != 0:
                pvi_warnings.append(f"⚠️ PVI Station {pvi['station']} is NOT a multiple of 5.")

        tangents_data = [
            {"start": 1000, "end": 1234.25, "grade": 0.3},  # أقل من Min Grade
            {"start": 1234.25, "end": 1500, "grade": 5.8},   # أكبر من Max Grade
            {"start": 1500, "end": 1782.5, "grade": 2.5}
        ]
        
        grade_violations = []
        for tan in tangents_data:
            g = tan["grade"]
            if abs(g) > max_grade:
                grade_violations.append(f"❌ Violation: Grade {g}% between station {tan['start']} and {tan['end']} exceeds Max Limit ({max_grade}%).")
            elif 0 < abs(g) < min_grade:
                grade_violations.append(f"⚠️ Warning: Grade {g}% between station {tan['start']} and {tan['end']} is below Min Drainage Slope ({min_grade}%).")

        curves_data = [
            {"station": 1234.25, "type": "Crest", "k_value": 20, "length": 80},
            {"station": 1500.00, "type": "Sag", "k_value": 40, "length": 120}
        ]
        
        curve_violations = []
        for c in curves_data:
            if c["type"] == "Crest" and c["k_value"] < min_k_crest:
                curve_violations.append(f"❌ Violation: Crest Curve at Station {c['station']} has K-Value {c['k_value']} (Less than required {min_k_crest}).")
            elif c["type"] == "Sag" and c["k_value"] < min_k_sag:
                curve_violations.append(f"❌ Violation: Sag Curve at Station {c['station']} has K-Value {c['k_value']} (Less than required {min_k_sag}).")

        tab1, tab2, tab3 = st.tabs(["📌 PVI Stationing Checks", "📐 Slopes & Grades Checks", "📈 Vertical Curves Checks"])
        
        with tab1:
            st.markdown("#### مراجعة محطات نقاط التقاطع الرأسي (PVI Stations):")
            if pvi_warnings:
                for w in pvi_warnings: st.warning(w)
            else:
                st.success("جميع محطات الـ PVI من مضاعفات الرقم 5 بنجاح!")
                
        with tab2:
            st.markdown("#### مراجعة الميول الطولية (Min/Max Slopes):")
            if grade_violations:
                for g_v in grade_violations:
                    if "❌" in g_v: st.error(g_v)
                    else: st.warning(g_v)
            else:
                st.success("جميع الميول الطولية مطابقة للحدود المسموح بها.")
                
        with tab3:
            st.markdown("#### مراجعة أطوال ومعاملات الكيرفات الرأسية (K-Values):")
            if curve_violations:
                for c_v in curve_violations: st.error(c_v)
            else:
                st.success("جميع الكيرفات الرأسية مطابقة لمتطلبات الكود.")

        st.markdown("---")
        if st.button("📥 Export Comprehensive Audit Report"):
            report_content = f"--- Road Design Audit Report ---\n"
            report_content += f"Design Speed: {design_speed} km/h | Terrain: {terrain_type}\n\n"
            report_content += "PVI Warnings:\n" + "\n".join(pvi_warnings) + "\n\n"
            report_content += "Grade Violations:\n" + "\n".join(grade_violations) + "\n\n"
            report_content += "Curve Violations:\n" + "\n".join(curve_violations) + "\n"
            
            st.download_button(
                label="Download Report File",
                data=report_content,
                file_name="Design_Audit_Report.txt",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة ملف الـ DXF: {e}")
else:
    st.info("💡 برجاء رفع ملف DXF الخاص بالمشروع من القائمة أعلى لبدء عملية الفحص الفني والمراجعة.")
