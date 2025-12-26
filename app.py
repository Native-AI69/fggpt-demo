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

# Resource Node characteristics (fixed - based on plant location)
# This is where RN optimization happens - at the plant's settlement point
RESOURCE_NODE_STATS = {
    'avg_da': 24.50,
    'avg_rt': 27.80,
    'avg_dart': 3.30,
    'volatility': 55.0,  # Fixed for the resource node
}

# Hub price statistics for VT Alpha trading (aggregated - not raw hourly data)
# VT Alpha trades at hubs, NOT at the resource node
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

def calculate_rn_value(plant_mw, mae, capture_rates):
    """Calculate RN optimization value - uses Resource Node stats (fixed), NOT hub"""
    base_value = BASE_VALUE_PER_MW['rn_optimization']
    
    # MAE adjustment (lower MAE = higher value)
    mae_factor = (10 - mae) / 4  # Normalized around MAE=6
    
    # Resource Node volatility (FIXED - doesn't change with hub selection)
    vol_factor = RESOURCE_NODE_STATS['volatility'] / 50
    
    # Capture rate weighted average
    weighted_capture = (
        capture_rates['high'] * SIGNAL_DISTRIBUTION['high_confidence_pct'] +
        capture_rates['med'] * SIGNAL_DISTRIBUTION['med_confidence_pct'] +
        capture_rates['low'] * SIGNAL_DISTRIBUTION['low_confidence_pct']
    ) / 100
    
    adjusted_value = base_value * mae_factor * vol_factor * weighted_capture * 2
    return plant_mw * adjusted_value

def calculate_vt_alpha(position_mw, mae, hub_stats, capture_rates):
    """Calculate VT Alpha value - uses selected Hub stats (this SHOULD change with hub)"""
    base_value = BASE_VALUE_PER_MW['vt_alpha']
    
    mae_factor = (10 - mae) / 4
    spread_factor = hub_stats['avg_dart'] / 4  # Hub DART spread matters here
    
    weighted_capture = (
        capture_rates['high'] * SIGNAL_DISTRIBUTION['high_confidence_pct'] +
        capture_rates['med'] * SIGNAL_DISTRIBUTION['med_confidence_pct'] * 0.5 +
        capture_rates['low'] * SIGNAL_DISTRIBUTION['low_confidence_pct'] * 0.1
    ) / 100
    
    adjusted_value = base_value * mae_factor * spread_factor * weighted_capture * 3
    return position_mw * adjusted_value

def calculate_vt_hedge(plant_mw, mae, capture_rates):
    """Calculate VT Hedge value - hedges plant production, uses Resource Node stats (fixed)"""
    base_value = BASE_VALUE_PER_MW['vt_hedge']
    
    mae_factor = (10 - mae) / 4
    # Hedge is at the resource node level, not hub
    vol_factor = RESOURCE_NODE_STATS['volatility'] / 50
    
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

# SCENARIO SELECTOR
st.sidebar.markdown("### 🎯 Strategy Scenario")
scenario = st.sidebar.radio(
    "Select Strategy:",
    ["RN + VT (Combined)", "RN Only", "VT Only"],
    index=0,
    help="Choose which strategies to include in the analysis"
)

st.sidebar.markdown("---")

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
st.sidebar.caption("⚡ Only affects VT Alpha (hub trading)")
hub_options = list(HUB_STATS.keys())
selected_hub = st.sidebar.selectbox("Alpha Hub (VT Only)", hub_options, 
                                     format_func=lambda x: x.replace('HB_', ''))

hub_stats = HUB_STATS[selected_hub]

# ============================================
# CALCULATIONS
# ============================================

# Calculate values - NOTE: RN and VT Hedge don't use hub_stats anymore
rn_value = calculate_rn_value(plant_mw, mae, capture_rates)
vt_alpha_value = calculate_vt_alpha(virtual_mw, mae, hub_stats, capture_rates)  # Only this uses hub
vt_hedge_value = calculate_vt_hedge(plant_mw, mae, capture_rates)

