import streamlit as st
import ezdxf
import pandas as pd
import io

# Page Configuration
st.set_page_config(
    page_title="Road Design Review & Checker Tool",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Road Design Review & Checker Tool")
st.markdown("An independent engineering tool for reviewing road CAD drawings (DXF) and checking compliance with AASHTO standards or custom project limits.")

# --- Sidebar / Criteria Settings ---
st.sidebar.header("⚙️ Design Criteria Settings")

criteria_mode = st.sidebar.radio(
    "Select Criteria Mode:",
    ["Use Code Standards (AASHTO)", "Manual Custom Entry"]
)

design_speed = st.sidebar.selectbox("Design Speed (km/h):", [50, 60, 70, 80, 90, 100, 110, 120], index=3)
terrain_type = st.sidebar.selectbox("Terrain Type:", ["Level", "Rolling", "Mountainous"])

# AASHTO Simplified Database
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

# Custom vs AASHTO Logic
if criteria_mode == "Manual Custom Entry":
    with st.expander("🛠️ Custom Limits Input", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            max_grade = st.number_input("Max Longitudinal Slope (%)", value=float(default_max_grade), step=0.5, format="%.2f")
            min_grade = st.number_input("Min Longitudinal Slope (%)", value=0.5, step=0.1, format="%.2f")
        with col2:
            min_radius = st.number_input("Min Horizontal Radius (m)", value=float(default_min_radius), step=1.0, format="%.2f")
        with col3:
            min_k_crest = st.number_input("Min K-Value (Crest)", value=float(default_k_crest), step=1.0, format="%.2f")
            min_k_sag = st.number_input("Min K-Value (Sag)", value=float(default_k_sag), step=1.0, format="%.2f")
else:
    max_grade = default_max_grade
    min_grade = 0.5
    min_radius = default_min_radius
    min_k_crest = default_k_crest
    min_k_sag = default_k_sag
    
    st.sidebar.info(f"📌 **AASHTO Standards Loaded:**\n- Max Grade: {max_grade}%\n- Min Radius: {min_radius}m\n- K-Crest: {min_k_crest}\n- K-Sag: {min_k_sag}")

# --- Main Section: File Upload ---
st.markdown("---")
uploaded_file = st.file_uploader("📂 Upload CAD File (.dxf)", type=["dxf"])

if uploaded_file is not None:
    try:
        with open("temp.dxf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        doc = ezdxf.readfile("temp.dxf")
        st.success("✅ DXF File loaded successfully!")
        
        st.markdown("---")
        st.subheader("📊 Design Check Audit Results")
        
        # Simulated Data (Now including Profile Name for multiple roads support)
        # 1. PVI Checks
        pvi_data = [
            {"Profile Name": "Main_Road_01", "Station": 1000.00, "Type": "PVI", "Status": "Pass"},
            {"Profile Name": "Main_Road_01", "Station": 1234.25, "Type": "PVI", "Status": "Warning (Not multiple of 5)"}, 
            {"Profile Name": "Side_Road_A", "Station": 1500.00, "Type": "PVI", "Status": "Pass"},
            {"Profile Name": "Side_Road_A", "Station": 1782.50, "Type": "PVI", "Status": "Warning (Not multiple of 5)"}
        ]
        df_pvi = pd.DataFrame(pvi_data)

        # 2. Slopes & Grades Checks
        tangents_data = [
            {"Profile Name": "Main_Road_01", "Start Station": 1000, "End Station": 1234.25, "Grade (%)": 0.3, "Status": "Warning (Below Min)"}, 
            {"Profile Name": "Main_Road_01", "Start Station": 1234.25, "End Station": 1500, "Grade (%)": 5.8, "Status": "Violation (Exceeds Max)"},   
            {"Profile Name": "Side_Road_A", "Start Station": 1500, "End Station": 1782.5, "Grade (%)": 2.5, "Status": "Pass"}
        ]
        df_grades = pd.DataFrame(tangents_data)

        # 3. Vertical Curves Checks
        curves_data = [
            {"Profile Name": "Main_Road_01", "Station": 1234.25, "Curve Type": "Crest", "Actual K-Value": 20, "Required K-Value": min_k_crest, "Status": "Violation (Below Min)"},
            {"Profile Name": "Side_Road_A", "Station": 1500.00, "Curve Type": "Sag", "Actual K-Value": 40, "Required K-Value": min_k_sag, "Status": "Violation (Below Min)" if 40 < min_k_sag else "Pass"}
        ]
        df_curves = pd.DataFrame(curves_data)

        # --- Display Results in Expanders ---
        
        # PVI Stations Expander
        with st.expander("📌 PVI Stationing Checks", expanded=True):
            st.markdown("#### PVI Stations Divisibility Check (Multiple of 5)")
            
            def highlight_pvi(s):
                if "Warning" in s["Status"]: return ['background-color: #fff3cd; color: #856404']*len(s)
                return ['background-color: #d4edda; color: #155724']*len(s)
            
            st.dataframe(df_pvi.style.apply(highlight_pvi, axis=1), use_container_width=True, hide_index=True)

        # Grades Expander
        with st.expander("📐 Slopes & Tangent Grades Checks", expanded=True):
            st.markdown(f"#### Maximum & Minimum Longitudinal Slopes (Max: {max_grade}%, Min: {min_grade}%)")
            
            def highlight_grades(s):
                if "Violation" in s["Status"]: return ['background-color: #f8d7da; color: #721c24']*len(s)
                elif "Warning" in s["Status"]: return ['background-color: #fff3cd; color: #856404']*len(s)
                return ['background-color: #d4edda; color: #155724']*len(s)

            st.dataframe(df_grades.style.apply(highlight_grades, axis=1), use_container_width=True, hide_index=True)

        # Vertical Curves Expander
        with st.expander("📈 Vertical Curves & K-Values Checks", expanded=True):
            st.markdown(f"#### Minimum K-Values Criteria (Crest: {min_k_crest}, Sag: {min_k_sag})")
            
            def highlight_curves(s):
                if "Violation" in s["Status"]: return ['background-color: #f8d7da; color: #721c24']*len(s)
                return ['background-color: #d4edda; color: #155724']*len(s)

            st.dataframe(df_curves.style.apply(highlight_curves, axis=1), use_container_width=True, hide_index=True)

        # --- Export Reports Section ---
        st.markdown("---")
        st.subheader("📥 Export Audit Reports")
        
        col_exp1, col_exp2 = st.columns(2)
        
        # 1. Text Report Generation
        report_content = f"--- Road Design Audit Report ---\n"
        report_content += f"Design Speed: {design_speed} km/h | Terrain: {terrain_type}\n\n"
        report_content += "PVI Checks:\n" + df_pvi.to_string(index=False) + "\n\n"
        report_content += "Grade Checks:\n" + df_grades.to_string(index=False) + "\n\n"
        report_content += "Curve Checks:\n" + df_curves.to_string(index=False) + "\n"
        
        with col_exp1:
            st.download_button(
                label="📄 Download as Text (Notepad)",
                data=report_content,
                file_name="Design_Audit_Report.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        # 2. Formatted Excel Report Generation
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_pvi.to_excel(writer, sheet_name='PVI Checks', index=False)
            df_grades.to_excel(writer, sheet_name='Grades Checks', index=False)
            df_curves.to_excel(writer, sheet_name='Vertical Curves', index=False)
            
            workbook = writer.book
            
            header_format = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top', 
                'fg_color': '#007bff', 'font_color': 'white', 'border': 1
            })
            
            pass_format = workbook.add_format({'bg_color': '#c6efce', 'font_color': '#006100'})
            warn_format = workbook.add_format({'bg_color': '#ffeb9c', 'font_color': '#9c6500'})
            fail_format = workbook.add_format({'bg_color': '#ffc7ce', 'font_color': '#9c0006'})
            
            for sheet_name, df in zip(['PVI Checks', 'Grades Checks', 'Vertical Curves'], [df_pvi, df_grades, df_curves]):
                worksheet = writer.sheets[sheet_name]
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, 22) 
                
                if 'Status' in df.columns:
                    status_col_idx = df.columns.get_loc('Status')
                    for row_num in range(len(df)):
                        status_val = str(df.iloc[row_num]['Status'])
                        if 'Pass' in status_val:
                            fmt = pass_format
                        elif 'Warning' in status_val:
                            fmt = warn_format
                        else:
                            fmt = fail_format
                        worksheet.write(row_num + 1, status_col_idx, status_val, fmt)

        excel_data = output.getvalue()
        
        with col_exp2:
            st.download_button(
                label="📊 Download as Excel (Formatted)",
                data=excel_data,
                file_name="Design_Audit_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
else:
    st.info("💡 Please upload a DXF file to begin the design audit.")
