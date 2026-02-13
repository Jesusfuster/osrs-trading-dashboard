"""
Chart creation utilities using Plotly
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

def create_price_chart(
    df: pd.DataFrame,
    title: str = "Price History",
    show_volume: bool = False
) -> go.Figure:
    """
    Create interactive price chart with buy/sell prices
    
    Args:
        df: DataFrame with columns: datetime, avgHighPrice, avgLowPrice
        title: Chart title
        show_volume: Whether to show volume as secondary y-axis
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    # Sell price
    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['avgHighPrice'],
        name='Sell Price',
        line=dict(color='#2ecc71', width=2),
        fill=None
    ))
    
    # Buy price
    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['avgLowPrice'],
        name='Buy Price',
        line=dict(color='#e74c3c', width=2),
        fill='tonexty',
        fillcolor='rgba(231, 76, 60, 0.1)'
    ))
    
    # Volume (optional)
    if show_volume and 'highPriceVolume' in df.columns:
        df_vol = df.copy()
        df_vol['total_volume'] = df_vol['highPriceVolume'] + df_vol['lowPriceVolume']
        
        fig.add_trace(go.Bar(
            x=df_vol['datetime'],
            y=df_vol['total_volume'],
            name='Volume',
            marker_color='rgba(128, 128, 128, 0.3)',
            yaxis='y2'
        ))
        
        # Secondary y-axis for volume
        fig.update_layout(
            yaxis2=dict(
                title='Volume',
                overlaying='y',
                side='right'
            )
        )
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Price (GP)',
        hovermode='x unified',
        height=500
    )
    
    return fig


def create_spread_chart(df: pd.DataFrame, title: str = "Spread Over Time") -> go.Figure:
    """
    Create spread percentage chart
    
    Args:
        df: DataFrame with avgHighPrice and avgLowPrice
        title: Chart title
    
    Returns:
        Plotly Figure
    """
    df_spread = df.copy()
    df_spread['spread_pct'] = (
        (df_spread['avgHighPrice'] - df_spread['avgLowPrice']) /
        df_spread['avgLowPrice'] * 100
    )
    
    fig = px.line(
        df_spread,
        x='datetime',
        y='spread_pct',
        title=title,
        labels={'spread_pct': 'Spread (%)', 'datetime': 'Date'}
    )
    
    # Add average line
    avg_spread = df_spread['spread_pct'].mean()
    fig.add_hline(
        y=avg_spread,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Avg: {avg_spread:.2f}%"
    )
    
    fig.update_layout(height=400)
    
    return fig


def create_volume_chart(df: pd.DataFrame, title: str = "Trading Volume") -> go.Figure:
    """
    Create volume bar chart
    
    Args:
        df: DataFrame with highPriceVolume and lowPriceVolume
        title: Chart title
    
    Returns:
        Plotly Figure
    """
    df_vol = df.copy()
    df_vol['total_volume'] = df_vol['highPriceVolume'] + df_vol['lowPriceVolume']
    
    fig = px.bar(
        df_vol,
        x='datetime',
        y='total_volume',
        title=title,
        labels={'total_volume': 'Volume', 'datetime': 'Date'},
        color_discrete_sequence=['#3498db']
    )
    
    fig.update_layout(height=400)
    
    return fig


def create_scatter_matrix(df: pd.DataFrame, columns: list) -> go.Figure:
    """
    Create scatter matrix for multiple metrics
    
    Args:
        df: DataFrame with metrics
        columns: List of column names to include
    
    Returns:
        Plotly Figure
    """
    fig = px.scatter_matrix(
        df,
        dimensions=columns,
        color='final_score',
        title="Metrics Correlation Matrix"
    )
    
    fig.update_traces(diagonal_visible=False)
    
    return fig


def create_roi_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Create ROI distribution histogram
    
    Args:
        df: DataFrame with avg_roi column
    
    Returns:
        Plotly Figure
    """
    fig = px.histogram(
        df,
        x='avg_roi',
        nbins=30,
        title="ROI Distribution",
        labels={'avg_roi': 'Average ROI (%)'},
        color_discrete_sequence=['#2ecc71']
    )
    
    fig.update_layout(height=400)
    
    return fig
