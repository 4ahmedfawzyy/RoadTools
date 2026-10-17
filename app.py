import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Road Engineering Platform",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for better typography, hiding sidebar, and styling buttons
st.markdown("""
    <style>
        /* Import a modern professional font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

        /* Apply the font to the whole page */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Hide Sidebar in the Main Page */
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
        
        /* Main Title Styling */
        .main-title {
            text-align: center;
            font-size: 55px;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -1px;
            color: #ffffff;
        }
        
        /* Subtitle Styling */
        .sub-title {
            text-align: center;
            color: #a0a0a0;
            font-size: 22px;
            font-weight: 400;
            margin-bottom: 60px;
            letter-spacing: 0.5px;
        }

        /* Button Styling */
        div.stButton > button {
            height: 140px;
            font-size: 28px !important;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
            border-radius: 20px;
            border: 2px solid #007bff;
            background-color: transparent;
            color: #007bff;
            transition: all 0.3s ease-in-out;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Button Hover Effect */
        div.stButton > button:hover {
            background-color: #007bff;
            color: white;
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 123, 255, 0.4);
            border-color: #007bff;
        }
        
        /* Big Emoji Styling */
        .big-emoji {
            text-align: center;
            font-size: 90px;
            margin-bottom: -15px;
        }
    </style>
""", unsafe_allow_html=True)

# Title and Subtitle
st.markdown("<div class='main-title'>🛣️ Road Engineering Platform</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Please select a tool to get started</div>", unsafe_allow_html=True)

# Columns for layout (centering the buttons)
col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

with col2:
    st.markdown("<div class='big-emoji'>🔍</div>", unsafe_allow_html=True)
    if st.button("Design Checks", use_container_width=True):
        st.switch_page("pages/1_Design_Checks.py")

with col3:
    st.markdown("<div class='big-emoji'>📄</div>", unsafe_allow_html=True)
    if st.button("BODR", use_container_width=True):
        st.switch_page("pages/2_BODR.py")
