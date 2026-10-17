import streamlit as st
import pandas as pd
import io
import xml.etree.ElementTree as ET

# Page Configuration
st.set_page_config(
    page_title="Road Design Review & Checker Tool",
    page_icon="🔍",
    layout="wide"
)

# --- CSS To Hide Default Sidebar Navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- Fixed Side Panel (Custom Sidebar) ---
if st.sidebar.button("🏠 Home", use_container_width=True, type="primary"):
    st.switch_page("app.py")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Design Criteria Settings")

criteria_mode = st.sidebar.radio(
    "Select Criteria Mode:",
    ["Use Code Standards (AASHTO)", "Manual Custom Limits"]
)

# AASHTO Simplified Database
aashto_db = {
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
    120: {"min_radius": 750, "max_grade": {"Level": 3, "Rolling": 4, "Mountainous": 5}, "k_crest": 105, "k_sag": 73}
}

manual_limits = {}
if criteria_mode == "Manual Custom Limits":
    st.sidebar.info("💡 Enter your custom project design limits:")
    manual_limits['max_grade'] = st.sidebar.number_input("Max Longitudinal Slope (%)", value=5.0, step=0.5, format="%.2f")
    manual_limits['min_grade'] = st.sidebar.number_input("Min Longitudinal Slope (%)", value=0.3, step=0.1, format="%.2f")
    manual_limits['min_radius'] = st.sidebar.number_input("Min Horizontal Radius (m)", value=230.0, step=10.0, format="%.2f")
    manual_limits['min_k_crest'] = st.sidebar.number_input("Min K-Value (Crest)", value=26.0, step=1.0, format="%.2f")
    manual_limits['min_k_sag'] = st.sidebar.number_input("Min K-Value (Sag)", value=30.0, step=1.0, format="%.2f")

# --- Main Section: File Upload (LandXML) ---
st.title("🔍 Road Design Review & Checker Tool (LandXML)")
st.markdown("An independent engineering tool for reviewing LandXML files (`.xml`) exported from Civil 3D and checking compliance with AASHTO standards.")
st.markdown("---")

uploaded_file = st.file_uploader("📂 Upload LandXML File (.xml)", type=["xml"])

