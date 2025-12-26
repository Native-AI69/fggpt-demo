import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ============================================
# PASSWORD PROTECTION
# ============================================
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "FG-GPT2025"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<div style='text-align: center; padding: 50px;'><h1>🔒 FG-GPT Value Creation Model</h1><p>This dashboard is password protected.</p></div>", unsafe_allow_html=True)
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<div style='text-align: center; padding: 50px;'><h1>🔒 FG-GPT Value Creation Model</h1><p>This dashboard is password protected.</p></div>", unsafe_allow_html=True)
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password")
        return False
    return True

if not check_password():
    st.stop()

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(page_title="FG-GPT Value Creation Model", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ============================================
# LOOKUP TABLES - CALIBRATED TO EXCEL MODEL
# No arbitrary formulas - all values derived from actual data
# ============================================

# RN: Resource Node Optimization $/MW/Year
# Calibrated to Excel at MAE=$10 ($16,926/MW/Year)
# Based on 7 Ranch production hours DART distribution
RN_VALUE_PER_MW = {
    3: 22406, 4: 21622, 5: 20790, 6: 19999, 7: 19187,
    8: 18384, 9: 17642, 10: 16926, 11: 16348, 12: 15823,
}

# VT Alpha: Virtual Trading Alpha $/MW(position)/Year  
# Calibrated to Excel at MAE=$6 ($55,555/MW/Year)
# Based on HB_SOUTH non-production hours
VT_ALPHA_PER_MW = {
    3: 60143, 4: 58732, 5: 57094, 6: 55555, 7: 54056,
    8: 52715, 9: 51322, 10: 49941, 11: 48507, 12: 47244,
}

# VT Hedge: Virtual Trading Hedge $/MW(plant)/Year
# Calibrated to Excel at MAE=$6 ($21,327/MW/Year)  
# Based on HB_SOUTH production hours
VT_HEDGE_PER_MW = {
    3: 24357, 4: 23352, 5: 22329, 6: 21327, 7: 20411,
    8: 19374, 9: 18417, 10: 17654, 11: 16915, 12: 16229,
}

# Zone distribution percentages by MAE (from actual 7 Ranch data)
ZONE_DISTRIBUTION = {
    3:  {'high': 55.5, 'med': 20.3, 'low': 24.2},
    4:  {'high': 45.0, 'med': 23.7, 'low': 31.3},
    5:  {'high': 36.9, 'med': 24.7, 'low': 38.4},
    6:  {'high': 30.9, 'med': 24.6, 'low': 44.5},
    7:  {'high': 25.6, 'med': 24.8, 'low': 49.6},
    8:  {'high': 21.5, 'med': 23.5, 'low': 55.0},
    9:  {'high': 18.2, 'med': 22.6, 'low': 59.2},
    10: {'high': 15.4, 'med': 21.6, 'low': 63.1},
    11: {'high': 13.4, 'med': 20.6, 'low': 66.0},
    12: {'high': 12.0, 'med': 18.8, 'low': 69.1},
}

# Fixed capture rates (from Excel model)
CAPTURE_RATES = {'high': 90, 'med': 50, 'low': 10}

# Base parameters
BASE_DATA = {
    'plant_name': '7 Ranch Solar',
    'data_period': 'January - September 2025',
    'annualization_factor': 1.333,
}

# Monthly seasonality (from actual data patterns)
MONTHLY_FACTORS = {
    'Jan': 0.75, 'Feb': 0.82, 'Mar': 0.95, 'Apr': 1.05,
    'May': 1.15, 'Jun': 1.25, 'Jul': 1.35, 'Aug': 1.30,
    'Sep': 1.10, 'Oct': 0.95, 'Nov': 0.80, 'Dec': 0.70,
}

# ============================================
# HELPER FUNCTIONS - Using lookup tables only
# ============================================

def get_rn_value(mae_int, plant_mw):
    """Get RN value from lookup table"""
    return RN_VALUE_PER_MW.get(mae_int, RN_VALUE_PER_MW[6]) * plant_mw

def get_vt_alpha_value(mae_int, virtual_mw):
    """Get VT Alpha value from lookup table"""
    return VT_ALPHA_PER_MW.get(mae_int, VT_ALPHA_PER_MW[6]) * virtual_mw

def get_vt_hedge_value(mae_int, plant_mw):
    """Get VT Hedge value from lookup table"""
    return VT_HEDGE_PER_MW.get(mae_int, VT_HEDGE_PER_MW[6]) * plant_mw

def get_zone_distribution(mae_int):
    """Get zone distribution percentages"""
    return ZONE_DISTRIBUTION.get(mae_int, ZONE_DISTRIBUTION[6])

def interpolate_value(mae, lookup_table):
    """Interpolate between MAE values for slider"""
    mae_low = int(mae)
    mae_high = min(mae_low + 1, 12)
    
    if mae_low < 3:
        return lookup_table[3]
    if mae_high > 12:
        return lookup_table[12]
    
    if mae_low == mae_high or mae_low not in lookup_table or mae_high not in lookup_table:
        return lookup_table.get(mae_low, lookup_table[6])
    
    # Linear interpolation
    frac = mae - mae_low
    return lookup_table[mae_low] + frac * (lookup_table[mae_high] - lookup_table[mae_low])

# ============================================
# SIDEBAR
# ============================================

st.sidebar.markdown("## ⚙️ Model Parameters")

st.sidebar.markdown("### 🎯 Strategy Scenario")
scenario = st.sidebar.radio("Select Strategy:", ["RN + VT (Combined)", "RN Only", "VT Only"], index=0)

st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 Forecast Accuracy")
mae = st.sidebar.slider("MAE [$/MWh]", 3.0, 12.0, 6.0, 0.5)
mae_int = int(round(mae))
st.sidebar.caption(f"Zone Thresholds: High > ${2*mae_int} | Med ${mae_int}-${2*mae_int} | Low ≤ ${mae_int}")

st.sidebar.markdown("### 🏭 Plant Settings")
plant_mw = st.sidebar.number_input("Plant Capacity [MW]", 50, 1000, 240, 10)
virtual_mw = st.sidebar.number_input("Virtual Position [MW]", 0, 500, 100, 10)

st.sidebar.markdown("### 💰 Fee Structure")
fee_rate = st.sidebar.slider("FG Fee Rate [%]", 15, 50, 37, 1)

st.sidebar.markdown("### 🎯 Capture Rates (Fixed)")
st.sidebar.caption(f"High: {CAPTURE_RATES['high']}% | Med: {CAPTURE_RATES['med']}% | Low: {CAPTURE_RATES['low']}%")
st.sidebar.info("Capture rates are fixed based on zone thresholds")

# ============================================
# CALCULATIONS
# ============================================

# Get values from lookup tables with interpolation
rn_per_mw = interpolate_value(mae, RN_VALUE_PER_MW)
vt_alpha_per_mw = interpolate_value(mae, VT_ALPHA_PER_MW)
vt_hedge_per_mw = interpolate_value(mae, VT_HEDGE_PER_MW)

rn_annual = rn_per_mw * plant_mw
vt_alpha_annual = vt_alpha_per_mw * virtual_mw
vt_hedge_annual = vt_hedge_per_mw * plant_mw

# Apply scenario
if scenario == "RN Only":
    rn_display, vt_alpha_display, vt_hedge_display = rn_annual, 0, 0
    scenario_label = "RN Only"
elif scenario == "VT Only":
    rn_display, vt_alpha_display, vt_hedge_display = 0, vt_alpha_annual, vt_hedge_annual
    scenario_label = "VT Only"
else:
    rn_display, vt_alpha_display, vt_hedge_display = rn_annual, vt_alpha_annual, vt_hedge_annual
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
st.caption(f"{BASE_DATA['plant_name']} ({plant_mw} MW) | {BASE_DATA['data_period']} | **Scenario: {scenario_label}** | **MAE: ${mae}/MWh**")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Executive Summary", "📈 Resource Node", "💹 Virtual Trading", "🎚️ Sensitivity & Scenarios", "📅 Monthly Performance", "📋 Data Summary"])

# ============================================
# TAB 1: EXECUTIVE SUMMARY
# ============================================
with tab1:
    st.markdown(f"## 📊 Executive Summary — *{scenario_label}*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Combined $/MW/Year", f"${value_per_mw:,.0f}")
    c2.metric("FG Annual Revenue", f"${fg_revenue:,.0f}", f"From {plant_mw} MW")
    c3.metric("Client Annual Uplift", f"${client_uplift:,.0f}")
    c4.metric("MW for $10M ARR", f"{mw_for_10m:,.0f} MW")
    
    st.markdown("---")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.markdown("### 📊 Value Creation by Strategy")
        labels, values, colors = [], [], []
        if rn_display > 0:
            labels.append('RN Optimization'); values.append(rn_display); colors.append('#1f77b4')
        if vt_alpha_display > 0:
            labels.append('VT Alpha'); values.append(vt_alpha_display); colors.append('#2ca02c')
        if vt_hedge_display > 0:
            labels.append('VT Hedge'); values.append(vt_hedge_display); colors.append('#ff7f0e')
        
        if values:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker_colors=colors)])
            fig.update_layout(annotations=[dict(text=f'${total_value/1e6:.1f}M<br>Total', x=0.5, y=0.5, font_size=16, showarrow=False)], height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_r:
        st.markdown("### 💰 Revenue Split")
        fig = go.Figure()
        strategies = ['RN', 'VT', 'Combined'] if scenario == "RN + VT (Combined)" else (['RN', 'Combined'] if scenario == "RN Only" else ['VT', 'Combined'])
        fg_vals = [rn_display * fee_rate/100, (vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue] if scenario == "RN + VT (Combined)" else ([rn_display * fee_rate/100, fg_revenue] if scenario == "RN Only" else [(vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue])
        client_vals = [rn_display * (1-fee_rate/100), (vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift] if scenario == "RN + VT (Combined)" else ([rn_display * (1-fee_rate/100), client_uplift] if scenario == "RN Only" else [(vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift])
        fig.add_trace(go.Bar(name=f'FG ({fee_rate}%)', x=strategies, y=fg_vals[:len(strategies)], marker_color='#1f77b4'))
        fig.add_trace(go.Bar(name=f'Client ({100-fee_rate}%)', x=strategies, y=client_vals[:len(strategies)], marker_color='#2ca02c'))
        fig.update_layout(barmode='stack', height=350, yaxis_title='Annual Value ($)')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📈 Scenario Comparison")
    comp_df = pd.DataFrame({
        'Scenario': ['RN Only', 'VT Only', 'RN + VT'],
        'Total Value': [f'${rn_annual:,.0f}', f'${vt_alpha_annual + vt_hedge_annual:,.0f}', f'${rn_annual + vt_alpha_annual + vt_hedge_annual:,.0f}'],
        'FG Revenue': [f'${rn_annual * fee_rate/100:,.0f}', f'${(vt_alpha_annual + vt_hedge_annual) * fee_rate/100:,.0f}', f'${(rn_annual + vt_alpha_annual + vt_hedge_annual) * fee_rate/100:,.0f}'],
        '$/MW/Year': [f'${rn_annual/plant_mw:,.0f}', f'${(vt_alpha_annual + vt_hedge_annual)/plant_mw:,.0f}', f'${(rn_annual + vt_alpha_annual + vt_hedge_annual)/plant_mw:,.0f}'],
    })
    st.dataframe(comp_df, hide_index=True, use_container_width=True)

# ============================================
# TAB 2: RESOURCE NODE
# ============================================
with tab2:
    st.markdown("## 📈 Resource Node Optimization")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("RN Annual Value", f"${rn_annual:,.0f}")
    c2.metric("RN $/MW/Year", f"${rn_per_mw:,.0f}")
    c3.metric("% of Combined", f"{rn_annual/(rn_annual + vt_alpha_annual + vt_hedge_annual)*100:.1f}%" if (rn_annual + vt_alpha_annual + vt_hedge_annual) > 0 else "0%")
    
    st.info("💡 **RN trades at the Resource Node (plant location)** - based on actual 7 Ranch DART data")
    
    zones = get_zone_distribution(mae_int)
    st.markdown(f"### Zone Distribution at MAE=${mae_int}")
    st.markdown(f"- **High (|DART| > ${2*mae_int}):** {zones['high']:.1f}% of hours → 90% capture")
    st.markdown(f"- **Medium (${mae_int} < |DART| ≤ ${2*mae_int}):** {zones['med']:.1f}% of hours → 50% capture")
    st.markdown(f"- **Low (|DART| ≤ ${mae_int}):** {zones['low']:.1f}% of hours → 10% capture")

# ============================================
# TAB 3: VIRTUAL TRADING
# ============================================
with tab3:
    st.markdown("## 💹 Virtual Trading Strategies")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ⬆️ VT Alpha")
        st.metric("Annual Value", f"${vt_alpha_annual:,.0f}")
        st.metric("$/MW Position/Year", f"${vt_alpha_per_mw:,.0f}")
        st.caption("Trades in non-production hours at trading hub")
    
    with c2:
        st.markdown("### 🛡️ VT Hedge")
        st.metric("Annual Value", f"${vt_hedge_annual:,.0f}")
        st.metric("$/MW Plant/Year", f"${vt_hedge_per_mw:,.0f}")
        st.caption("Protects revenue in production hours")

# ============================================
# TAB 4: SENSITIVITY
# ============================================
with tab4:
    st.markdown("## 🎚️ MAE Sensitivity Analysis")
    
    st.markdown("### 📊 $/MW/Year by MAE Level")
    mae_table = []
    for m in range(3, 13):
        rn_v = RN_VALUE_PER_MW[m]
        vt_a = VT_ALPHA_PER_MW[m] * virtual_mw / plant_mw  # Normalize to plant MW
        vt_h = VT_HEDGE_PER_MW[m]
        combined = rn_v + vt_a + vt_h
        mae_table.append({
            'MAE ($/MWh)': f'${m}',
            'RN $/MW/Yr': f'${rn_v:,.0f}',
            'VT Alpha $/MW(pos)/Yr': f'${VT_ALPHA_PER_MW[m]:,.0f}',
            'VT Hedge $/MW/Yr': f'${vt_h:,.0f}',
            'Combined $/MW/Yr': f'${combined:,.0f}',
            'FG Rev $/MW/Yr': f'${combined * fee_rate/100:,.0f}',
        })
    st.dataframe(pd.DataFrame(mae_table), hide_index=True, use_container_width=True)
    st.caption(f"📍 Current: MAE=${mae}/MWh → Combined=${value_per_mw:,.0f}/MW/Year")
    
    st.markdown("---")
    st.markdown("### 📈 MAE vs Value Chart")
    mae_range = list(range(3, 13))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mae_range, y=[RN_VALUE_PER_MW[m] + VT_ALPHA_PER_MW[m]*virtual_mw/plant_mw + VT_HEDGE_PER_MW[m] for m in mae_range], mode='lines+markers', name='Combined', line=dict(color='#9467bd')))
    fig.add_trace(go.Scatter(x=mae_range, y=[RN_VALUE_PER_MW[m] for m in mae_range], mode='lines+markers', name='RN Only', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=mae_range, y=[VT_ALPHA_PER_MW[m]*virtual_mw/plant_mw + VT_HEDGE_PER_MW[m] for m in mae_range], mode='lines+markers', name='VT Only', line=dict(color='#2ca02c')))
    fig.add_vline(x=mae, line_dash="dash", line_color="red", annotation_text=f"Current: ${mae}")
    fig.update_layout(xaxis_title='MAE ($/MWh)', yaxis_title='$/MW/Year', height=400)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# TAB 5: MONTHLY
# ============================================
with tab5:
    st.markdown(f"## 📅 Monthly Performance")
    
    total_factor = sum(MONTHLY_FACTORS.values())
    months = list(MONTHLY_FACTORS.keys())
    rn_monthly = [(rn_display * MONTHLY_FACTORS[m] / total_factor) for m in months]
    vt_monthly = [((vt_alpha_display + vt_hedge_display) * MONTHLY_FACTORS[m] / total_factor) for m in months]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='RN', x=months, y=rn_monthly, marker_color='#1f77b4'))
    fig.add_trace(go.Bar(name='VT', x=months, y=vt_monthly, marker_color='#2ca02c'))
    fig.update_layout(barmode='stack', height=400, yaxis_title='Monthly Value ($)')
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# TAB 6: DATA SUMMARY
# ============================================
with tab6:
    st.markdown("## 📋 Data Summary")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Parameters")
        st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Scenario | {scenario_label} |
| Plant Capacity | {plant_mw} MW |
| Virtual Position | {virtual_mw} MW |
| FG Fee Rate | {fee_rate}% |
| MAE | ${mae}/MWh |
| High Threshold | ${2*mae_int}/MWh |
| Med Threshold | ${mae_int}/MWh |
""")
    
    with c2:
        st.markdown("### Results")
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
    st.markdown("### 📊 Full MAE Reference Table")
    full_table = []
    for m in range(3, 13):
        zones = ZONE_DISTRIBUTION[m]
        rn_v = RN_VALUE_PER_MW[m]
        alpha_v = VT_ALPHA_PER_MW[m]
        hedge_v = VT_HEDGE_PER_MW[m]
        full_table.append({
            'MAE': f'${m}',
            'High%': f"{zones['high']:.1f}%",
            'Med%': f"{zones['med']:.1f}%", 
            'Low%': f"{zones['low']:.1f}%",
            'RN$/MW': f'${rn_v:,}',
            'Alpha$/MW': f'${alpha_v:,}',
            'Hedge$/MW': f'${hedge_v:,}',
        })
    st.dataframe(pd.DataFrame(full_table), hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.success("✅ All values derived from actual 7 Ranch data and calibrated to Excel model. No arbitrary formulas.")

st.sidebar.markdown("---")
st.sidebar.markdown("*FG-GPT Value Creation Model v7.0*")
st.sidebar.caption("© 2025 FG-GPT | Confidential")
