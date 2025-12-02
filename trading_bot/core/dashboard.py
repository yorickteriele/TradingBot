import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from trading_bot.core.initializer import Account
from trading_bot.core.performance_tracker import PerformanceTracker
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")


@st.cache_resource
def get_account():
    return Account()


@st.cache_resource
def get_tracker():
    return PerformanceTracker()


def get_account_info(account):
    """Get detailed account information from Alpaca"""
    try:
        acc = account.get_trading_client().get_account()
        return {
            'equity': float(acc.equity),
            'cash': float(acc.cash),
            'buying_power': float(acc.buying_power),
            'portfolio_value': float(acc.portfolio_value),
            'last_equity': float(acc.last_equity),
            'long_market_value': float(acc.long_market_value) if acc.long_market_value else 0,
            'short_market_value': float(acc.short_market_value) if acc.short_market_value else 0,
            'initial_margin': float(acc.initial_margin) if acc.initial_margin else 0,
            'maintenance_margin': float(acc.maintenance_margin) if acc.maintenance_margin else 0,
            'daytrade_count': int(acc.daytrade_count) if acc.daytrade_count else 0,
            'daytrading_buying_power': float(acc.daytrading_buying_power) if acc.daytrading_buying_power else 0,
        }
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return None


def get_positions_data(account):
    """Get all positions with current values"""
    try:
        positions = account.get_trading_client().get_all_positions()
        positions_data = []
        
        for pos in positions:
            positions_data.append({
                'Symbol': pos.symbol,
                'Qty': float(pos.qty),
                'Avg Entry': f"${float(pos.avg_entry_price):.2f}",
                'Current': f"${float(pos.current_price):.2f}",
                'Market Value': f"${float(pos.market_value):.2f}",
                'Unrealized P&L': float(pos.unrealized_pl),
                'Unrealized P&L %': float(pos.unrealized_plpc) * 100,
                'Side': pos.side,
            })
        
        return pd.DataFrame(positions_data)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return pd.DataFrame()


def get_portfolio_history(account):
    """Get portfolio history from Alpaca"""
    try:
        trading_client = account.get_trading_client()
        # Get portfolio history for the last 30 days
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        from alpaca.trading.enums import TimeFrame
        
        request = GetPortfolioHistoryRequest(
            period='1M',
            timeframe=TimeFrame.Day
        )
        history = trading_client.get_portfolio_history(request)
        
        if history and history.equity:
            df = pd.DataFrame({
                'timestamp': [datetime.fromtimestamp(ts) for ts in history.timestamp],
                'equity': history.equity,
                'profit_loss': history.profit_loss,
                'profit_loss_pct': history.profit_loss_pct
            })
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error getting portfolio history: {e}")
        return pd.DataFrame()


def create_performance_chart(trade_history):
    """Create performance chart from trade history"""
    if trade_history.empty:
        return go.Figure()

    trade_history['cumulative_pnl'] = trade_history['pnl'].cumsum()

    fig = make_subplots(rows=2, cols=1,
                        row_heights=[0.7, 0.3],
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=('Cumulative P&L', 'Individual Trade P&L'))

    fig.add_trace(
        go.Scatter(x=trade_history['exit_time'],
                   y=trade_history['cumulative_pnl'],
                   name='Cumulative P&L',
                   line=dict(color='#00D9FF', width=2),
                   fill='tozeroy'),
        row=1, col=1
    )

    colors = ['green' if pnl > 0 else 'red' for pnl in trade_history['pnl']]
    fig.add_trace(
        go.Bar(x=trade_history['exit_time'],
               y=trade_history['pnl'],
               name='Trade P&L',
               marker_color=colors),
        row=2, col=1
    )

    fig.update_layout(height=600, title='Trading Performance', showlegend=False)
    fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
    fig.update_yaxes(title_text="P&L ($)", row=2, col=1)
    return fig


