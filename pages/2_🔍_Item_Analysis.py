"""
Item Analysis - Deep Dive

Detailed analysis of individual items with historical charts and metrics.
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

st.set_page_config(page_title="Item Analysis", page_icon="🔍", layout="wide")

# Header
st.title("🔍 Item Analysis")
st.markdown("Deep dive into individual item performance")

# Load candidates
@st.cache_data
def load_candidates():
    """Load final candidates data"""
    processed_dir = Path(config.get('storage', 'processed_dir'))
    
    for risk_profile in ['moderate', 'conservative', 'aggressive']:
        file_path = processed_dir / f'final_candidates_{risk_profile}.parquet'
        if file_path.exists():
            return pd.read_parquet(file_path)
    
    return None

df = load_candidates()

if df is None:
    st.error("❌ No candidates data found!")
    st.info("💡 Run the pipeline first")
    st.stop()

# Item selector
item_names = sorted(df['name'].tolist())
selected_item = st.selectbox(
    "Select an item to analyze",
    options=item_names,
    index=0
)

# Get item data
item_row = df[df['name'] == selected_item].iloc[0]
item_id = item_row['item_id']

# Display item info
col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Avg Price", f"{item_row['avg_high_price']:.0f} GP")
col2.metric("📊 Spread", f"{item_row['avg_spread_pct']:.2f}%", 
            help="Average difference between buy and sell price")
col3.metric("🎯 Win Rate", f"{item_row['win_rate']:.1f}%",
            help="Percentage of profitable trades in backtest")
col4.metric("💵 Avg ROI", f"{item_row['avg_roi']:.2f}%",
            help="Average return on investment per trade")

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Price History", "📊 Metrics", "🎮 Simulator", "ℹ️ Info"])

with tab1:
    st.subheader("Historical Prices (6h data)")
    
    # Load timeseries data
    @st.cache_data
    def load_timeseries(item_id):
        """Load 6h timeseries for item"""
        raw_dir = Path(config.get('storage', 'raw_dir'))
        ts_file = raw_dir / 'timeseries_6h' / f'item_{item_id}.parquet'
        
        if ts_file.exists():
            df_ts = pd.read_parquet(ts_file)
            return df_ts.sort_values('datetime')
        return None
    
    df_ts = load_timeseries(item_id)
    
    if df_ts is not None and len(df_ts) > 0:
        # Date range selector
        col1, col2 = st.columns(2)
        
        min_date = df_ts['datetime'].min().date()
        max_date = df_ts['datetime'].max().date()
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=max_date - pd.Timedelta(days=30),
                min_value=min_date,
                max_value=max_date
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        
        # Filter by date range
        df_ts_filtered = df_ts[
            (df_ts['datetime'].dt.date >= start_date) &
            (df_ts['datetime'].dt.date <= end_date)
        ]
        
        if len(df_ts_filtered) > 0:
            # Price chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_ts_filtered['datetime'],
                y=df_ts_filtered['avgHighPrice'],
                name='Sell Price',
                line=dict(color='#2ecc71', width=2),
                fill=None
            ))
            
            fig.add_trace(go.Scatter(
                x=df_ts_filtered['datetime'],
                y=df_ts_filtered['avgLowPrice'],
                name='Buy Price',
                line=dict(color='#e74c3c', width=2),
                fill='tonexty',
                fillcolor='rgba(231, 76, 60, 0.1)'
            ))
            
            fig.update_layout(
                title=f"Price History - {selected_item}",
                xaxis_title="Date",
                yaxis_title="Price (GP)",
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Spread over time
            df_ts_filtered['spread_pct'] = (
                (df_ts_filtered['avgHighPrice'] - df_ts_filtered['avgLowPrice']) /
                df_ts_filtered['avgLowPrice'] * 100
            )
            
            fig2 = px.line(
                df_ts_filtered,
                x='datetime',
                y='spread_pct',
                title="Spread % Over Time",
                labels={'spread_pct': 'Spread (%)', 'datetime': 'Date'}
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Volume chart
            df_ts_filtered['total_volume'] = (
                df_ts_filtered['highPriceVolume'] + df_ts_filtered['lowPriceVolume']
            )
            
            fig3 = px.bar(
                df_ts_filtered,
                x='datetime',
                y='total_volume',
                title="Trading Volume Over Time",
                labels={'total_volume': 'Volume', 'datetime': 'Date'}
            )
            fig3.update_layout(height=300)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("No data in selected date range")
    else:
        st.warning("No historical data available for this item")

with tab2:
    st.subheader("Detailed Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Price Metrics")
        st.metric("Average High Price", f"{item_row['avg_high_price']:.2f} GP")
        st.metric("Average Low Price", f"{item_row['avg_low_price']:.2f} GP")
        st.metric("Spread (GP)", f"{item_row['avg_spread_gp']:.2f} GP")
        st.metric("Spread (%)", f"{item_row['avg_spread_pct']:.2f}%")
        
        st.markdown("### 📊 Trading Metrics")
        st.metric("Daily Volume", f"{item_row['avg_daily_volume']:.0f}")
        st.metric("Trading Frequency", f"{item_row['trading_frequency']:.2%}")
        st.metric("Buy Limit", f"{item_row['limit']:.0f} / 4h")
    
    with col2:
        st.markdown("### 🎯 Performance Metrics")
        st.metric("Win Rate", f"{item_row['win_rate']:.2f}%")
        st.metric("Average ROI", f"{item_row['avg_roi']:.2f}%")
        st.metric("Sharpe Ratio", f"{item_row['sharpe_ratio']:.2f}")
        st.metric("Total Trades (Backtest)", f"{item_row['total_trades']:.0f}")
        
        st.markdown("### 🏆 Quality Score")
        st.metric("Final Score", f"{item_row['final_score']:.4f}")
        
        # Score breakdown
        st.markdown("**Score Components:**")
        st.progress(item_row['norm_volume'], text=f"Volume: {item_row['norm_volume']:.2f}")
        st.progress(item_row['norm_win_rate'], text=f"Win Rate: {item_row['norm_win_rate']:.2f}")
        st.progress(item_row['norm_roi'], text=f"ROI: {item_row['norm_roi']:.2f}")

with tab3:
    st.subheader("🎮 Trade Simulator")
    
    st.markdown("Simulate a trade with current average prices")
    
    col1, col2 = st.columns(2)
    
    with col1:
        quantity = st.number_input(
            "Quantity to trade",
            min_value=1,
            max_value=int(item_row['limit']),
            value=min(100, int(item_row['limit'])),
            help=f"Max buy limit: {item_row['limit']:.0f} every 4 hours"
        )
        
        custom_buy = st.checkbox("Use custom buy price")
        if custom_buy:
            buy_price = st.number_input(
                "Buy price (GP)",
                min_value=1.0,
                value=float(item_row['avg_low_price']),
                step=1.0
            )
        else:
            buy_price = item_row['avg_low_price']
            st.info(f"Using average buy price: {buy_price:.0f} GP")
    
    with col2:
        custom_sell = st.checkbox("Use custom sell price")
        if custom_sell:
            sell_price = st.number_input(
                "Sell price (GP)",
                min_value=1.0,
                value=float(item_row['avg_high_price']),
                step=1.0
            )
        else:
            sell_price = item_row['avg_high_price']
            st.info(f"Using average sell price: {sell_price:.0f} GP")
    
    # Calculate
    investment = buy_price * quantity
    gross_revenue = sell_price * quantity
    gross_profit = gross_revenue - investment
    ge_tax = sell_price * quantity * 0.01  # 1% tax
    net_profit = gross_profit - ge_tax
    roi = (net_profit / investment * 100) if investment > 0 else 0
    
    # Results
    st.divider()
    st.markdown("### 💵 Simulation Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("💰 Investment", f"{investment:,.0f} GP")
    col2.metric("📈 Revenue", f"{gross_revenue:,.0f} GP")
    col3.metric("💸 GE Tax (1%)", f"{ge_tax:,.0f} GP", delta=f"-{ge_tax:,.0f}")
    col4.metric("💵 Net Profit", f"{net_profit:,.0f} GP", 
                delta=f"{roi:.2f}% ROI",
                delta_color="normal" if net_profit > 0 else "inverse")
    
    # Visual breakdown
    st.markdown("### 📊 Profit Breakdown")
    
    fig = go.Figure(data=[
        go.Bar(name='Investment', x=['Trade'], y=[investment], marker_color='#e74c3c'),
        go.Bar(name='Gross Profit', x=['Trade'], y=[gross_profit], marker_color='#3498db'),
        go.Bar(name='GE Tax', x=['Trade'], y=[-ge_tax], marker_color='#95a5a6'),
        go.Bar(name='Net Profit', x=['Trade'], y=[net_profit], marker_color='#2ecc71')
    ])
    
    fig.update_layout(
        barmode='relative',
        title="Profit/Loss Breakdown",
        yaxis_title="GP",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("ℹ️ Item Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📦 General Info")
        st.write(f"**Item ID:** {item_id}")
        st.write(f"**Name:** {item_row['name']}")
        st.write(f"**Members:** {'Yes' if item_row['members'] else 'No'}")
        st.write(f"**Buy Limit:** {item_row['limit']:.0f} / 4 hours")
        
        st.markdown("### 💎 Alchemy Values")
        st.write(f"**High Alch:** {item_row['highalch']:.0f} GP")
        st.write(f"**Low Alch:** {item_row['lowalch']:.0f} GP")
    
    with col2:
        st.markdown("### 📊 Data Quality")
        st.write(f"**Total Records:** {item_row['records']:.0f}")
        st.write(f"**Days Since Activity:** {item_row['days_since_last_activity']:.0f}")
        st.write(f"**Price Volatility:** {item_row['price_volatility']:.4f}")
        st.write(f"**Spread Volatility:** {item_row['spread_volatility']:.2f}")
        
        st.markdown("### 🔗 Links")
        st.markdown(f"[OSRS Wiki](https://oldschool.runescape.wiki/w/{item_row['name'].replace(' ', '_')})")
        st.markdown(f"[GE Tracker](https://www.ge-tracker.com/item/{item_row['name'].replace(' ', '-').lower()})")

# Footer
st.divider()
st.info("💡 Historical data is from 6h intervals. For more granular analysis, 1h data is used internally for timing optimization.")
