import streamlit as st

# إعداد إعدادات الصفحة
st.set_page_config(page_title="K-Value Calculator", layout="centered")

# قاعدة البيانات المستخرجة من الجداول المرفقة (AASHTO و Abu Dhabi)
k_values_data = {
    "AASHTO": {
        "Crest": {
            20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 
            80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124
        },
        "Sag": {
            20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 
            80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73
        }
    },
    "Abu Dhabi": {
        "Crest": {
            20: 1, 30: 2, 40: 4, 50: 7, 60: 11, 70: 17, 
            80: 26, 90: 39, 100: 52, 110: 74, 120: 95, 130: 124, 140: 161
        },
        "Sag": {
            20: 3, 30: 6, 40: 9, 50: 13, 60: 18, 70: 23, 
            80: 30, 90: 38, 100: 45, 110: 55, 120: 63, 130: 73, 140: 84
        }
    }
}

# عنوان الأداة وتنسيقها
st.title("🛣️ Live Tool: K-Value Requirement Calculator")
st.markdown("---")

# تقسيم الواجهة إلى 3 أعمدة للقوائم المنسدلة
col1, col2, col3 = st.columns(3)

with col1:
    # القائمة الأولى: اختيار كود التصميم
    selected_code = st.selectbox("Design Code (كود التصميم)", options=["AASHTO", "Abu Dhabi"])

with col2:
    # القائمة الثانية: اختيار نوع المنحنى
    curve_type = st.selectbox("Curve Type (نوع المنحنى)", options=["Crest", "Sag"])

with col3:
    # القائمة الثالثة: السرعة التصميمية (يتم تحديثها تلقائياً بناءً على الكود المختار)
    available_speeds = list(k_values_data[selected_code][curve_type].keys())
    # جعل السرعة الافتراضية 120 إذا كانت متاحة
    default_index = available_speeds.index(120) if 120 in available_speeds else 0
    speed = st.selectbox("Design Speed (V) [km/h]", options=available_speeds, index=default_index)

st.markdown("<br>", unsafe_allow_html=True)

# حاوية لعرض النتيجة
result_container = st.container()

# زر الحساب
if st.button("Calculate Required K", type="primary", use_container_width=True):
    # استخراج القيمة من قاعدة البيانات
    required_k = k_values_data[selected_code][curve_type][speed]
    
    # عرض النتيجة بشكل بارز وجميل
    with result_container:
        st.info(f"### Required Minimum K: **{required_k}**")
        st.caption(f"*Based on {selected_code} Metric approximations for {curve_type} curves.*")