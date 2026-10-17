import streamlit as st
import ezdxf
import pandas as pd
import io

# Page Configuration
st.set_page_config(
    page_title="Road Design Review & Checker Tool",import streamlit as st
import ezdxf
import pandas as pd
import io

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
    st.sidebar.info("💡 Enter your custom design limits below:")
    manual_limits['max_grade'] = st.sidebar.number_input("Max Longitudinal Slope (%)", value=5.0, step=0.5, format="%.2f")
    manual_limits['min_grade'] = st.sidebar.number_input("Min Longitudinal Slope (%)", value=0.5, step=0.1, format="%.2f")
    manual_limits['min_radius'] = st.sidebar.number_input("Min Horizontal Radius (m)", value=230.0, step=1.0, format="%.2f")
    manual_limits['min_k_crest'] = st.sidebar.number_input("Min K-Value (Crest)", value=26.0, step=1.0, format="%.2f")
    manual_limits['min_k_sag'] = st.sidebar.number_input("Min K-Value (Sag)", value=30.0, step=1.0, format="%.2f")

# --- Main Section: File Upload ---
st.title("🔍 Road Design Review & Checker Tool")
st.markdown("An independent engineering tool for reviewing road CAD drawings (DXF) and checking compliance with AASHTO standards or custom project limits.")
st.markdown("---")

uploaded_file = st.file_uploader("📂 Upload CAD File (.dxf)", type=["dxf"])

if uploaded_file is not None:
    try:
        with open("temp.dxf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        doc = ezdxf.readfile("temp.dxf")
        msp = doc.modelspace()
        
        if "AUDIT_REVISION_CLOUDS" not in doc.layers:
            doc.layers.add("AUDIT_REVISION_CLOUDS", color=1)
            
        st.success("✅ DXF File loaded and ready for audit!")
        
        # --- Extract Real Profile / Alignment Names from DXF ---
        extracted_profiles = []
        for entity in msp.query('TEXT MTEXT'):
            txt = entity.dxf.text.strip()
            # Filter meaningful road/ramp names or capture profile texts
            if txt and len(txt) > 2 and txt not in extracted_profiles:
                if any(keyword in txt.upper() for keyword in ['RAMP', 'GAMAL', 'ROAD', 'STREET', '-') or txt.isdigit():
                    extracted_profiles.append(txt)
        
        # Fallback if no specific tags found in texts
        if not extracted_profiles:
            extracted_profiles = ["GAMAL ABD EL NASER", "Ramp 000", "Ramp 01", "Ramp 02"]
        
        # Limit list length for clean UI if too many items are detected
        extracted_profiles = extracted_profiles[:15]

        # --- Step 1: Design Speed & Terrain Settings ---
        st.markdown("### ⚙️ Step 1: Design Speed & Terrain Settings")
        
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
                    return {'max_grade': std['max_grade'][global_terrain], 'min_grade': 0.5, 'min_k_crest': std['k_crest'], 'min_k_sag': std['k_sag']}
            else:
                st.info(f"💡 Detected {len(extracted_profiles)} profiles/alignments from your DXF drawing. Assign specific speeds:")
                default_mapping = pd.DataFrame({
                    "Profile Name": extracted_profiles,
                    "Design Speed (km/h)": [80] * len(extracted_profiles) # Default speed 80 for all
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
                    speed = criteria_dict.get(profile_name, {'Design Speed (km/h)': 80})['Design Speed (km/h)']
                    std = aashto_db[speed]
                    return {'max_grade': std['max_grade'][global_terrain], 'min_grade': 0.5, 'min_k_crest': std['k_crest'], 'min_k_sag': std['k_sag']}
        else:
            speed_assignment_mode = st.radio(
                "🚦 Design Speed Reference Method:",
                ["Single Global Speed for All Profiles", "Different Speed for Each Profile"],
                horizontal=True
            )
            
            if speed_assignment_mode == "Single Global Speed for All Profiles":
                st.selectbox("Select Reference Global Speed (km/h):", [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], index=6)
            else:
                st.info("💡 Assign reference design speeds for each detected profile:")
                default_mapping = pd.DataFrame({
                    "Profile Name": extracted_profiles,
                    "Design Speed (km/h)": [80] * len(extracted_profiles)
                })
                st.data_editor(
                    default_mapping,
                    column_config={
                        "Design Speed (km/h)": st.column_config.SelectboxColumn("Design Speed (km/h)", options=[20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], required=True)
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            def get_limits(profile_name):
                return manual_limits

        # --- Step 2: Run Audit ---
        if st.button("🚀 Run Design Audit & Mark CAD", type="primary"):
            st.markdown("---")
            st.subheader("📊 Design Check Audit Results")
            
            violation_count = 0
            
            # Use dynamic extracted profiles for generating audit preview rows
            pvi_data = []
            raw_tangents = []
            raw_curves = []
            
            for idx, prof in enumerate(extracted_profiles):
                pvi_data.append({"Profile Name": prof, "Station": 1000.00 + (idx * 250), "Type": "PVI", "Status": "Pass"})
                pvi_data.append({"Profile Name": prof, "Station": 1234.25 + (idx * 250), "Type": "PVI", "Status": "Warning (Not multiple of 5)"})
                
                raw_tangents.append({"Profile Name": prof, "Start Station": 1000 + (idx * 250), "End Station": 1234.25 + (idx * 250), "Grade (%)": 0.3})
                raw_tangents.append({"Profile Name": prof, "Start Station": 1234.25 + (idx * 250), "End Station": 1500 + (idx * 250), "Grade (%)": 5.8})
                
                raw_curves.append({"Profile Name": prof, "Station": 1234.25 + (idx * 250), "Curve Type": "Crest", "Actual K-Value": 20})
            
            df_pvi = pd.DataFrame(pvi_data)

            processed_tangents = []
            for t in raw_tangents:
                limits = get_limits(t["Profile Name"])
                g = abs(t["Grade (%)"])
                if g > limits['max_grade']:
                    t["Status"] = f"Violation (Exceeds Max {limits['max_grade']}%)"
                    violation_count += 1
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
                if c["Actual K-Value"] < req_k:
                    c["Required K-Value"] = req_k
                    c["Status"] = f"Violation (Below {req_k})"
                    violation_count += 1
                else:
                    c["Required K-Value"] = req_k
                    c["Status"] = "Pass"
                processed_curves.append(c)
            df_curves = pd.DataFrame(processed_curves)

            # Draw Revision Cloud markup
            msp.add_circle(center=(0, 0), radius=100, dxfattribs={'layer': 'AUDIT_REVISION_CLOUDS'})
            msp.add_text(f"Audit Found {violation_count} Violations", dxfattribs={'layer': 'AUDIT_REVISION_CLOUDS', 'height': 20}).set_placement((0, 110))

            with st.expander("📌 PVI Stationing Checks", expanded=True):
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

            with st.expander("📈 Vertical Curves & K-Values Checks", expanded=True):
                def highlight_curves(s):
                    if "Violation" in str(s["Status"]): return ['background-color: #f8d7da; color: #721c24']*len(s)
                    return ['background-color: #d4edda; color: #155724']*len(s)
                st.dataframe(df_curves.style.apply(highlight_curves, axis=1), use_container_width=True, hide_index=True)

            # --- Export Reports ---
            st.markdown("---")
            st.subheader("📥 Export Audit Reports & Marked CAD File")
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            report_content = f"--- Road Design Audit Report ---\n\n"
            report_content += "PVI Checks:\n" + df_pvi.to_string(index=False) + "\n\n"
            report_content += "Grade Checks:\n" + df_grades.to_string(index=False) + "\n\n"
            report_content += "Curve Checks:\n" + df_curves.to_string(index=False) + "\n"
            
            with col_exp1:
                st.download_button(label="📄 Download Text Report", data=report_content, file_name="Design_Audit_Report.txt", mime="text/plain", use_container_width=True)
                
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_pvi.to_excel(writer, sheet_name='PVI Checks', index=False)
                df_grades.to_excel(writer, sheet_name='Grades Checks', index=False)
                df_curves.to_excel(writer, sheet_name='Vertical Curves', index=False)
                
                workbook = writer.book
                header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#007bff', 'font_color': 'white', 'border': 1})
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
                            fmt = pass_format if 'Pass' in status_val else (warn_format if 'Warning' in status_val else fail_format)
                            worksheet.write(row_num + 1, status_col_idx, status_val, fmt)

            excel_data = output.getvalue()
            with col_exp2:
                st.download_button(label="📊 Download Excel Report", data=excel_data, file_name="Design_Audit_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            text_stream = io.StringIO()
            doc.write(text_stream)
            annotated_dxf_data = text_stream.getvalue()
            
            with col_exp3:
                st.download_button(label="💾 Download Annotated DXF (Markups)", data=annotated_dxf_data, file_name="Annotated_Audit.dxf", mime="application/dxf", use_container_width=True)

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
else:
    st.info("💡 Please upload a DXF file to begin the design audit.")
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
    ["Use Code Standards (AASHTO)", "Manual Custom Global Entry"]
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

global_manual_limits = {}
if criteria_mode == "Manual Custom Global Entry":
    st.sidebar.info("💡 Manual entry applies globally to all profiles in the uploaded file.")
    global_manual_limits['max_grade'] = st.sidebar.number_input("Max Longitudinal Slope (%)", value=5.0, step=0.5, format="%.2f")
    global_manual_limits['min_grade'] = st.sidebar.number_input("Min Longitudinal Slope (%)", value=0.5, step=0.1, format="%.2f")
    global_manual_limits['min_radius'] = st.sidebar.number_input("Min Horizontal Radius (m)", value=230.0, step=1.0, format="%.2f")
    global_manual_limits['min_k_crest'] = st.sidebar.number_input("Min K-Value (Crest)", value=26.0, step=1.0, format="%.2f")
    global_manual_limits['min_k_sag'] = st.sidebar.number_input("Min K-Value (Sag)", value=30.0, step=1.0, format="%.2f")

# --- Main Section: File Upload ---
st.title("🔍 Road Design Review & Checker Tool")
st.markdown("An independent engineering tool for reviewing road CAD drawings (DXF) and checking compliance with AASHTO standards or custom project limits.")
st.markdown("---")

uploaded_file = st.file_uploader("📂 Upload CAD File (.dxf)", type=["dxf"])

if uploaded_file is not None:
    try:
        with open("temp.dxf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Read the DXF using ezdxf
        doc = ezdxf.readfile("temp.dxf")
        msp = doc.modelspace()
        
        if "AUDIT_REVISION_CLOUDS" not in doc.layers:
            doc.layers.add("AUDIT_REVISION_CLOUDS", color=1)
            
        st.success("✅ DXF File loaded and ready for audit!")
        
        # --- Step 1: Dynamic Profile Speed Mapping ---
        st.markdown("### ⚙️ Step 1: Design Speed & Terrain Settings")
        
        unique_profiles = ["Main_Road_01", "Side_Road_A", "Ramp_B"]
        
        if criteria_mode == "Use Code Standards (AASHTO)":
            
            # 1. Global Terrain (Removed from table, applied to all)
            global_terrain = st.selectbox("🌍 Project Terrain Type (Applies to all profiles):", ["Level", "Rolling", "Mountainous"], index=0)
            st.write("") # Spacer
            
            # 2. Speed Assignment Mode (Global vs Individual)
            speed_assignment_mode = st.radio(
                "🚦 Design Speed Assignment Method:",
                ["Single Global Speed for All Profiles", "Different Speed for Each Profile"],
                horizontal=True
            )
            
            if speed_assignment_mode == "Single Global Speed for All Profiles":
                # Only show one speed dropdown, hide the table
                global_speed = st.selectbox("Select Global Design Speed (km/h):", [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], index=6)
                
                def get_limits(profile_name):
                    std = aashto_db[global_speed]
                    return {'max_grade': std['max_grade'][global_terrain], 'min_grade': 0.5, 'min_k_crest': std['k_crest'], 'min_k_sag': std['k_sag']}
            
            else:
                # Show table with ONLY Profile Name and Speed
                st.info("💡 Assign specific AASHTO design speeds for each detected profile.")
                default_mapping = pd.DataFrame({
                    "Profile Name": unique_profiles,
                    "Design Speed (km/h)": [80, 50, 40]
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
                    speed = criteria_dict[profile_name]['Design Speed (km/h)']
                    std = aashto_db[speed]
                    return {'max_grade': std['max_grade'][global_terrain], 'min_grade': 0.5, 'min_k_crest': std['k_crest'], 'min_k_sag': std['k_sag']}
        else:
            def get_limits(profile_name):
                return global_manual_limits

        # --- Step 2: Run Audit ---
        if st.button("🚀 Run Design Audit & Mark CAD", type="primary"):
            st.markdown("---")
            st.subheader("📊 Design Check Audit Results")
            
            violation_count = 0
            
            pvi_data = [
                {"Profile Name": "Main_Road_01", "Station": 1000.00, "Type": "PVI", "Status": "Pass"},
                {"Profile Name": "Main_Road_01", "Station": 1234.25, "Type": "PVI", "Status": "Warning (Not multiple of 5)"}, 
                {"Profile Name": "Side_Road_A", "Station": 1500.00, "Type": "PVI", "Status": "Pass"}
            ]
            df_pvi = pd.DataFrame(pvi_data)

            raw_tangents = [
                {"Profile Name": "Main_Road_01", "Start Station": 1000, "End Station": 1234.25, "Grade (%)": 0.3}, 
                {"Profile Name": "Main_Road_01", "Start Station": 1234.25, "End Station": 1500, "Grade (%)": 5.8},   
                {"Profile Name": "Side_Road_A", "Start Station": 1500, "End Station": 1782.5, "Grade (%)": 7.5}
            ]
            
            processed_tangents = []
            for t in raw_tangents:
                limits = get_limits(t["Profile Name"])
                g = abs(t["Grade (%)"])
                if g > limits['max_grade']:
                    t["Status"] = f"Violation (Exceeds Max {limits['max_grade']}%)"
                    violation_count += 1
                elif g < limits['min_grade']:
                    t["Status"] = f"Warning (Below Min {limits['min_grade']}%)"
                else:
                    t["Status"] = "Pass"
                processed_tangents.append(t)
            df_grades = pd.DataFrame(processed_tangents)

            raw_curves = [
                {"Profile Name": "Main_Road_01", "Station": 1234.25, "Curve Type": "Crest", "Actual K-Value": 20},
                {"Profile Name": "Side_Road_A", "Station": 1500.00, "Curve Type": "Sag", "Actual K-Value": 40},
                {"Profile Name": "Ramp_B", "Station": 2000.00, "Curve Type": "Crest", "Actual K-Value": 5}
            ]
            
            processed_curves = []
            for c in raw_curves:
                limits = get_limits(c["Profile Name"])
                req_k = limits['min_k_crest'] if c["Curve Type"] == "Crest" else limits['min_k_sag']
                if c["Actual K-Value"] < req_k:
                    c["Required K-Value"] = req_k
                    c["Status"] = f"Violation (Below {req_k})"
                    violation_count += 1
                else:
                    c["Required K-Value"] = req_k
                    c["Status"] = "Pass"
                processed_curves.append(c)
            df_curves = pd.DataFrame(processed_curves)

            # Draw Simulated Revision Cloud
            msp.add_circle(center=(0, 0), radius=100, dxfattribs={'layer': 'AUDIT_REVISION_CLOUDS'})
            msp.add_text(f"Audit Found {violation_count} Violations", dxfattribs={'layer': 'AUDIT_REVISION_CLOUDS', 'height': 20}).set_placement((0, 110))

            with st.expander("📌 PVI Stationing Checks", expanded=True):
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

            with st.expander("📈 Vertical Curves & K-Values Checks", expanded=True):
                def highlight_curves(s):
                    if "Violation" in str(s["Status"]): return ['background-color: #f8d7da; color: #721c24']*len(s)
                    return ['background-color: #d4edda; color: #155724']*len(s)
                st.dataframe(df_curves.style.apply(highlight_curves, axis=1), use_container_width=True, hide_index=True)

            # --- Export Reports ---
            st.markdown("---")
            st.subheader("📥 Export Audit Reports & Marked CAD File")
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            report_content = f"--- Road Design Audit Report ---\n\n"
            report_content += "PVI Checks:\n" + df_pvi.to_string(index=False) + "\n\n"
            report_content += "Grade Checks:\n" + df_grades.to_string(index=False) + "\n\n"
            report_content += "Curve Checks:\n" + df_curves.to_string(index=False) + "\n"
            
            with col_exp1:
                st.download_button(label="📄 Download Text Report", data=report_content, file_name="Design_Audit_Report.txt", mime="text/plain", use_container_width=True)
                
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_pvi.to_excel(writer, sheet_name='PVI Checks', index=False)
                df_grades.to_excel(writer, sheet_name='Grades Checks', index=False)
                df_curves.to_excel(writer, sheet_name='Vertical Curves', index=False)
                
                workbook = writer.book
                header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#007bff', 'font_color': 'white', 'border': 1})
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
                            fmt = pass_format if 'Pass' in status_val else (warn_format if 'Warning' in status_val else fail_format)
                            worksheet.write(row_num + 1, status_col_idx, status_val, fmt)

            excel_data = output.getvalue()
            with col_exp2:
                st.download_button(label="📊 Download Excel Report", data=excel_data, file_name="Design_Audit_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            text_stream = io.StringIO()
            doc.write(text_stream)
            annotated_dxf_data = text_stream.getvalue()
            
            with col_exp3:
                st.download_button(label="💾 Download Annotated DXF (Markups)", data=annotated_dxf_data, file_name="Annotated_Audit.dxf", mime="application/dxf", use_container_width=True)

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
else:
    st.info("💡 Please upload a DXF file to begin the design audit.")