def create_portfolio_chart(portfolio_history):
    """Create portfolio equity chart from Alpaca history"""
    if portfolio_history.empty:
        return go.Figure()

    fig = make_subplots(rows=2, cols=1,
                        row_heights=[0.7, 0.3],
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=('Portfolio Equity', 'Daily P&L'))

    fig.add_trace(
        go.Scatter(x=portfolio_history['timestamp'],
                   y=portfolio_history['equity'],
                   name='Equity',
                   line=dict(color='#00D9FF', width=2),
                   fill='tozeroy'),
        row=1, col=1
    )

    colors = ['green' if pl > 0 else 'red' for pl in portfolio_history['profit_loss']]
    fig.add_trace(
        go.Bar(x=portfolio_history['timestamp'],
               y=portfolio_history['profit_loss'],
               name='Daily P&L',
               marker_color=colors),
        row=2, col=1
    )

    fig.update_layout(height=600, title='Portfolio Performance (Last 30 Days)', showlegend=False)
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="P&L ($)", row=2, col=1)
    return fig


def main():
    st.title("Trading Bot Dashboard")
    
    # Add refresh button
    col_refresh, col_auto = st.columns([1, 5])
    with col_refresh:
        if st.button("Refresh"):
            st.rerun()
    with col_auto:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()

    account = get_account()
    tracker = get_tracker()

    # Get account info from Alpaca
    account_info = get_account_info(account)
    
    if not account_info:
        st.error("Unable to connect to Alpaca API. Please check your credentials.")
        return

    # Account Overview Section
    st.header("Account Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Calculate daily P&L
    daily_pnl = account_info['equity'] - account_info['last_equity']
    daily_pnl_pct = (daily_pnl / account_info['last_equity'] * 100) if account_info['last_equity'] > 0 else 0
    
    with col1:
        st.metric(
            "Portfolio Value", 
            f"${account_info['equity']:,.2f}",
            f"{daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)"
        )
    
    with col2:
        st.metric("Cash", f"${account_info['cash']:,.2f}")
    
    with col3:
        st.metric("Buying Power", f"${account_info['buying_power']:,.2f}")
    
    positions_data = get_positions_data(account)
    total_positions = len(positions_data)
    
    with col4:
        st.metric("Open Positions", total_positions)
    
    total_unrealized_pnl = positions_data['Unrealized P&L'].sum() if not positions_data.empty else 0
    
    with col5:
        st.metric("Unrealized P&L", f"${total_unrealized_pnl:,.2f}")

    # Additional Account Details
    with st.expander("Additional Account Details"):
        detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
        
        with detail_col1:
            st.metric("Long Market Value", f"${account_info['long_market_value']:,.2f}")
        with detail_col2:
            st.metric("Short Market Value", f"${account_info['short_market_value']:,.2f}")
        with detail_col3:
            st.metric("Day Trade Count", account_info['daytrade_count'])
        with detail_col4:
            st.metric("Day Trading BP", f"${account_info['daytrading_buying_power']:,.2f}")

    # Portfolio History Chart
    st.header("Portfolio Performance")
    portfolio_history = get_portfolio_history(account)
    
    if not portfolio_history.empty:
        fig_portfolio = create_portfolio_chart(portfolio_history)
        st.plotly_chart(fig_portfolio, use_container_width=True)
        
        # Calculate period statistics
        total_return = portfolio_history['equity'].iloc[-1] - portfolio_history['equity'].iloc[0]
        total_return_pct = (total_return / portfolio_history['equity'].iloc[0]) * 100
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        with stat_col1:
            st.metric("Period Return", f"${total_return:,.2f}", f"{total_return_pct:+.2f}%")
        with stat_col2:
            st.metric("Best Day", f"${portfolio_history['profit_loss'].max():,.2f}")
        with stat_col3:
            st.metric("Worst Day", f"${portfolio_history['profit_loss'].min():,.2f}")
        with stat_col4:
            avg_daily = portfolio_history['profit_loss'].mean()
            st.metric("Avg Daily P&L", f"${avg_daily:,.2f}")
    else:
        st.info("No portfolio history available yet.")

    # Current Positions Section
    st.header("💼 Current Positions")
    
    if not positions_data.empty:
        # Style the dataframe
        def color_pnl(val):
            if isinstance(val, (int, float)):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}'
            return ''
        
        styled_positions = positions_data.style.applymap(
            color_pnl, 
            subset=['Unrealized P&L', 'Unrealized P&L %']
        ).format({
            'Unrealized P&L': '${:.2f}',
            'Unrealized P&L %': '{:.2f}%',
            'Qty': '{:.0f}'
        })
        
        st.dataframe(styled_positions, use_container_width=True)
        
        # Position breakdown pie chart
        if len(positions_data) > 0:
            col_pie1, col_pie2 = st.columns(2)
            
            with col_pie1:
                # Market value breakdown
                positions_data['Market Value Clean'] = positions_data['Market Value'].str.replace('$', '').str.replace(',', '').astype(float)
                fig_pie = go.Figure(data=[go.Pie(
                    labels=positions_data['Symbol'],
                    values=positions_data['Market Value Clean'],
                    hole=.3
                )])
                fig_pie.update_layout(title='Portfolio Allocation by Market Value', height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_pie2:
                # P&L breakdown
                fig_pnl_pie = go.Figure(data=[go.Pie(
                    labels=positions_data['Symbol'],
                    values=positions_data['Unrealized P&L'],
                    hole=.3
                )])
                fig_pnl_pie.update_layout(title='Unrealized P&L by Position', height=400)
                st.plotly_chart(fig_pnl_pie, use_container_width=True)
    else:
        st.info("No open positions currently.")

    # Bot Performance Metrics (from tracker)
    st.header("Bot Trading Performance")
    metrics = tracker.get_performance_metrics()
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("Total Trades", metrics['total_trades'])
    with metric_col2:
        st.metric("Win Rate", f"{metrics['win_rate'] * 100:.1f}%")
    with metric_col3:
        st.metric("Total P&L", f"${metrics['total_pnl']:,.2f}")
    with metric_col4:
        st.metric("Max Drawdown", f"{metrics['max_drawdown'] * 100:.1f}%")

    # Trade History Chart
    trade_history = tracker.get_trade_history()
    
    if not trade_history.empty:
        closed_trades = trade_history[trade_history['exit_time'].notna()]
        if not closed_trades.empty:
            st.subheader("Trade History Performance")
            fig = create_performance_chart(closed_trades)
            st.plotly_chart(fig, use_container_width=True)

    # Trade History Tables
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Trades")
        if not trade_history.empty:
            closed_trades = trade_history[trade_history['exit_time'].notna()].tail(10)
            if not closed_trades.empty:
                display_trades = closed_trades[['symbol', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl', 'sentiment']].copy()
                display_trades['entry_time'] = pd.to_datetime(display_trades['entry_time']).dt.strftime('%Y-%m-%d %H:%M')
                display_trades['exit_time'] = pd.to_datetime(display_trades['exit_time']).dt.strftime('%Y-%m-%d %H:%M')
                
                def color_pnl(val):
                    if isinstance(val, (int, float)):
                        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                        return f'color: {color}'
                    return ''
                
                styled_trades = display_trades.style.applymap(color_pnl, subset=['pnl']).format({'pnl': '${:.2f}', 'entry_price': '${:.2f}', 'exit_price': '${:.2f}'})
                st.dataframe(styled_trades, use_container_width=True, hide_index=True)
            else:
                st.info("No closed trades yet.")
        else:
            st.info("No trades recorded yet.")

    with col2:
        st.subheader("Active Bot Positions")
        current_positions = tracker.get_current_positions()
        if not current_positions.empty:
            display_positions = current_positions[['symbol', 'entry_time', 'entry_price', 'position_size', 'stop_loss']].copy()
            display_positions['entry_time'] = pd.to_datetime(display_positions['entry_time']).dt.strftime('%Y-%m-%d %H:%M')
            display_positions = display_positions.rename(columns={
                'symbol': 'Symbol',
                'entry_time': 'Entry Time',
                'entry_price': 'Entry Price',
                'position_size': 'Size',
                'stop_loss': 'Stop Loss'
            })
            st.dataframe(display_positions, use_container_width=True, hide_index=True)
        else:
            st.info("No active positions tracked by bot.")


if __name__ == "__main__":
    main()