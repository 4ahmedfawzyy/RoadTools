import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Road Engineering Platform",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Hide Sidebar in the Main Page */
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
        
        .main-title {
            text-align: center;
            font-size: 55px;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -1px;
            color: #ffffff;
        }
        
        .sub-title {
            text-align: center;
            color: #a0a0a0;
            font-size: 22px;
            font-weight: 400;
            margin-bottom: 60px;
        }

        /* Force Big Font Size for Buttons */
        div.stButton > button {
            height: 140px;
            border-radius: 20px;
            border: 2px solid #007bff;
            background-color: transparent;
            transition: all 0.3s ease-in-out;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        div.stButton > button * {
            font-size: 32px !important;
            font-weight: 600 !important;
            color: #007bff !important;
        }
        
        div.stButton > button:hover {
            background-color: #007bff;
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 123, 255, 0.4);
        }
        
        div.stButton > button:hover * {
            color: white !important;
        }
        
        .big-emoji {
            text-align: center;
            font-size: 90px;
            margin-bottom: -15px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🛣️ Road Engineering Platform</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Please select a tool to get started</div>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

with col2:
    st.markdown("<div class='big-emoji'>🔍</div>", unsafe_allow_html=True)
    if st.button("Design Checks", use_container_width=True):
        st.switch_page("pages/1_Design_Checks.py")

with col3:
    st.markdown("<div class='big-emoji'>📄</div>", unsafe_allow_html=True)
    if st.button("BODR", use_container_width=True):
        st.switch_page("pages/2_BODR.py")
