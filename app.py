"""
OSRS Trading Dashboard - Main App

Multi-page Streamlit application for OSRS Grand Exchange trading analysis.
"""
import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="OSRS Trading Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Simple authentication (optional - comment out if not needed)
def check_password():
    """Returns True if user has correct password"""
    
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "osrs2026"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    # Skip auth if no password set
    if "password" not in st.secrets:
        st.session_state["password_correct"] = True
        return True
    
    if "password_correct" not in st.session_state:
        st.text_input(
            "🔐 Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔐 Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("😕 Incorrect password")
        return False
    else:
        return True


# Main app
if check_password():
    # Header
    st.markdown('<p class="main-header">🎮 OSRS Trading Dashboard</p>', unsafe_allow_html=True)
    
    # Welcome message
    st.markdown("""
    ### Welcome to the OSRS Grand Exchange Trading Analysis Tool
    
    This dashboard helps you identify profitable flipping opportunities in Old School RuneScape.
    
    **Navigate using the sidebar:**
    - 📊 **Dashboard**: View top trading candidates
    - 🔍 **Item Analysis**: Deep dive into specific items
    - ⚙️ **Settings**: Configure your trading preferences
    - 🚀 **Run Pipeline**: Execute data updates and analysis
    """)
    
    # Quick stats
    st.divider()
    st.subheader("📈 Quick Stats")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Try to load candidates and show stats
    try:
        import pandas as pd
        from src.utils.config import config
        
        processed_dir = Path(config.get('storage', 'processed_dir'))
        
        # Find latest candidates file
        candidates_file = None
        for risk_profile in ['moderate', 'conservative', 'aggressive']:
            file_path = processed_dir / f'final_candidates_{risk_profile}.parquet'
            if file_path.exists():
                candidates_file = file_path
                break
        
        if candidates_file:
            df = pd.read_parquet(candidates_file)
            
            col1.metric("📦 Total Candidates", len(df))
            col2.metric("💰 Avg ROI", f"{df['avg_roi'].mean():.1f}%")
            col3.metric("🎯 Avg Win Rate", f"{df['win_rate'].mean():.0f}%")
            col4.metric("📊 Avg Spread", f"{df['avg_spread_pct'].mean():.1f}%")
            
            # Show top 3
            st.divider()
            st.subheader("🏆 Top 3 Candidates")
            
            top_3 = df.nlargest(3, 'final_score')[['name', 'avg_high_price', 'avg_spread_pct', 'win_rate', 'avg_roi']]
            
            for i, (idx, row) in enumerate(top_3.iterrows(), 1):
                with st.container():
                    cols = st.columns([1, 3, 2, 2, 2])
                    cols[0].markdown(f"**#{i}**")
                    cols[1].markdown(f"**{row['name']}**")
                    cols[2].metric("Price", f"{row['avg_high_price']:.0f} GP")
                    cols[3].metric("Spread", f"{row['avg_spread_pct']:.1f}%")
                    cols[4].metric("ROI", f"{row['avg_roi']:.1f}%")
        else:
            st.info("📊 No candidates data found. Run the pipeline first!")
            
    except Exception as e:
        st.warning(f"⚠️ Could not load stats: {e}")
        st.info("💡 Run the pipeline to generate candidate data")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Made with ❤️ for OSRS traders | Data from OSRS Wiki API</p>
    </div>
    """, unsafe_allow_html=True)

else:
    # Show login screen
    st.info("👋 Please enter the password to access the dashboard")