# Annualize
rn_annual = rn_value * BASE_DATA['annualization_factor']
vt_alpha_annual = vt_alpha_value * BASE_DATA['annualization_factor']
vt_hedge_annual = vt_hedge_value * BASE_DATA['annualization_factor']

# Apply scenario filter
if scenario == "RN Only":
    rn_display = rn_annual
    vt_alpha_display = 0
    vt_hedge_display = 0
    scenario_label = "RN Only"
elif scenario == "VT Only":
    rn_display = 0
    vt_alpha_display = vt_alpha_annual
    vt_hedge_display = vt_hedge_annual
    scenario_label = "VT Only"
else:  # Combined
    rn_display = rn_annual
    vt_alpha_display = vt_alpha_annual
    vt_hedge_display = vt_hedge_annual
    scenario_label = "RN + VT"

total_value = rn_display + vt_alpha_display + vt_hedge_display
fg_revenue = total_value * (fee_rate / 100)
client_uplift = total_value - fg_revenue

value_per_mw = total_value / plant_mw if plant_mw > 0 else 0
mw_for_10m = 10_000_000 / (fg_revenue / plant_mw) if fg_revenue > 0 else 0

# ============================================
# MAIN CONTENT
# ============================================

st.markdown(f"### ⚡ FG-GPT Value Creation Model")
st.caption(f"{BASE_DATA['plant_name']} ({plant_mw} MW) | {BASE_DATA['data_period']} | Annualized Projections | **Scenario: {scenario_label}**")

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
    st.markdown(f"## 📊 Executive Summary — *{scenario_label}*")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Combined $/MW/Year", f"${value_per_mw:,.0f}")
    with col2:
        st.metric("FG Annual Revenue", f"${fg_revenue:,.0f}", f"From {plant_mw} MW")
    with col3:
        st.metric("Client Annual Uplift", f"${client_uplift:,.0f}", f"+{(client_uplift/(total_value-client_uplift))*100:.0f}% revenue" if total_value > client_uplift and client_uplift > 0 else "")
    with col4:
        st.metric("MW for $10M ARR", f"{mw_for_10m:,.0f} MW", "Target capacity")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📊 Value Creation by Strategy")
        
        # Only show non-zero values in pie
        labels = []
        values = []
        colors = []
        
        if rn_display > 0:
            labels.append('RN Optimization')
            values.append(rn_display)
            colors.append('#1f77b4')
        if vt_alpha_display > 0:
            labels.append('Alpha Trading')
            values.append(vt_alpha_display)
            colors.append('#2ca02c')
        if vt_hedge_display > 0:
            labels.append('Hedge Trading')
            values.append(vt_hedge_display)
            colors.append('#ff7f0e')
        
        if values:
            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker_colors=colors
            )])
            fig_pie.update_layout(
                annotations=[dict(text=f'${total_value/1e6:.1f}M<br>Total', x=0.5, y=0.5, font_size=16, showarrow=False)],
                height=350,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Select a scenario to see value breakdown")
    
    with col_right:
        st.markdown("### 💰 Revenue Split")
        
        fig_bar = go.Figure()
        
        # Build bars based on scenario
        if scenario == "RN Only":
            strategies = ['RN', 'Combined']
            fg_values = [rn_display * fee_rate/100, fg_revenue]
            client_values = [rn_display * (1-fee_rate/100), client_uplift]
        elif scenario == "VT Only":
            strategies = ['VT Strategy', 'Combined']
            fg_values = [(vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue]
            client_values = [(vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift]
        else:
            strategies = ['RN', 'VT Strategy', 'Combined']
            fg_values = [rn_display * fee_rate/100, (vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue]
            client_values = [rn_display * (1-fee_rate/100), (vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift]
        
        fig_bar.add_trace(go.Bar(name=f'FG ({fee_rate}%)', x=strategies, y=fg_values, marker_color='#1f77b4'))
        fig_bar.add_trace(go.Bar(name=f'Client ({100-fee_rate}%)', x=strategies, y=client_values, marker_color='#2ca02c'))
        
        fig_bar.update_layout(barmode='stack', height=350, yaxis_title='Annual Value ($)')
        st.plotly_chart(fig_bar, use_container_width=True)

    # Scenario comparison table
    st.markdown("---")
    st.markdown("### 📈 Scenario Comparison")
    
    # Calculate all scenarios for comparison
    rn_only_total = rn_annual
    vt_only_total = vt_alpha_annual + vt_hedge_annual
    combined_total = rn_annual + vt_alpha_annual + vt_hedge_annual
    
    comparison_df = pd.DataFrame({
        'Scenario': ['RN Only', 'VT Only', 'RN + VT (Combined)'],
        'Total Value': [f'${rn_only_total:,.0f}', f'${vt_only_total:,.0f}', f'${combined_total:,.0f}'],
        'FG Revenue': [f'${rn_only_total * fee_rate/100:,.0f}', f'${vt_only_total * fee_rate/100:,.0f}', f'${combined_total * fee_rate/100:,.0f}'],
        'Client Uplift': [f'${rn_only_total * (1-fee_rate/100):,.0f}', f'${vt_only_total * (1-fee_rate/100):,.0f}', f'${combined_total * (1-fee_rate/100):,.0f}'],
        '$/MW/Year': [f'${rn_only_total/plant_mw:,.0f}', f'${vt_only_total/plant_mw:,.0f}', f'${combined_total/plant_mw:,.0f}'],
    })
    
    st.dataframe(comparison_df, hide_index=True, use_container_width=True)

# ============================================
# TAB 2: RESOURCE NODE
# ============================================
with tab2:
    st.markdown("## 📈 Resource Node Optimization")
    st.markdown("Optimize Day-Ahead vs Real-Time dispatch decisions at the **plant's settlement point**.")
    
    if scenario == "VT Only":
        st.warning("⚠️ RN is not included in current scenario. Switch to 'RN Only' or 'RN + VT' to see RN values.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("RN Annual Value", f"${rn_annual:,.0f}")
    with col2:
        st.metric("RN $/MW/Year", f"${rn_annual/plant_mw:,.0f}")
    with col3:
        pct = (rn_annual/(rn_annual + vt_alpha_annual + vt_hedge_annual)*100) if (rn_annual + vt_alpha_annual + vt_hedge_annual) > 0 else 0
        st.metric("% of Combined Value", f"{pct:.1f}%")
    
    st.markdown("---")
    
    st.info("💡 **RN trades at the Resource Node (plant location)** - Hub selection does NOT affect RN values.")
    
    st.markdown("### Resource Node Statistics")
    rn_df = pd.DataFrame({
        'Metric': ['Avg DA Price', 'Avg RT Price', 'Avg DART Spread', 'Volatility'],
        'Value': [f"${RESOURCE_NODE_STATS['avg_da']:.2f}/MWh", 
                  f"${RESOURCE_NODE_STATS['avg_rt']:.2f}/MWh",
                  f"${RESOURCE_NODE_STATS['avg_dart']:.2f}/MWh",
                  f"{RESOURCE_NODE_STATS['volatility']:.1f}"]
    })
    st.dataframe(rn_df, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### How RN Optimization Works")
    st.markdown("""
    1. **Forecast DA vs RT prices** for each hour at the Resource Node
    2. **If RT > DA predicted:** Reduce DA commitment, sell more in RT
    3. **If DA > RT predicted:** Maximize DA commitment, reduce RT exposure
    4. **Capture the spread** between markets at your settlement point
    """)

# ============================================
# TAB 3: VIRTUAL TRADING
# ============================================
with tab3:
    st.markdown("## 💹 Virtual Trading Strategies")
    
    if scenario == "RN Only":
        st.warning("⚠️ VT is not included in current scenario. Switch to 'VT Only' or 'RN + VT' to see VT values.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⬆️ VT Alpha")
        st.markdown(f"*Trading at **{selected_hub.replace('HB_', '')}** hub*")
        st.metric("Annual Value", f"${vt_alpha_annual:,.0f}")
        st.metric("$/MW Position/Year", f"${vt_alpha_annual/virtual_mw:,.0f}" if virtual_mw > 0 else "$0")
        
        st.info("💡 **VT Alpha trades at hubs** - changing hub selection affects this value.")
        
        st.markdown("""
        **How it works:**
        - RT > DA → Virtual demand (buy DA, sell RT)
        - DA > RT → Virtual supply (sell DA, buy RT)
        - Profit if forecast is correct
        """)
    
    with col2:
        st.markdown("### 🛡️ VT Hedge")
        st.markdown("*Hedging at Resource Node*")
        st.metric("Annual Value", f"${vt_hedge_annual:,.0f}")
        st.metric("$/MW Hedged/Year", f"${vt_hedge_annual/plant_mw:,.0f}")
        
        st.info("💡 **VT Hedge protects plant revenue** - tied to Resource Node, not hub.")
        
        st.markdown("""
        **How it works:**
        - Lock in revenue protection
        - When RT predicted to fall below DA
        - Insurance for your solar production
        """)
    
    st.markdown("---")
    
    # Hub comparison for VT Alpha
    st.markdown("### Hub Comparison (VT Alpha)")
    st.caption("VT Alpha value changes based on hub selection")
    hub_df = pd.DataFrame(HUB_STATS).T
    hub_df.columns = ['Avg DA ($/MWh)', 'Avg RT ($/MWh)', 'Avg DART Spread', 'Volatility']
    hub_df.index = [h.replace('HB_', '') for h in hub_df.index]
    
    # Highlight selected hub
    st.dataframe(hub_df.style.format('${:.2f}'), use_container_width=True)
    st.caption(f"Currently selected: **{selected_hub.replace('HB_', '')}**")
    
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
    mae_values_rn = []
    mae_values_vt = []
    mae_values_combined = []
    
    for m in mae_range:
        rv = calculate_rn_value(plant_mw, m, capture_rates) * BASE_DATA['annualization_factor']
        va = calculate_vt_alpha(virtual_mw, m, hub_stats, capture_rates) * BASE_DATA['annualization_factor']
        vh = calculate_vt_hedge(plant_mw, m, capture_rates) * BASE_DATA['annualization_factor']
        mae_values_rn.append(rv)
        mae_values_vt.append(va + vh)
        mae_values_combined.append(rv + va + vh)
    
    fig_mae = go.Figure()
    fig_mae.add_trace(go.Scatter(x=mae_range, y=mae_values_combined, mode='lines+markers', name='RN + VT', line=dict(color='#9467bd')))
    fig_mae.add_trace(go.Scatter(x=mae_range, y=mae_values_rn, mode='lines+markers', name='RN Only', line=dict(color='#1f77b4')))
    fig_mae.add_trace(go.Scatter(x=mae_range, y=mae_values_vt, mode='lines+markers', name='VT Only', line=dict(color='#2ca02c')))
    fig_mae.add_vline(x=mae, line_dash="dash", line_color="red", annotation_text=f"Current MAE: {mae}")
    fig_mae.update_layout(
        xaxis_title='MAE ($/MWh)',
        yaxis_title='Annual Value ($)',
        height=400
    )
    st.plotly_chart(fig_mae, use_container_width=True)
    
    st.markdown("### Capacity Sensitivity")
    cap_range = np.arange(100, 1050, 50)
    cap_rn = []
    cap_vt = []
    cap_combined = []
    
    for c in cap_range:
        rv = calculate_rn_value(c, mae, capture_rates) * BASE_DATA['annualization_factor']
        va = calculate_vt_alpha(virtual_mw * c / plant_mw, mae, hub_stats, capture_rates) * BASE_DATA['annualization_factor']
        vh = calculate_vt_hedge(c, mae, capture_rates) * BASE_DATA['annualization_factor']
        cap_rn.append(rv * fee_rate / 100)
        cap_vt.append((va + vh) * fee_rate / 100)
        cap_combined.append((rv + va + vh) * fee_rate / 100)
    
    fig_cap = go.Figure()
    fig_cap.add_trace(go.Scatter(x=cap_range, y=cap_combined, mode='lines', name='RN + VT', line=dict(color='#9467bd')))
    fig_cap.add_trace(go.Scatter(x=cap_range, y=cap_rn, mode='lines', name='RN Only', line=dict(color='#1f77b4')))
    fig_cap.add_trace(go.Scatter(x=cap_range, y=cap_vt, mode='lines', name='VT Only', line=dict(color='#2ca02c')))
    fig_cap.add_hline(y=10_000_000, line_dash="dash", line_color="green", annotation_text="$10M ARR Target")
    fig_cap.update_layout(
        xaxis_title='Plant Capacity (MW)',
        yaxis_title='FG Annual Revenue ($)',
        height=400
    )
    st.plotly_chart(fig_cap, use_container_width=True)

# ============================================
# TAB 5: MONTHLY PERFORMANCE
# ============================================
with tab5:
    st.markdown(f"## 📅 Monthly Performance — *{scenario_label}*")
    
    monthly_rn = calculate_monthly_breakdown(rn_display)
    monthly_vt = calculate_monthly_breakdown(vt_alpha_display + vt_hedge_display)
    
    months = list(MONTHLY_FACTORS.keys())
    rn_vals = [monthly_rn[m] for m in months]
    vt_vals = [monthly_vt[m] for m in months]
    
    fig_monthly = go.Figure()
    if scenario != "VT Only":
        fig_monthly.add_trace(go.Bar(name='RN', x=months, y=rn_vals, marker_color='#1f77b4'))
    if scenario != "RN Only":
        fig_monthly.add_trace(go.Bar(name='VT', x=months, y=vt_vals, marker_color='#2ca02c'))
    fig_monthly.update_layout(barmode='stack', height=400, yaxis_title='Monthly Value ($)')
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Monthly table
    st.markdown("### Monthly Breakdown")
    monthly_df = pd.DataFrame({
        'Month': months,
        'RN Value': [f'${v:,.0f}' for v in rn_vals],
        'VT Value': [f'${v:,.0f}' for v in vt_vals],
        'Total': [f'${r + v:,.0f}' for r, v in zip(rn_vals, vt_vals)],
        'FG Revenue': [f'${(r + v) * fee_rate/100:,.0f}' for r, v in zip(rn_vals, vt_vals)],
    })
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
        | **Scenario** | **{scenario_label}** |
        | Plant Capacity | {plant_mw} MW |
        | Virtual Position | {virtual_mw} MW |
        | FG Fee Rate | {fee_rate}% |
        | MAE | ${mae}/MWh |
        | VT Alpha Hub | {selected_hub.replace('HB_', '')} |
        | Data Period | {BASE_DATA['data_period']} |
        | Annualization | {BASE_DATA['annualization_factor']:.3f}x |
        """)
    
    with col2:
        st.markdown("### Results Summary")
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | RN Annual | ${rn_display:,.0f} |
        | VT Alpha Annual | ${vt_alpha_display:,.0f} |
        | VT Hedge Annual | ${vt_hedge_display:,.0f} |
        | **Total Value** | **${total_value:,.0f}** |
        | FG Revenue | ${fg_revenue:,.0f} |
        | Client Uplift | ${client_uplift:,.0f} |
        | $/MW/Year | ${value_per_mw:,.0f} |
        """)
    
    st.markdown("---")
    st.markdown("### Settlement Point Hierarchy")
    st.markdown("""
    | Strategy | Settlement Point | Affected by Hub Selection? |
    |----------|-----------------|---------------------------|
    | **RN Optimization** | Resource Node (plant location) | ❌ No |
    | **VT Alpha** | Selected Hub | ✅ Yes |
    | **VT Hedge** | Resource Node (plant location) | ❌ No |
    """)
    
    st.markdown("---")
    st.markdown("### Methodology")
    st.markdown("""
    **RN Optimization:** Captures value from optimal DA vs RT dispatch decisions at the plant's Resource Node.
    
    **VT Alpha:** Profits from directional price predictions at a trading hub (selected above).
    
    **VT Hedge:** Protects plant revenue against adverse price movements at the Resource Node.
    
    **Capture Rates:** Percentage of theoretical value captured based on forecast confidence levels.
    """)

# ============================================
# FOOTER
# ============================================
st.sidebar.markdown("---")
st.sidebar.markdown("*FG-GPT Value Creation Model v5.0*")
st.sidebar.caption("© 2025 FG-GPT | Confidential")
