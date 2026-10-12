st.markdown("""
    <style>
    /* أنيميشن كلمة Welcome */
    .welcome-banner { text-align: center; animation: fadeInScale 1.5s ease-in-out; margin-bottom: 20px; }
    .welcome-title { font-size: 3.5rem; font-weight: 900; background: -webkit-linear-gradient(45deg, #007bff, #00d2ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; letter-spacing: 2px; }
    .welcome-subtitle { font-size: 1.2rem; opacity: 0.8; letter-spacing: 1px; }
    @keyframes fadeInScale { 0% { opacity: 0; transform: translateY(-30px) scale(0.9); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
    
    /* تنسيق الكروت الديناميكي (يدعم Dark/Light Mode) */
    .stCard { 
        background-color: var(--secondary-background-color); 
        color: var(--text-color);
        padding: 20px; 
        border-radius: 10px; 
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); 
        margin-bottom: 20px; 
        border-left: 5px solid #007bff; 
        transition: transform 0.3s; 
    }
    .stCard h4, .stCard p {
        color: var(--text-color) !important;
    }
    .stCard:hover { transform: translateY(-5px); box-shadow: 0 6px 12px 0 rgba(0,0,0,0.2); }
    
    .metric-card { 
        background-color: var(--secondary-background-color); 
        color: var(--text-color);
        padding: 15px; 
        border-radius: 8px; 
        box-shadow: 0 2px 4px 0 rgba(0,0,0,0.1); 
        text-align: center; 
        border: 1px solid var(--faded-text-color); 
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
    .metric-label { font-size: 14px; opacity: 0.8; }
    
    /* تنسيق اللوجو */
    .sidebar-logo { font-size: 80px; text-align: center; margin-bottom: -20px; }
    </style>
""", unsafe_allow_html=True)
