"""
Settings - User Configuration

Configure trading preferences and risk profile.
"""
import streamlit as st
import yaml
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

# Header
st.title("⚙️ Settings")
st.markdown("Configure your trading preferences")

# Load config
config_file = project_root / 'config.yaml'

if not config_file.exists():
    st.error("❌ config.yaml not found!")
    st.stop()

with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# Create tabs
tab1, tab2, tab3 = st.tabs(["👤 User Profile", "🎯 Risk Filters", "ℹ️ Info"])

with tab1:
    st.subheader("Your Trading Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Capital
        capital = st.number_input(
            "💰 Available Capital (GP)",
            min_value=1000,
            max_value=1000000000,
            value=config.get('capital', 10000000),
            step=100000,
            help="Total GP you have available for flipping"
        )
        
        # GE Slots
        ge_slots = st.number_input(
            "📦 GE Slots Available",
            min_value=1,
            max_value=8,
            value=config.get('ge_slots', 8),
            help="Number of Grand Exchange slots you can use"
        )
    
    with col2:
        # Risk Profile
        risk_profile = st.selectbox(
            "🎲 Risk Profile",
            options=['conservative', 'moderate', 'aggressive'],
            index=['conservative', 'moderate', 'aggressive'].index(config.get('risk_profile', 'moderate')),
            help="Determines which filters are applied"
        )
        
        # GE Tax
        ge_tax = st.number_input(
            "💸 GE Tax Rate",
            min_value=0.0,
            max_value=0.1,
            value=config.get('ge_tax_rate', 0.01),
            step=0.001,
            format="%.3f",
            help="Grand Exchange tax (default: 1%)"
        )
    
    # Preview changes
    st.divider()
    st.subheader("📊 Profile Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Capital", f"{capital:,} GP")
    col2.metric("GE Slots", ge_slots)
    col3.metric("Risk", risk_profile.title())
    col4.metric("Tax Rate", f"{ge_tax:.1%}")
    
    # Save button
    if st.button("💾 Save Settings", type="primary"):
        try:
            # Update config
            config['capital'] = int(capital)
            config['ge_slots'] = int(ge_slots)
            config['risk_profile'] = risk_profile
            config['ge_tax_rate'] = float(ge_tax)
            
            # Save to file
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            st.success("✅ Settings saved successfully!")
            st.info("💡 Run the pipeline to apply new settings: `python scripts/run_pipeline.py --mode full`")
            
        except Exception as e:
            st.error(f"❌ Error saving settings: {e}")

with tab2:
    st.subheader("Risk Profile Filters")
    
    st.info(f"Currently using: **{config.get('risk_profile', 'moderate').title()}** profile")
    
    # Show current filters
    profiles = config.get('risk_profiles', {})
    current_profile = profiles.get(config.get('risk_profile', 'moderate'), {})
    
    if current_profile:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### Level 1: Basic Survival")
            l1 = current_profile.get('level1', {})
            st.write(f"**Min Volume:** {l1.get('min_total_volume', 'N/A'):,}")
            st.write(f"**Min Records:** {l1.get('min_records', 'N/A')}")
            st.write(f"**Max Days Inactive:** {l1.get('max_days_since_activity', 'N/A')}")
        
        with col2:
            st.markdown("### Level 2: Quality Filter")
            l2 = current_profile.get('level2', {})
            st.write(f"**Spread:** {l2.get('min_spread_pct', 'N/A')}% - {l2.get('max_spread_pct', 'N/A')}%")
            st.write(f"**Volume Percentile:** Top {100 - l2.get('min_volume_percentile', 0)}%")
            st.write(f"**Min Trade Freq:** {l2.get('min_trading_frequency', 'N/A')}")
            st.write(f"**Price Range:** {l2.get('min_price', 'N/A'):,} - {l2.get('max_price', 'N/A'):,} GP")
        
        with col3:
            st.markdown("### Level 3: Top Performers")
            l3 = current_profile.get('level3', {})
            st.write(f"**Min Win Rate:** {l3.get('min_win_rate', 'N/A')}%")
            st.write(f"**Min ROI:** {l3.get('min_avg_roi', 'N/A')}%")
            st.write(f"**Min Sharpe:** {l3.get('min_sharpe_ratio', 'N/A')}")
    
    st.divider()
    
    # Compare profiles
    st.subheader("📊 Profile Comparison")
    
    comparison_data = []
    for profile_name, profile_data in profiles.items():
        l2 = profile_data.get('level2', {})
        l3 = profile_data.get('level3', {})
        
        comparison_data.append({
            'Profile': profile_name.title(),
            'Min Spread': f"{l2.get('min_spread_pct', 0)}%",
            'Max Spread': f"{l2.get('max_spread_pct', 0)}%",
            'Min Win Rate': f"{l3.get('min_win_rate', 0)}%",
            'Min ROI': f"{l3.get('min_avg_roi', 0)}%",
            'Volume Req': f"Top {100 - l2.get('min_volume_percentile', 0)}%",
            'Description': '🛡️ Safe' if profile_name == 'conservative' else '⚖️ Balanced' if profile_name == 'moderate' else '🚀 Risky'
        })
    
    import pandas as pd
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    st.markdown("""
    **Profile Recommendations:**
    - 🛡️ **Conservative**: High liquidity, low volatility, safe profits
    - ⚖️ **Moderate**: Good balance of risk and reward (recommended)
    - 🚀 **Aggressive**: Higher profits, more volatility, needs more capital
    """)

with tab3:
    st.subheader("ℹ️ Configuration Info")
    
    st.markdown("""
    ### How Settings Work
    
    **User Profile** settings affect:
    - Portfolio optimization (how capital is distributed)
    - Item recommendations (based on available slots)
    - ROI calculations (accounting for GE tax)
    
    **Risk Filters** determine:
    - Which items pass the analysis pipeline
    - Level 1, 2, 3 filtering thresholds
    - Final candidate selection (max 50 items)
    
    ### Important Notes
    
    ⚠️ **Changing settings requires re-running the analysis:**
    ```bash
    python scripts/run_pipeline.py --mode full
    ```
    
    💡 **To completely re-analyze with new filters:**
    ```bash
    python scripts/run_pipeline.py --mode full --reanalyze
    ```
    
    📝 **Settings are stored in:** `config.yaml`
    
    ### Default Values
    - **Capital:** 10,000,000 GP
    - **GE Slots:** 8
    - **Risk Profile:** Moderate
    - **GE Tax:** 1%
    """)
    
    # Show raw config (expandable)
    with st.expander("🔧 View Raw Config"):
        st.code(yaml.dump(config, default_flow_style=False), language='yaml')

# Footer
st.divider()
st.info("💡 **Tip:** Start with 'Moderate' profile. Switch to 'Conservative' if results are too risky, or 'Aggressive' if you want more opportunities.")
