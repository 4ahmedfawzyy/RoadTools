import streamlit as st

# 1. إعداد الصفحة وإخفاء الشريط الجانبي مبدئياً
st.set_page_config(
    page_title="Road Engineering Platform",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. كود CSS لإخفاء زر القائمة الجانبية وتكبير الأزرار في المنتصف
st.markdown("""
    <style>
        /* إخفاء القائمة الجانبية في الصفحة الرئيسية */
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
        
        /* تصميم الأزرار لتكون كبيرة واحترافية */
        div.stButton > button {
            height: 120px;
            font-size: 26px !important;
            font-weight: bold;
            border-radius: 15px;
            border: 2px solid #007bff;
            background-color: white;
            color: #007bff;
            transition: all 0.3s ease-in-out;
        }
        div.stButton > button:hover {
            background-color: #007bff;
            color: white;
            transform: scale(1.05);
        }
    </style>
""", unsafe_allow_html=True)

# 3. عنوان الصفحة الترحيبية
st.markdown("<h1 style='text-align: center; font-size: 50px;'>🛣️ Road Engineering Platform</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: gray; margin-bottom: 60px;'>يرجى اختيار الأداة المطلوبة للبدء</h3>", unsafe_allow_html=True)

# 4. تقسيم الشاشة لعمل الأيقونات في المنتصف
col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

with col2:
    # أيقونة كبيرة وزر لأداة الـ Design Checks
    st.markdown("<h1 style='text-align: center; font-size: 90px; margin-bottom: 0px;'>🔍</h1>", unsafe_allow_html=True)
    if st.button("Design Checks", use_container_width=True):
        st.switch_page("pages/1_Design_Checks.py")

with col3:
    # أيقونة كبيرة وزر لأداة الـ BODR
    st.markdown("<h1 style='text-align: center; font-size: 90px; margin-bottom: 0px;'>📄</h1>", unsafe_allow_html=True)
    if st.button("BODR & K-Value", use_container_width=True):
        st.switch_page("pages/2_BODR.py")
