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


def get_portfolio_history(account, period='1M'):
    """Get portfolio history from Alpaca"""
    try:
        trading_client = account.get_trading_client()
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        from alpaca.trading.enums import TimeFrame
        
        request = GetPortfolioHistoryRequest(
            period=period,
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


def get_recent_orders(account, limit=50):
    """Get recent orders from Alpaca"""
    try:
        trading_client = account.get_trading_client()
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        
        request = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit
        )
        orders = trading_client.get_orders(request)
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'Symbol': order.symbol,
                'Side': order.side.value,
                'Type': order.type.value,
                'Qty': float(order.qty) if order.qty else 0,
                'Filled Qty': float(order.filled_qty) if order.filled_qty else 0,
                'Status': order.status.value,
                'Submitted': pd.to_datetime(order.submitted_at).strftime('%Y-%m-%d %H:%M:%S'),
                'Filled Price': f"${float(order.filled_avg_price):.2f}" if order.filled_avg_price else 'N/A',
            })
        
        return pd.DataFrame(orders_data)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return pd.DataFrame()


def get_account_activities(account, activity_type=None, limit=100):
    """Get account activities from Alpaca"""
    try:
        trading_client = account.get_trading_client()
        from alpaca.trading.requests import GetAccountActivitiesRequest
        
        request = GetAccountActivitiesRequest(
            activity_types=activity_type,
        )
        activities = trading_client.get_account_activities(request)
        
        activities_data = []
        for activity in activities[:limit]:
            activity_dict = {
                'Date': pd.to_datetime(activity.activity_type if hasattr(activity, 'transaction_time') else activity.date).strftime('%Y-%m-%d %H:%M:%S') if hasattr(activity, 'date') or hasattr(activity, 'transaction_time') else 'N/A',
                'Type': activity.activity_type if hasattr(activity, 'activity_type') else 'N/A',
            }
            
            if hasattr(activity, 'symbol'):
                activity_dict['Symbol'] = activity.symbol
            if hasattr(activity, 'qty'):
                activity_dict['Qty'] = float(activity.qty)
            if hasattr(activity, 'price'):
                activity_dict['Price'] = f"${float(activity.price):.2f}"
            if hasattr(activity, 'side'):
                activity_dict['Side'] = activity.side
            if hasattr(activity, 'net_amount'):
                activity_dict['Amount'] = f"${float(activity.net_amount):.2f}"
                
            activities_data.append(activity_dict)
        
        return pd.DataFrame(activities_data)
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
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
    st.caption("Starting Capital: $100.00")
    
    # Add refresh button and time period selector
    col_refresh, col_period, col_auto = st.columns([1, 2, 3])
    with col_refresh:
        if st.button("Refresh"):
            st.rerun()
    with col_period:
        period = st.selectbox("Time Period", ["1W", "1M", "3M", "1A", "All"], index=1)
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
    portfolio_history = get_portfolio_history(account, period=period)
    
    if not portfolio_history.empty:
        fig_portfolio = create_portfolio_chart(portfolio_history)
        st.plotly_chart(fig_portfolio, use_container_width=True)
        
        # Calculate period statistics
        total_return = portfolio_history['equity'].iloc[-1] - portfolio_history['equity'].iloc[0]
        total_return_pct = (total_return / portfolio_history['equity'].iloc[0]) * 100
        
        # Calculate volatility and Sharpe ratio
        daily_returns = portfolio_history['profit_loss_pct']
        volatility = daily_returns.std() * (252 ** 0.5)  # Annualized volatility
        avg_return = daily_returns.mean() * 252  # Annualized return
        sharpe_ratio = (avg_return - 0.02) / volatility if volatility > 0 else 0  # Assuming 2% risk-free rate
        
        # Calculate max drawdown
        cumulative = (1 + daily_returns / 100).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
        with stat_col1:
            st.metric("Period Return", f"${total_return:,.2f}", f"{total_return_pct:+.2f}%")
        with stat_col2:
            st.metric("Best Day", f"${portfolio_history['profit_loss'].max():,.2f}")
        with stat_col3:
            st.metric("Worst Day", f"${portfolio_history['profit_loss'].min():,.2f}")
        with stat_col4:
            st.metric("Volatility (Ann.)", f"{volatility:.2f}%")
        with stat_col5:
            st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
        
        # Additional statistics row
        stat2_col1, stat2_col2, stat2_col3, stat2_col4 = st.columns(4)
        with stat2_col1:
            avg_daily = portfolio_history['profit_loss'].mean()
            st.metric("Avg Daily P&L", f"${avg_daily:,.2f}")
        with stat2_col2:
            winning_days = (portfolio_history['profit_loss'] > 0).sum()
            total_days = len(portfolio_history)
            win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
            st.metric("Winning Days", f"{winning_days}/{total_days} ({win_rate:.1f}%)")
        with stat2_col3:
            st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
        with stat2_col4:
            total_pnl = portfolio_history['profit_loss'].sum()
            st.metric("Total P&L", f"${total_pnl:,.2f}")
    else:
        st.info("No portfolio history available yet.")

    # Current Positions Section
    st.header("Current Positions")
    
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

    # Recent Orders Section
    st.header("Recent Orders")
    recent_orders = get_recent_orders(account, limit=20)
    
    if not recent_orders.empty:
        # Add filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            status_filter = st.multiselect("Filter by Status", 
                                          options=recent_orders['Status'].unique().tolist(),
                                          default=recent_orders['Status'].unique().tolist())
        with col_filter2:
            side_filter = st.multiselect("Filter by Side",
                                        options=recent_orders['Side'].unique().tolist(),
                                        default=recent_orders['Side'].unique().tolist())
        with col_filter3:
            type_filter = st.multiselect("Filter by Type",
                                        options=recent_orders['Type'].unique().tolist(),
                                        default=recent_orders['Type'].unique().tolist())
        
        filtered_orders = recent_orders[
            (recent_orders['Status'].isin(status_filter)) &
            (recent_orders['Side'].isin(side_filter)) &
            (recent_orders['Type'].isin(type_filter))
        ]
        
        st.dataframe(filtered_orders, use_container_width=True, hide_index=True)
        
        # Order statistics
        if not filtered_orders.empty:
            order_stat_col1, order_stat_col2, order_stat_col3, order_stat_col4 = st.columns(4)
            with order_stat_col1:
                total_orders = len(filtered_orders)
                st.metric("Total Orders", total_orders)
            with order_stat_col2:
                filled_orders = len(filtered_orders[filtered_orders['Status'] == 'filled'])
                st.metric("Filled Orders", filled_orders)
            with order_stat_col3:
                pending_orders = len(filtered_orders[filtered_orders['Status'].isin(['pending_new', 'accepted', 'new'])])
                st.metric("Pending Orders", pending_orders)
            with order_stat_col4:
                cancelled_orders = len(filtered_orders[filtered_orders['Status'] == 'canceled'])
                st.metric("Cancelled Orders", cancelled_orders)
    else:
        st.info("No orders found.")

    # Account Activities Section
    st.header("Account Activities")
    activities = get_account_activities(account, limit=50)
    
    if not activities.empty:
        # Activity type filter
        if 'Type' in activities.columns:
            activity_types = activities['Type'].unique().tolist()
            selected_types = st.multiselect("Filter by Activity Type", 
                                           options=activity_types,
                                           default=activity_types)
            filtered_activities = activities[activities['Type'].isin(selected_types)]
        else:
            filtered_activities = activities
        
        st.dataframe(filtered_activities, use_container_width=True, hide_index=True)
        
        # Activity summary
        if 'Type' in filtered_activities.columns:
            st.subheader("Activity Summary")
            activity_counts = filtered_activities['Type'].value_counts()
            
            fig_activity = go.Figure(data=[go.Bar(
                x=activity_counts.index,
                y=activity_counts.values,
                marker_color='#00D9FF'
            )])
            fig_activity.update_layout(
                title='Activity Types Distribution',
                xaxis_title='Activity Type',
                yaxis_title='Count',
                height=400
            )
            st.plotly_chart(fig_activity, use_container_width=True)
    else:
        st.info("No activities found.")

    # Risk Metrics Section
    st.header("Risk Analysis")
    
    risk_col1, risk_col2 = st.columns(2)
    
    with risk_col1:
        st.subheader("Position Concentration")
        if not positions_data.empty:
            # Calculate concentration metrics
            positions_data['Market Value Clean'] = positions_data['Market Value'].str.replace('$', '').str.replace(',', '').astype(float)
            total_portfolio = positions_data['Market Value Clean'].sum()
            
            concentration_data = []
            for _, pos in positions_data.iterrows():
                weight = (pos['Market Value Clean'] / total_portfolio * 100) if total_portfolio > 0 else 0
                concentration_data.append({
                    'Symbol': pos['Symbol'],
                    'Weight %': f"{weight:.2f}%",
                    'Market Value': pos['Market Value']
                })
            
            concentration_df = pd.DataFrame(concentration_data)
            st.dataframe(concentration_df, use_container_width=True, hide_index=True)
            
            # Highlight if concentration is too high
            max_weight = positions_data['Market Value Clean'].max() / total_portfolio * 100 if total_portfolio > 0 else 0
            if max_weight > 20:
                st.warning(f"Highest position concentration: {max_weight:.1f}% - Consider diversification")
        else:
            st.info("No positions to analyze")
    
    with risk_col2:
        st.subheader("Margin Utilization")
        if account_info['buying_power'] > 0:
            # Calculate margin usage
            used_buying_power = account_info['long_market_value']
            available_buying_power = account_info['buying_power']
            total_buying_power = used_buying_power + available_buying_power
            margin_usage = (used_buying_power / total_buying_power * 100) if total_buying_power > 0 else 0
            
            # Create gauge chart
            fig_margin = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=margin_usage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Margin Usage %"},
                delta={'reference': 50},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgreen"},
                        {'range': [50, 75], 'color': "yellow"},
                        {'range': [75, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_margin.update_layout(height=300)
            st.plotly_chart(fig_margin, use_container_width=True)
            
            margin_metrics = st.columns(3)
            with margin_metrics[0]:
                st.metric("Used", f"${used_buying_power:,.2f}")
            with margin_metrics[1]:
                st.metric("Available", f"${available_buying_power:,.2f}")
            with margin_metrics[2]:
                st.metric("Total", f"${total_buying_power:,.2f}")


if __name__ == "__main__":
    main()