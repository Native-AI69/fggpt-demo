import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================
# PASSWORD PROTECTION
# ============================================
def check_password():
    """Returns True if password is correct"""
    
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "FG-GPT2025"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h1>🔒 FG-GPT Value Creation Model</h1>
            <p>This dashboard is password protected.</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        return False
    
    elif not st.session_state["password_correct"]:
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h1>🔒 FG-GPT Value Creation Model</h1>
            <p>This dashboard is password protected.</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password")
        return False
    
    return True

# Check password before showing anything
if not check_password():
    st.stop()

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="FG-GPT Value Creation Model",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# EMBEDDED BASE DATA (Protected - not in external files)
# ============================================

# Base plant parameters (derived from 7 Ranch analysis)
BASE_DATA = {
    'plant_name': '7 Ranch Solar',
    'plant_capacity_mw': 240,
    'data_period': 'January - September 2025',
    'total_hours': 6554,
    'production_hours': 3495,
    'annualization_factor': 1.333,
}

# Hub price statistics (aggregated - not raw hourly data)
HUB_STATS = {
    'HB_NORTH': {'avg_da': 25.42, 'avg_rt': 28.15, 'avg_dart': 2.73, 'volatility': 45.2},
    'HB_SOUTH': {'avg_da': 26.18, 'avg_rt': 31.24, 'avg_dart': 5.06, 'volatility': 52.8},
    'HB_WEST': {'avg_da': 22.35, 'avg_rt': 26.89, 'avg_dart': 4.54, 'volatility': 68.4},
    'HB_HOUSTON': {'avg_da': 27.45, 'avg_rt': 30.12, 'avg_dart': 2.67, 'volatility': 41.5},
    'HB_PAN': {'avg_da': 19.82, 'avg_rt': 24.56, 'avg_dart': 4.74, 'volatility': 72.1},
}

# Base value creation metrics (per MW basis from analysis)
BASE_VALUE_PER_MW = {
    'rn_optimization': 20271,      # $/MW/year from RN strategy
    'vt_alpha': 23148,             # $/MW/year from VT Alpha
    'vt_hedge': 25386,             # $/MW/year from VT Hedge
}

# Confidence signal distribution
SIGNAL_DISTRIBUTION = {
    'high_confidence_pct': 0.15,   # 15% of hours
    'med_confidence_pct': 0.35,    # 35% of hours
    'low_confidence_pct': 0.50,    # 50% of hours
}

# Monthly seasonality factors
MONTHLY_FACTORS = {
    'Jan': 0.75, 'Feb': 0.82, 'Mar': 0.95, 'Apr': 1.05,
    'May': 1.15, 'Jun': 1.25, 'Jul': 1.35, 'Aug': 1.30,
    'Sep': 1.10, 'Oct': 0.95, 'Nov': 0.80, 'Dec': 0.70,
}

# ============================================
# CALCULATION FUNCTIONS
# ============================================

def calculate_rn_value(plant_mw, mae, hub_stats, capture_rates):
    """Calculate RN optimization value based on inputs"""
    base_value = BASE_VALUE_PER_MW['rn_optimization']
    
    # MAE adjustment (lower MAE = higher value)
    mae_factor = (10 - mae) / 4  # Normalized around MAE=6
    
    # Hub volatility adjustment
    vol_factor = hub_stats['volatility'] / 50  # Normalized around 50
    
    # Capture rate weighted average
    weighted_capture = (
        capture_rates['high'] * SIGNAL_DISTRIBUTION['high_confidence_pct'] +
        capture_rates['med'] * SIGNAL_DISTRIBUTION['med_confidence_pct'] +
        capture_rates['low'] * SIGNAL_DISTRIBUTION['low_confidence_pct']
    ) / 100
    
    adjusted_value = base_value * mae_factor * vol_factor * weighted_capture * 2
    return plant_mw * adjusted_value