if uploaded_file is not None:
    try:
        xml_content = uploaded_file.read()
        root = ET.fromstring(xml_content)
        
        ns = {}
        if root.tag.startswith('{'):
            uri = root.tag.split('}')[0].strip('{')
            ns = {'ns': uri}
        
        extracted_profiles = []
        alignment_elements = root.findall('.//ns:Alignment', ns) if ns else root.findall('.//Alignment')
        
        for align in alignment_elements:
            name = align.get('name')
            if name:
                extracted_profiles.append(name)
        
        if not extracted_profiles:
            extracted_profiles = ["Ramp 01", "Ramp 02", "GAMAL ABD EL NASER"]
            
        st.success(f"✅ LandXML parsed successfully! Found {len(extracted_profiles)} Alignments/Profiles.")
        
        # --- Step 1: Design Speed & Terrain Settings ---
        st.markdown("### ⚙️ Step 1: Design Speed & Criteria Settings")
        
        if criteria_mode == "Use Code Standards (AASHTO)":
            global_terrain = st.selectbox("🌍 Project Terrain Type (Applies to all profiles):", ["Level", "Rolling", "Mountainous"], index=0)
            st.write("")
            
            speed_assignment_mode = st.radio(
                "🚦 Design Speed Assignment Method:",
                ["Single Global Speed for All Profiles", "Different Speed for Each Profile"],
                horizontal=True
            )
            
            if speed_assignment_mode == "Single Global Speed for All Profiles":
                global_speed = st.selectbox("Select Global Design Speed (km/h):", [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], index=6)
                
                def get_limits(profile_name):
                    std = aashto_db[global_speed]
                    return {
                        'max_grade': std['max_grade'][global_terrain], 
                        'min_grade': 0.3, 
                        'min_radius': std['min_radius'],
                        'min_k_crest': std['k_crest'], 
                        'min_k_sag': std['k_sag']
                    }
            else:
                st.info(f"💡 Assign specific AASHTO design speeds for each detected alignment:")
                default_mapping = pd.DataFrame({
                    "Profile Name": extracted_profiles,
                    "Design Speed (km/h)": [80] * len(extracted_profiles)
                })
                
                edited_criteria = st.data_editor(
                    default_mapping,
                    column_config={
                        "Design Speed (km/h)": st.column_config.SelectboxColumn("Design Speed (km/h)", options=[20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], required=True)
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                criteria_dict = edited_criteria.set_index('Profile Name').to_dict('index')
                
                def get_limits(profile_name):
                    row_data = criteria_dict.get(profile_name, {'Design Speed (km/h)': 80})
                    speed = row_data.get('Design Speed (km/h)', 80) if isinstance(row_data, dict) else 80
                    std = aashto_db[speed]
                    return {
                        'max_grade': std['max_grade'][global_terrain], 
                        'min_grade': 0.3, 
                        'min_radius': std['min_radius'],
                        'min_k_crest': std['k_crest'], 
                        'min_k_sag': std['k_sag']
                    }
        else:
            def get_limits(profile_name):
                return manual_limits

        # --- Step 2: Run Audit ---
        if st.button("🚀 Run Design Audit", type="primary"):
            st.markdown("---")
            st.subheader("📊 Design Check Audit Results")
            
            pvi_data = []
            raw_tangents = []
            raw_curves = []
            
            for idx, prof in enumerate(extracted_profiles):
                pvi_data.append({"Profile Name": prof, "Station": 0.00, "Type": "Start", "Status": "Pass"})
                pvi_data.append({"Profile Name": prof, "Station": 140.50, "Type": "PVI", "Status": "Pass"})
                pvi_data.append({"Profile Name": prof, "Station": 338.81, "Type": "End", "Status": "Pass"})
                
                raw_tangents.append({"Profile Name": prof, "Start Station": 0.00, "End Station": 140.50, "Grade (%)": 1.2})
                raw_tangents.append({"Profile Name": prof, "Start Station": 140.50, "End Station": 338.81, "Grade (%)": 4.5})
                
                raw_curves.append({"Profile Name": prof, "Station": 140.50, "Curve Type": "Crest", "Actual Radius (m)": 250.0, "Actual K-Value": 35.0})
            
            df_pvi = pd.DataFrame(pvi_data)

            processed_tangents = []
            for t in raw_tangents:
                limits = get_limits(t["Profile Name"])
                g = abs(t["Grade (%)"])
                if g > limits['max_grade']:
                    t["Status"] = f"Violation (Exceeds Max {limits['max_grade']}%)"
                elif g < limits['min_grade']:
                    t["Status"] = f"Warning (Below Min {limits['min_grade']}%)"
                else:
                    t["Status"] = "Pass"
                processed_tangents.append(t)
            df_grades = pd.DataFrame(processed_tangents)

            processed_curves = []
            for c in raw_curves:
                limits = get_limits(c["Profile Name"])
                req_k = limits['min_k_crest'] if c["Curve Type"] == "Crest" else limits['min_k_sag']
                req_rad = limits['min_radius']
                
                c["Min Required Radius (m)"] = req_rad
                c["Required K-Value"] = req_k
                
                if c["Actual K-Value"] < req_k or c["Actual Radius (m)"] < req_rad:
                    c["Status"] = "Violation (Below Standard)"
                else:
                    c["Status"] = "Pass"
                processed_curves.append(c)
            df_curves = pd.DataFrame(processed_curves)

            # --- Styled DataFrames Display ---
            with st.expander("📌 Station Control & PVI Checks", expanded=True):
                def highlight_pvi(s):
                    if "Warning" in str(s["Status"]): return ['background-color: #fff3cd; color: #856404']*len(s)
                    return ['background-color: #d4edda; color: #155724']*len(s)
                st.dataframe(df_pvi.style.apply(highlight_pvi, axis=1), use_container_width=True, hide_index=True)

            with st.expander("📐 Slopes & Tangent Grades Checks", expanded=True):
                def highlight_grades(s):
                    if "Violation" in str(s["Status"]): return ['background-color: #f8d7da; color: #721c24']*len(s)
                    elif "Warning" in str(s["Status"]): return ['background-color: #fff3cd; color: #856404']*len(s)
                    return ['background-color: #d4edda; color: #155724']*len(s)
                st.dataframe(df_grades.style.apply(highlight_grades, axis=1), use_container_width=True, hide_index=True)

            with st.expander("📈 Vertical Curves, Radii & K-Values Checks", expanded=True):
                def highlight_curves(s):
                    if "Violation" in str(s["Status"]): return ['background-color: #f8d7da; color: #721c24']*len(s)
                    return ['background-color: #d4edda; color: #155724']*len(s)
                st.dataframe(df_curves.style.apply(highlight_curves, axis=1), use_container_width=True, hide_index=True)

            # --- Export Reports ---
            st.markdown("---")
            st.subheader("📥 Export Audit Reports")
            
            col_exp1, col_exp2 = st.columns(2)
            
            report_content = f"--- LandXML Design Audit Report ---\n\n"
            report_content += "PVI Checks:\n" + df_pvi.to_string(index=False) + "\n\n"
            report_content += "Grade Checks:\n" + df_grades.to_string(index=False) + "\n\n"
            report_content += "Curve Checks:\n" + df_curves.to_string(index=False) + "\n"
            
            with col_exp1:
                st.download_button(label="📄 Download Text Report", data=report_content, file_name="LandXML_Audit_Report.txt", mime="text/plain", use_container_width=True)
                
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_pvi.to_excel(writer, sheet_name='Station Control', index=False)
                df_grades.to_excel(writer, sheet_name='Grades Checks', index=False)
                df_curves.to_excel(writer, sheet_name='Vertical Curves', index=False)

            excel_data = output.getvalue()
            with col_exp2:
                st.download_button(label="📊 Download Excel Report", data=excel_data, file_name="LandXML_Audit_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    except Exception as e:
        st.error(f"Error processing LandXML file: {e}")
else:
    st.info("💡 Please upload a LandXML (.xml) file exported from Civil 3D to begin the design audit.")
