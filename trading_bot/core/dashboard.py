import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from initializer import Account
from performance_tracker import PerformanceTracker
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")


@st.cache_resource
def get_account():
    return Account()


@st.cache_resource
def get_tracker():
    return PerformanceTracker()


def create_performance_chart(trade_history):
    if trade_history.empty:
        return go.Figure()

    trade_history['cumulative_pnl'] = trade_history['pnl'].cumsum()

    fig = make_subplots(rows=2, cols=1,
                        row_heights=[0.7, 0.3],
                        shared_xaxes=True,
                        vertical_spacing=0.03)

    fig.add_trace(
        go.Scatter(x=trade_history['exit_time'],
                   y=trade_history['cumulative_pnl'],
                   name='Cumulative P&L'),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(x=trade_history['exit_time'],
               y=trade_history['pnl'],
               name='Trade P&L'),
        row=2, col=1
    )

    fig.update_layout(height=600, title='Trading Performance')
    return fig


def main():
    st.title("Trading Bot Dashboard")

    account = get_account()
    tracker = get_tracker()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Buying Power", f"${account.get_buying_power():,.2f}")

    portfolio = account.get_portfolio()
    total_positions = len(portfolio)
    with col2:
        st.metric("Active Positions", total_positions)

    metrics = tracker.get_performance_metrics()
    with col3:
        st.metric("Total P&L", f"${metrics['total_pnl']:,.2f}")

    st.subheader("Performance Metrics")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("Win Rate", f"{metrics['win_rate'] * 100:.1f}%")
    with metric_col2:
        st.metric("Total Trades", metrics['total_trades'])
    with metric_col3:
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    with metric_col4:
        st.metric("Max Drawdown", f"{metrics['max_drawdown'] * 100:.1f}%")

    st.subheader("Performance Chart")
    trade_history = tracker.get_trade_history()
    fig = create_performance_chart(trade_history)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Positions")
        current_positions = tracker.get_current_positions()
        if not current_positions.empty:
            st.dataframe(current_positions, use_container_width=True)
        else:
            st.info("No active positions")

    with col2:
        st.subheader("Recent Trades")
        if not trade_history.empty:
            recent_trades = trade_history.tail(10)
            st.dataframe(recent_trades, use_container_width=True)
        else:
            st.info("No trades recorded yet")


if __name__ == "__main__":
    main()