def calculate_vt_alpha(position_mw, mae, hub_stats, capture_rates):
    """Calculate VT Alpha value"""
    base_value = BASE_VALUE_PER_MW['vt_alpha']
    
    mae_factor = (10 - mae) / 4
    spread_factor = hub_stats['avg_dart'] / 4  # Normalized around $4 spread
    
    weighted_capture = (
        capture_rates['high'] * SIGNAL_DISTRIBUTION['high_confidence_pct'] +
        capture_rates['med'] * SIGNAL_DISTRIBUTION['med_confidence_pct'] * 0.5 +
        capture_rates['low'] * SIGNAL_DISTRIBUTION['low_confidence_pct'] * 0.1
    ) / 100
    
    adjusted_value = base_value * mae_factor * spread_factor * weighted_capture * 3
    return position_mw * adjusted_value

def calculate_vt_hedge(plant_mw, mae, hub_stats, capture_rates):
    """Calculate VT Hedge value"""
    base_value = BASE_VALUE_PER_MW['vt_hedge']
    
    mae_factor = (10 - mae) / 4
    vol_factor = hub_stats['volatility'] / 50
    
    weighted_capture = (
        capture_rates['high'] * SIGNAL_DISTRIBUTION['high_confidence_pct'] +
        capture_rates['med'] * SIGNAL_DISTRIBUTION['med_confidence_pct'] * 0.7
    ) / 100
    
    adjusted_value = base_value * mae_factor * vol_factor * weighted_capture * 2.5
    return plant_mw * adjusted_value

def calculate_monthly_breakdown(annual_value):
    """Break down annual value by month using seasonality"""
    total_factor = sum(MONTHLY_FACTORS.values())
    monthly = {}
    for month, factor in MONTHLY_FACTORS.items():
        monthly[month] = annual_value * (factor / total_factor)
    return monthly

# ============================================
# SIDEBAR - USER INPUTS
# ============================================

st.sidebar.markdown("## ⚙️ Model Parameters")

st.sidebar.markdown("### 📊 Forecast Accuracy")
mae = st.sidebar.slider("MAE [$/MWh]", 3.0, 10.0, 6.0, 0.5, 
                        help="Mean Absolute Error - lower is better")
st.sidebar.caption(f"Thresholds: High >12 | Med 6-12 | Low <6")

st.sidebar.markdown("### 🏭 Plant Settings")
plant_mw = st.sidebar.number_input("Plant Capacity [MW]", 50, 1000, 240, 10)
virtual_mw = st.sidebar.number_input("Virtual Position [MW]", 0, 500, 100, 10)

st.sidebar.markdown("### 💰 Fee Structure")
fee_rate = st.sidebar.slider("FG Fee Rate [%]", 15, 50, 37, 1)

st.sidebar.markdown("### 🎯 Capture Rates")
col1, col2, col3 = st.sidebar.columns(3)
capture_high = col1.number_input("High%", 0, 100, 90, 5)
capture_med = col2.number_input("Med%", 0, 100, 50, 5)
capture_low = col3.number_input("Low%", 0, 100, 10, 5)

capture_rates = {'high': capture_high, 'med': capture_med, 'low': capture_low}

st.sidebar.markdown("### 🌐 Hub Selection")
hub_options = list(HUB_STATS.keys())
hub_display = [h.replace('HB_', '') for h in hub_options]
selected_hub = st.sidebar.selectbox("Alpha Hub (Non-Prod)", hub_options, 
                                     format_func=lambda x: x.replace('HB_', ''))

hub_stats = HUB_STATS[selected_hub]

# ============================================
# CALCULATIONS
# ============================================

# Calculate values
rn_value = calculate_rn_value(plant_mw, mae, hub_stats, capture_rates)
vt_alpha_value = calculate_vt_alpha(virtual_mw, mae, hub_stats, capture_rates)
vt_hedge_value = calculate_vt_hedge(plant_mw, mae, hub_stats, capture_rates)

# Annualize
rn_annual = rn_value * BASE_DATA['annualization_factor']
vt_alpha_annual = vt_alpha_value * BASE_DATA['annualization_factor']
vt_hedge_annual = vt_hedge_value * BASE_DATA['annualization_factor']

total_value = rn_annual + vt_alpha_annual + vt_hedge_annual
fg_revenue = total_value * (fee_rate / 100)
client_uplift = total_value - fg_revenue

