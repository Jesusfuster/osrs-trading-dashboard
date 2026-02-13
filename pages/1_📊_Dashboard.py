"""
Dashboard - Trading Candidates Overview

Interactive table with filtering and sorting of top trading candidates.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import config

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Header
st.title("📊 Trading Candidates Dashboard")
st.markdown("Explore and filter top flipping opportunities")

# Load data
@st.cache_data
def load_candidates():
    """Load final candidates data"""
    processed_dir = Path(config.get('storage', 'processed_dir'))
    
    # Try to find candidates file
    for risk_profile in ['moderate', 'conservative', 'aggressive']:
        file_path = processed_dir / f'final_candidates_{risk_profile}.parquet'
        if file_path.exists():
            df = pd.read_parquet(file_path)
            return df, risk_profile
    
    return None, None

df, risk_profile = load_candidates()

if df is None:
    st.error("❌ No candidates data found!")
    st.info("💡 Run the pipeline first: `python scripts/run_pipeline.py --mode full --reanalyze`")
    st.stop()

# Success message
st.success(f"✅ Loaded {len(df)} candidates (Risk Profile: **{risk_profile.title()}**)")

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Price filter
price_min, price_max = st.sidebar.slider(
    "Price Range (GP)",
    min_value=int(df['avg_high_price'].min()),
    max_value=int(df['avg_high_price'].max()),
    value=(int(df['avg_high_price'].min()), int(df['avg_high_price'].max())),
    step=100
)

# Spread filter
spread_min, spread_max = st.sidebar.slider(
    "Spread %",
    min_value=float(df['avg_spread_pct'].min()),
    max_value=float(df['avg_spread_pct'].max()),
    value=(float(df['avg_spread_pct'].min()), float(df['avg_spread_pct'].max())),
    step=0.5
)

# Win rate filter
win_rate_min = st.sidebar.slider(
    "Min Win Rate %",
    min_value=float(df['win_rate'].min()),
    max_value=100.0,
    value=float(df['win_rate'].min()),
    step=1.0
)

# ROI filter
roi_min = st.sidebar.slider(
    "Min ROI %",
    min_value=float(df['avg_roi'].min()),
    max_value=float(df['avg_roi'].max()),
    value=float(df['avg_roi'].min()),
    step=0.5
)

# Members filter
members_filter = st.sidebar.radio(
    "Item Type",
    options=["All", "Members Only", "F2P Only"],
    index=0
)

# Apply filters
df_filtered = df[
    (df['avg_high_price'] >= price_min) &
    (df['avg_high_price'] <= price_max) &
    (df['avg_spread_pct'] >= spread_min) &
    (df['avg_spread_pct'] <= spread_max) &
    (df['win_rate'] >= win_rate_min) &
    (df['avg_roi'] >= roi_min)
].copy()

if members_filter == "Members Only":
    df_filtered = df_filtered[df_filtered['members'] == True]
elif members_filter == "F2P Only":
    df_filtered = df_filtered[df_filtered['members'] == False]

st.sidebar.markdown(f"**{len(df_filtered)}** items match filters")

# Main content
if len(df_filtered) == 0:
    st.warning("⚠️ No items match your filters. Try relaxing the criteria.")
    st.stop()

# Summary metrics
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("📦 Items", len(df_filtered))
col2.metric("💰 Avg Price", f"{df_filtered['avg_high_price'].mean():.0f} GP")
col3.metric("📊 Avg Spread", f"{df_filtered['avg_spread_pct'].mean():.1f}%")
col4.metric("🎯 Avg Win Rate", f"{df_filtered['win_rate'].mean():.0f}%")
col5.metric("💵 Avg ROI", f"{df_filtered['avg_roi'].mean():.1f}%")

st.divider()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📋 Table View", "📊 Charts", "🔝 Top 10"])

with tab1:
    st.subheader("Candidates Table")
    
    # Select columns to display
    display_columns = [
        'name', 'avg_high_price', 'avg_spread_pct', 'limit',
        'win_rate', 'avg_roi', 'sharpe_ratio', 'trading_frequency',
        'avg_daily_volume', 'final_score'
    ]
    
    # Format the dataframe
    df_display = df_filtered[display_columns].copy()
    df_display.columns = [
        'Item', 'Price (GP)', 'Spread %', 'Buy Limit',
        'Win Rate %', 'ROI %', 'Sharpe', 'Trade Freq',
        'Daily Vol', 'Score'
    ]
    
    # Sort by score
    df_display = df_display.sort_values('Score', ascending=False)
    
    # Style the dataframe
    st.dataframe(
        df_display.style.format({
            'Price (GP)': '{:.0f}',
            'Spread %': '{:.2f}',
            'Win Rate %': '{:.1f}',
            'ROI %': '{:.2f}',
            'Sharpe': '{:.2f}',
            'Trade Freq': '{:.2f}',
            'Daily Vol': '{:.0f}',
            'Score': '{:.3f}'
        }).background_gradient(subset=['Score'], cmap='RdYlGn'),
        use_container_width=True,
        height=600
    )
    
    # Download button
    csv = df_display.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f"osrs_candidates_{risk_profile}.csv",
        mime="text/csv"
    )

with tab2:
    st.subheader("Visual Analysis")
    
    # Chart 1: Scatter plot - ROI vs Win Rate
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.scatter(
            df_filtered,
            x='win_rate',
            y='avg_roi',
            size='final_score',
            color='avg_spread_pct',
            hover_name='name',
            hover_data={
                'avg_high_price': ':,.0f',
                'win_rate': ':.1f',
                'avg_roi': ':.2f',
                'final_score': ':.3f'
            },
            labels={
                'win_rate': 'Win Rate (%)',
                'avg_roi': 'Average ROI (%)',
                'avg_spread_pct': 'Spread %'
            },
            title="ROI vs Win Rate",
            color_continuous_scale='RdYlGn'
        )
        fig1.update_layout(height=400)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Chart 2: Spread distribution
        fig2 = px.histogram(
            df_filtered,
            x='avg_spread_pct',
            nbins=20,
            title="Spread Distribution",
            labels={'avg_spread_pct': 'Spread (%)'},
            color_discrete_sequence=['#1f77b4']
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Chart 3: Price vs Volume
    col3, col4 = st.columns(2)
    
    with col3:
        fig3 = px.scatter(
            df_filtered,
            x='avg_high_price',
            y='avg_daily_volume',
            color='final_score',
            hover_name='name',
            log_y=True,
            title="Price vs Daily Volume",
            labels={
                'avg_high_price': 'Price (GP)',
                'avg_daily_volume': 'Daily Volume (log scale)'
            },
            color_continuous_scale='Viridis'
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # Chart 4: Top 15 by score
        top_15 = df_filtered.nlargest(15, 'final_score')
        fig4 = px.bar(
            top_15,
            y='name',
            x='final_score',
            orientation='h',
            title="Top 15 by Score",
            labels={'final_score': 'Score', 'name': ''},
            color='final_score',
            color_continuous_scale='RdYlGn'
        )
        fig4.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

with tab3:
    st.subheader("🔝 Top 10 Candidates")
    
    top_10 = df_filtered.nlargest(10, 'final_score')
    
    for i, (idx, row) in enumerate(top_10.iterrows(), 1):
        with st.expander(f"#{i} - {row['name']} (Score: {row['final_score']:.3f})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Price", f"{row['avg_high_price']:.0f} GP")
                st.metric("📊 Spread", f"{row['avg_spread_pct']:.2f}%")
                st.metric("🎯 Win Rate", f"{row['win_rate']:.1f}%")
            
            with col2:
                st.metric("💵 ROI", f"{row['avg_roi']:.2f}%")
                st.metric("📈 Sharpe", f"{row['sharpe_ratio']:.2f}")
                st.metric("🔄 Trade Freq", f"{row['trading_frequency']:.2f}")
            
            with col3:
                st.metric("📦 Buy Limit", f"{row['limit']:.0f}")
                st.metric("📊 Daily Vol", f"{row['avg_daily_volume']:.0f}")
                st.metric("🏆 Score", f"{row['final_score']:.3f}")
            
            # Quick calc
            st.divider()
            st.markdown("**💡 Quick Calculator**")
            
            quantity = st.number_input(
                f"Quantity to buy",
                min_value=1,
                max_value=int(row['limit']),
                value=min(100, int(row['limit'])),
                key=f"qty_{idx}"
            )
            
            buy_price = row['avg_low_price']
            sell_price = row['avg_high_price']
            
            gross_profit = (sell_price - buy_price) * quantity
            tax = sell_price * quantity * 0.01
            net_profit = gross_profit - tax
            
            st.info(f"""
            **Investment:** {buy_price * quantity:,.0f} GP  
            **Expected Return:** {sell_price * quantity:,.0f} GP  
            **Net Profit:** {net_profit:,.0f} GP ({(net_profit / (buy_price * quantity) * 100):.2f}% ROI)
            """)

# Footer
st.divider()
st.markdown("💡 **Tip:** Use filters in the sidebar to narrow down candidates based on your capital and risk tolerance")