value_per_mw = total_value / plant_mw if plant_mw > 0 else 0
mw_for_10m = 10_000_000 / (fg_revenue / plant_mw) if fg_revenue > 0 else 0

# ============================================
# MAIN CONTENT
# ============================================

st.markdown(f"### ⚡ FG-GPT Value Creation Model")
st.caption(f"{BASE_DATA['plant_name']} ({plant_mw} MW) | {BASE_DATA['data_period']} | Annualized Projections")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Executive Summary", 
    "📈 Resource Node", 
    "💹 Virtual Trading",
    "🎚️ Sensitivity & Scenarios",
    "📅 Monthly Performance",
    "📋 Data Summary"
])

# ============================================
# TAB 1: EXECUTIVE SUMMARY
# ============================================
with tab1:
    st.markdown("## 📊 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Combined $/MW/Year", f"${value_per_mw:,.0f}")
    with col2:
        st.metric("FG Annual Revenue", f"${fg_revenue:,.0f}", f"From {plant_mw} MW")
    with col3:
        st.metric("Client Annual Uplift", f"${client_uplift:,.0f}", f"+{(client_uplift/(total_value-client_uplift))*100:.0f}% revenue" if total_value > client_uplift else "")
    with col4:
        st.metric("MW for $10M ARR", f"{mw_for_10m:,.0f} MW", "Target capacity")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📊 Value Creation by Strategy")
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['RN Optimization', 'Alpha Trading', 'Hedge Trading'],
            values=[rn_annual, vt_alpha_annual, vt_hedge_annual],
            hole=0.5,
            marker_colors=['#1f77b4', '#2ca02c', '#ff7f0e']
        )])
        fig_pie.update_layout(
            annotations=[dict(text=f'${total_value/1e6:.1f}M<br>Total', x=0.5, y=0.5, font_size=16, showarrow=False)],
            height=350,
            showlegend=True
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_right:
        st.markdown("### 💰 Revenue Split")
        
        fig_bar = go.Figure()
        
        # Stacked bars for each strategy
        strategies = ['RN', 'VT Strategy', 'Combined']
        fg_values = [rn_annual * fee_rate/100, (vt_alpha_annual + vt_hedge_annual) * fee_rate/100, fg_revenue]
        client_values = [rn_annual * (1-fee_rate/100), (vt_alpha_annual + vt_hedge_annual) * (1-fee_rate/100), client_uplift]
        
        fig_bar.add_trace(go.Bar(name=f'FG ({fee_rate}%)', x=strategies, y=fg_values, marker_color='#1f77b4'))
        fig_bar.add_trace(go.Bar(name=f'Client ({100-fee_rate}%)', x=strategies, y=client_values, marker_color='#2ca02c'))
        
        fig_bar.update_layout(barmode='stack', height=350, yaxis_title='Annual Value ($)')
        st.plotly_chart(fig_bar, use_container_width=True)

# ============================================
# TAB 2: RESOURCE NODE
# ============================================
with tab2:
    st.markdown("## 📈 Resource Node Optimization")
    st.markdown("Optimize Day-Ahead vs Real-Time dispatch decisions based on price forecasts.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("RN Annual Value", f"${rn_annual:,.0f}")
    with col2:
        st.metric("RN $/MW/Year", f"${rn_annual/plant_mw:,.0f}")
    with col3:
        st.metric("% of Total Value", f"{rn_annual/total_value*100:.1f}%")
    
    st.markdown("---")
    
    st.markdown("### How RN Optimization Works")
    st.markdown("""
    1. **Forecast DA vs RT prices** for each hour
    2. **If RT > DA predicted:** Reduce DA commitment, sell more in RT
    3. **If DA > RT predicted:** Maximize DA commitment, reduce RT exposure
    4. **Capture the spread** between markets
    """)
    
    # Show hub comparison
    st.markdown("### Hub Price Statistics")
    hub_df = pd.DataFrame(HUB_STATS).T
    hub_df.columns = ['Avg DA ($/MWh)', 'Avg RT ($/MWh)', 'Avg DART Spread', 'Volatility']
    hub_df.index = [h.replace('HB_', '') for h in hub_df.index]
    st.dataframe(hub_df.style.format('${:.2f}'), use_container_width=True)

# ============================================
# TAB 3: VIRTUAL TRADING
# ============================================
with tab3:
    st.markdown("## 💹 Virtual Trading Strategies")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⬆️ VT Alpha")
        st.markdown("*Profit from predicting price direction*")
        st.metric("Annual Value", f"${vt_alpha_annual:,.0f}")
        st.metric("$/MW Position/Year", f"${vt_alpha_annual/virtual_mw:,.0f}" if virtual_mw > 0 else "$0")
        
        st.markdown("""
        **How it works:**
        - RT > DA → Virtual demand (buy DA, sell RT)
        - DA > RT → Virtual supply (sell DA, buy RT)
        - Profit if forecast is correct
        """)
    
    with col2:
        st.markdown("### 🛡️ VT Hedge")
        st.markdown("*Protect against adverse price moves*")
        st.metric("Annual Value", f"${vt_hedge_annual:,.0f}")
        st.metric("$/MW Hedged/Year", f"${vt_hedge_annual/plant_mw:,.0f}")
        
        st.markdown("""
        **How it works:**
        - Lock in revenue protection
        - When RT predicted to fall below DA
        - Insurance for your solar production
        """)
    
    st.markdown("---")
    
    # VT breakdown chart
    st.markdown("### VT Strategy Breakdown")
    fig_vt = go.Figure()
    fig_vt.add_trace(go.Bar(
        x=['Alpha', 'Hedge', 'Total VT'],
        y=[vt_alpha_annual, vt_hedge_annual, vt_alpha_annual + vt_hedge_annual],
        marker_color=['#2ca02c', '#ff7f0e', '#9467bd'],
        text=[f'${v/1e6:.2f}M' for v in [vt_alpha_annual, vt_hedge_annual, vt_alpha_annual + vt_hedge_annual]],
        textposition='outside'
    ))
    fig_vt.update_layout(height=300, yaxis_title='Annual Value ($)')
    st.plotly_chart(fig_vt, use_container_width=True)

# ============================================
# TAB 4: SENSITIVITY & SCENARIOS
# ============================================
with tab4:
    st.markdown("## 🎚️ Sensitivity & Scenarios")
    
    st.markdown("### MAE Sensitivity")
    mae_range = np.arange(3.0, 10.5, 0.5)
    mae_values = []
    for m in mae_range:
        rv = calculate_rn_value(plant_mw, m, hub_stats, capture_rates)
        va = calculate_vt_alpha(virtual_mw, m, hub_stats, capture_rates)
        vh = calculate_vt_hedge(plant_mw, m, hub_stats, capture_rates)
        total = (rv + va + vh) * BASE_DATA['annualization_factor']
        mae_values.append(total)
    
    fig_mae = go.Figure()
    fig_mae.add_trace(go.Scatter(x=mae_range, y=mae_values, mode='lines+markers', name='Total Value'))
    fig_mae.add_vline(x=mae, line_dash="dash", line_color="red", annotation_text=f"Current MAE: {mae}")
    fig_mae.update_layout(
        xaxis_title='MAE ($/MWh)',
        yaxis_title='Annual Value ($)',
        height=350
    )
    st.plotly_chart(fig_mae, use_container_width=True)
    
    st.markdown("### Capacity Sensitivity")
    cap_range = np.arange(100, 1050, 50)
    cap_values = []
    fg_values = []
    for c in cap_range:
        rv = calculate_rn_value(c, mae, hub_stats, capture_rates)
        va = calculate_vt_alpha(virtual_mw * c / plant_mw, mae, hub_stats, capture_rates)
        vh = calculate_vt_hedge(c, mae, hub_stats, capture_rates)
        total = (rv + va + vh) * BASE_DATA['annualization_factor']
        cap_values.append(total)
        fg_values.append(total * fee_rate / 100)
    
    fig_cap = go.Figure()
    fig_cap.add_trace(go.Scatter(x=cap_range, y=cap_values, mode='lines', name='Total Value'))
    fig_cap.add_trace(go.Scatter(x=cap_range, y=fg_values, mode='lines', name='FG Revenue'))
    fig_cap.add_hline(y=10_000_000, line_dash="dash", line_color="green", annotation_text="$10M ARR Target")
    fig_cap.update_layout(
        xaxis_title='Plant Capacity (MW)',
        yaxis_title='Annual Value ($)',
        height=350
    )
    st.plotly_chart(fig_cap, use_container_width=True)

# ============================================
# TAB 5: MONTHLY PERFORMANCE
# ============================================
with tab5:
    st.markdown("## 📅 Monthly Performance")
    
    monthly_rn = calculate_monthly_breakdown(rn_annual)
    monthly_vt = calculate_monthly_breakdown(vt_alpha_annual + vt_hedge_annual)
    
    months = list(MONTHLY_FACTORS.keys())
    rn_vals = [monthly_rn[m] for m in months]
    vt_vals = [monthly_vt[m] for m in months]
    
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(name='RN', x=months, y=rn_vals, marker_color='#1f77b4'))
    fig_monthly.add_trace(go.Bar(name='VT', x=months, y=vt_vals, marker_color='#2ca02c'))
    fig_monthly.update_layout(barmode='stack', height=400, yaxis_title='Monthly Value ($)')
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Monthly table
    st.markdown("### Monthly Breakdown")
    monthly_df = pd.DataFrame({
        'Month': months,
        'RN Value': rn_vals,
        'VT Value': vt_vals,
        'Total': [r + v for r, v in zip(rn_vals, vt_vals)],
        'FG Revenue': [(r + v) * fee_rate/100 for r, v in zip(rn_vals, vt_vals)],
    })
    monthly_df['Total'] = monthly_df['Total'].apply(lambda x: f'${x:,.0f}')
    monthly_df['RN Value'] = monthly_df['RN Value'].apply(lambda x: f'${x:,.0f}')
    monthly_df['VT Value'] = monthly_df['VT Value'].apply(lambda x: f'${x:,.0f}')
    monthly_df['FG Revenue'] = monthly_df['FG Revenue'].apply(lambda x: f'${x:,.0f}')
    st.dataframe(monthly_df, hide_index=True, use_container_width=True)

# ============================================
# TAB 6: DATA SUMMARY
# ============================================
with tab6:
    st.markdown("## 📋 Data Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Model Parameters")
        st.markdown(f"""
        | Parameter | Value |
        |-----------|-------|
        | Plant Capacity | {plant_mw} MW |
        | Virtual Position | {virtual_mw} MW |
        | FG Fee Rate | {fee_rate}% |
        | MAE | ${mae}/MWh |
        | Selected Hub | {selected_hub.replace('HB_', '')} |
        | Data Period | {BASE_DATA['data_period']} |
        | Annualization | {BASE_DATA['annualization_factor']:.3f}x |
        """)
    
    with col2:
        st.markdown("### Results Summary")
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | RN Annual | ${rn_annual:,.0f} |
        | VT Alpha Annual | ${vt_alpha_annual:,.0f} |
        | VT Hedge Annual | ${vt_hedge_annual:,.0f} |
        | **Total Value** | **${total_value:,.0f}** |
        | FG Revenue | ${fg_revenue:,.0f} |
        | Client Uplift | ${client_uplift:,.0f} |
        | $/MW/Year | ${value_per_mw:,.0f} |
        """)
    
    st.markdown("---")
    st.markdown("### Methodology")
    st.markdown("""
    **RN Optimization:** Captures value from optimal DA vs RT dispatch decisions based on price forecasts.
    
    **VT Alpha:** Profits from directional price predictions in the DART spread.
    
    **VT Hedge:** Protects against adverse price movements by locking in favorable positions.
    
    **Capture Rates:** Percentage of theoretical value captured based on forecast confidence levels.
    """)

# ============================================
# FOOTER
# ============================================
st.sidebar.markdown("---")
st.sidebar.markdown("*FG-GPT Value Creation Model v3.0*")
st.sidebar.caption("© 2025 FG-GPT | Confidential")
