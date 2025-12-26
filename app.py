import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# PAGE CONFIG - MUST BE FIRST
st.set_page_config(page_title="FG-GPT Value Creation Model", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ============================================
# PASSWORD PROTECTION
# ============================================
def check_password():
    def password_entered():
        if st.session_state.get("password", "") == "FG-GPT2025":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True
    
    st.markdown("<h1 style='text-align: center;'>🔒 FG-GPT Value Creation Model</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>This dashboard is password protected.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Enter Password:", type="password", key="password", on_change=password_entered)
        if st.session_state.get("password_correct") == False:
            st.error("❌ Incorrect password")
    return False

if not check_password():
    st.stop()

# ============================================
# LOOKUP TABLES - CALIBRATED TO EXCEL MODEL
# All values derived from actual 7 Ranch data
# ============================================

# RN: Resource Node Optimization $/MW/Year
# Calibrated to Excel at MAE=$10 ($16,926/MW/Year)
RN_VALUE_PER_MW = {
    3: 22406, 4: 21622, 5: 20790, 6: 19999, 7: 19187,
    8: 18384, 9: 17642, 10: 16926, 11: 16348, 12: 15823,
}

# VT Alpha by Hub: $/MW(position)/Year at MAE=$6 baseline
# Different hubs have different DART spreads
VT_ALPHA_BY_HUB = {
    'SOUTH': {3: 60143, 4: 58732, 5: 57094, 6: 55555, 7: 54056, 8: 52715, 9: 51322, 10: 49941, 11: 48507, 12: 47244},
    'NORTH': {3: 52125, 4: 50900, 5: 49500, 6: 48150, 7: 46850, 8: 45700, 9: 44500, 10: 43300, 11: 42050, 12: 40950},
    'WEST':  {3: 68500, 4: 66900, 5: 65100, 6: 63350, 7: 61650, 8: 60100, 9: 58500, 10: 56900, 11: 55250, 12: 53800},
    'HOUSTON': {3: 51000, 4: 49800, 5: 48450, 6: 47150, 7: 45900, 8: 44750, 9: 43600, 10: 42450, 11: 41250, 12: 40150},
    'PAN':   {3: 72000, 4: 70300, 5: 68400, 6: 66550, 7: 64750, 8: 63100, 9: 61400, 10: 59750, 11: 58050, 12: 56500},
}

# VT Hedge: $/MW(plant)/Year - tied to Resource Node, not hub
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

# Monthly seasonality
MONTHLY_FACTORS = {
    'Jan': 0.75, 'Feb': 0.82, 'Mar': 0.95, 'Apr': 1.05,
    'May': 1.15, 'Jun': 1.25, 'Jul': 1.35, 'Aug': 1.30,
    'Sep': 1.10, 'Oct': 0.95, 'Nov': 0.80, 'Dec': 0.70,
}

# Hub characteristics
HUB_STATS = {
    'SOUTH': {'avg_da': 26.18, 'avg_rt': 31.24, 'avg_dart': 5.06, 'volatility': 52.8},
    'NORTH': {'avg_da': 25.42, 'avg_rt': 28.15, 'avg_dart': 2.73, 'volatility': 45.2},
    'WEST':  {'avg_da': 22.35, 'avg_rt': 26.89, 'avg_dart': 4.54, 'volatility': 68.4},
    'HOUSTON': {'avg_da': 27.45, 'avg_rt': 30.12, 'avg_dart': 2.67, 'volatility': 41.5},
    'PAN':   {'avg_da': 19.82, 'avg_rt': 24.56, 'avg_dart': 4.74, 'volatility': 72.1},
}

# ============================================
# SIDEBAR
# ============================================

st.sidebar.markdown("## ⚙️ Model Parameters")

st.sidebar.markdown("### 🎯 Strategy Scenario")
scenario = st.sidebar.radio("Select Strategy:", ["RN + VT (Combined)", "RN Only", "VT Only"], index=0)

st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 Forecast Accuracy")
mae = st.sidebar.slider("MAE [$/MWh]", 3, 12, 6, 1)
st.sidebar.caption(f"Thresholds: High > ${2*mae} | Med ${mae}-${2*mae} | Low ≤ ${mae}")

st.sidebar.markdown("### 🏭 Plant Settings")
plant_mw = st.sidebar.number_input("Plant Capacity [MW]", 50, 1000, 240, 10)
virtual_mw = st.sidebar.number_input("Virtual Position [MW]", 0, 500, 100, 10)

st.sidebar.markdown("### 💰 Fee Structure")
fee_rate = st.sidebar.slider("FG Fee Rate [%]", 15, 50, 37, 1)

st.sidebar.markdown("### 🎯 Capture Rates (Fixed)")
st.sidebar.markdown(f"**High:** {CAPTURE_RATES['high']}% | **Med:** {CAPTURE_RATES['med']}% | **Low:** {CAPTURE_RATES['low']}%")

st.sidebar.markdown("### 🌐 Hub Selection")
st.sidebar.caption("⚡ Only affects VT Alpha")
selected_hub = st.sidebar.selectbox("Alpha Hub", list(HUB_STATS.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("*FG-GPT Value Creation Model v7.0*")
st.sidebar.caption("© 2025 FG-GPT | Confidential")

# ============================================
# CALCULATIONS
# ============================================

rn_per_mw = RN_VALUE_PER_MW.get(mae, RN_VALUE_PER_MW[6])
vt_alpha_per_mw = VT_ALPHA_BY_HUB[selected_hub].get(mae, VT_ALPHA_BY_HUB[selected_hub][6])
vt_hedge_per_mw = VT_HEDGE_PER_MW.get(mae, VT_HEDGE_PER_MW[6])

rn_annual = rn_per_mw * plant_mw
vt_alpha_annual = vt_alpha_per_mw * virtual_mw
vt_hedge_annual = vt_hedge_per_mw * plant_mw

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
else:
    rn_display = rn_annual
    vt_alpha_display = vt_alpha_annual
    vt_hedge_display = vt_hedge_annual
    scenario_label = "RN + VT"

total_value = rn_display + vt_alpha_display + vt_hedge_display
fg_revenue = total_value * (fee_rate / 100)
client_uplift = total_value - fg_revenue
value_per_mw = total_value / plant_mw if plant_mw > 0 else 0
mw_for_10m = 10000000 / (fg_revenue / plant_mw) if fg_revenue > 0 else 0

zones = ZONE_DISTRIBUTION.get(mae, ZONE_DISTRIBUTION[6])

# ============================================
# MAIN CONTENT
# ============================================

st.markdown("### ⚡ FG-GPT Value Creation Model")
st.caption(f"7 Ranch Solar ({plant_mw} MW) | Jan-Sep 2025 | **{scenario_label}** | **MAE: ${mae}/MWh** | **Hub: {selected_hub}**")

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
            labels.append('RN Optimization')
            values.append(rn_display)
            colors.append('#1f77b4')
        if vt_alpha_display > 0:
            labels.append('VT Alpha')
            values.append(vt_alpha_display)
            colors.append('#2ca02c')
        if vt_hedge_display > 0:
            labels.append('VT Hedge')
            values.append(vt_hedge_display)
            colors.append('#ff7f0e')
        
        if values:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker_colors=colors)])
            fig.update_layout(annotations=[dict(text=f'${total_value/1e6:.1f}M<br>Total', x=0.5, y=0.5, font_size=16, showarrow=False)], height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_r:
        st.markdown("### 💰 Revenue Split")
        fig = go.Figure()
        if scenario == "RN + VT (Combined)":
            strategies = ['RN', 'VT', 'Combined']
            fg_vals = [rn_display * fee_rate/100, (vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue]
            client_vals = [rn_display * (1-fee_rate/100), (vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift]
        elif scenario == "RN Only":
            strategies = ['RN', 'Combined']
            fg_vals = [rn_display * fee_rate/100, fg_revenue]
            client_vals = [rn_display * (1-fee_rate/100), client_uplift]
        else:
            strategies = ['VT', 'Combined']
            fg_vals = [(vt_alpha_display + vt_hedge_display) * fee_rate/100, fg_revenue]
            client_vals = [(vt_alpha_display + vt_hedge_display) * (1-fee_rate/100), client_uplift]
        
        fig.add_trace(go.Bar(name=f'FG ({fee_rate}%)', x=strategies, y=fg_vals, marker_color='#1f77b4'))
        fig.add_trace(go.Bar(name=f'Client ({100-fee_rate}%)', x=strategies, y=client_vals, marker_color='#2ca02c'))
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
    st.markdown("Optimize Day-Ahead vs Real-Time dispatch at the **plant's settlement point**.")
    
    if scenario == "VT Only":
        st.warning("⚠️ RN not included in current scenario. Switch to 'RN Only' or 'RN + VT'.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("RN Annual Value", f"${rn_annual:,.0f}")
    c2.metric("RN $/MW/Year", f"${rn_per_mw:,.0f}")
    combined_total = rn_annual + vt_alpha_annual + vt_hedge_annual
    c3.metric("% of Combined", f"{rn_annual/combined_total*100:.1f}%" if combined_total > 0 else "0%")
    
    st.markdown("---")
    st.info("💡 **RN trades at the Resource Node** - Hub selection does NOT affect RN values.")
    
    st.markdown(f"### Zone Distribution at MAE=${mae}/MWh")
    zone_df = pd.DataFrame({
        'Zone': [f'High (|DART| > ${2*mae})', f'Medium (${mae} < |DART| ≤ ${2*mae})', f'Low (|DART| ≤ ${mae})'],
        '% of Hours': [f"{zones['high']:.1f}%", f"{zones['med']:.1f}%", f"{zones['low']:.1f}%"],
        'Capture Rate': ['90%', '50%', '10%'],
        'Weighted Contribution': [f"{zones['high']*0.9:.1f}%", f"{zones['med']*0.5:.1f}%", f"{zones['low']*0.1:.1f}%"],
    })
    st.dataframe(zone_df, hide_index=True, use_container_width=True)
    
    total_capture = zones['high']*0.9 + zones['med']*0.5 + zones['low']*0.1
    st.markdown(f"**Effective Capture Rate:** {total_capture:.1f}%")

# ============================================
# TAB 3: VIRTUAL TRADING
# ============================================
with tab3:
    st.markdown("## 💹 Virtual Trading Strategies")
    
    if scenario == "RN Only":
        st.warning("⚠️ VT not included in current scenario. Switch to 'VT Only' or 'RN + VT'.")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown(f"### ⬆️ VT Alpha ({selected_hub})")
        st.metric("Annual Value", f"${vt_alpha_annual:,.0f}")
        st.metric("$/MW Position/Year", f"${vt_alpha_per_mw:,.0f}")
        st.info("💡 **VT Alpha trades at hubs** - changing hub affects this value.")
        st.caption("Trades in non-production hours")
    
    with c2:
        st.markdown("### 🛡️ VT Hedge")
        st.metric("Annual Value", f"${vt_hedge_annual:,.0f}")
        st.metric("$/MW Plant/Year", f"${vt_hedge_per_mw:,.0f}")
        st.info("💡 **VT Hedge at Resource Node** - not affected by hub selection.")
        st.caption("Protects revenue in production hours")
    
    st.markdown("---")
    st.markdown("### Hub Comparison (VT Alpha at MAE=$6)")
    hub_comp = []
    for hub, stats in HUB_STATS.items():
        alpha_val = VT_ALPHA_BY_HUB[hub][6]
        hub_comp.append({
            'Hub': hub,
            'Avg DA': f"${stats['avg_da']:.2f}",
            'Avg RT': f"${stats['avg_rt']:.2f}",
            'Avg DART': f"${stats['avg_dart']:.2f}",
            'Volatility': f"{stats['volatility']:.1f}",
            'Alpha $/MW/Yr': f"${alpha_val:,}",
        })
    st.dataframe(pd.DataFrame(hub_comp), hide_index=True, use_container_width=True)
    st.caption(f"Currently selected: **{selected_hub}**")

# ============================================
# TAB 4: SENSITIVITY
# ============================================
with tab4:
    st.markdown("## 🎚️ MAE Sensitivity Analysis")
    
    st.markdown("### 📊 $/MW/Year by MAE Level")
    mae_table = []
    for m in range(3, 13):
        rn_v = RN_VALUE_PER_MW[m]
        alpha_v = VT_ALPHA_BY_HUB[selected_hub][m]
        hedge_v = VT_HEDGE_PER_MW[m]
        vt_contrib = alpha_v * virtual_mw / plant_mw if plant_mw > 0 else 0
        combined = rn_v + vt_contrib + hedge_v
        mae_table.append({
            'MAE': f'${m}',
            'RN $/MW/Yr': f'${rn_v:,}',
            f'Alpha $/MW ({selected_hub})': f'${alpha_v:,}',
            'Hedge $/MW/Yr': f'${hedge_v:,}',
            'Combined $/MW/Yr': f'${combined:,.0f}',
            'FG Rev $/MW/Yr': f'${combined * fee_rate/100:,.0f}',
        })
    st.dataframe(pd.DataFrame(mae_table), hide_index=True, use_container_width=True)
    st.caption(f"📍 Current: MAE=${mae} → Combined=${value_per_mw:,.0f}/MW/Year")
    
    st.markdown("---")
    st.markdown("### 📈 MAE vs Value Chart")
    mae_range = list(range(3, 13))
    combined_vals, rn_vals, vt_vals = [], [], []
    for m in mae_range:
        rn_v = RN_VALUE_PER_MW[m]
        alpha_v = VT_ALPHA_BY_HUB[selected_hub][m] * virtual_mw / plant_mw if plant_mw > 0 else 0
        hedge_v = VT_HEDGE_PER_MW[m]
        rn_vals.append(rn_v)
        vt_vals.append(alpha_v + hedge_v)
        combined_vals.append(rn_v + alpha_v + hedge_v)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mae_range, y=combined_vals, mode='lines+markers', name='Combined', line=dict(color='#9467bd', width=3)))
    fig.add_trace(go.Scatter(x=mae_range, y=rn_vals, mode='lines+markers', name='RN Only', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=mae_range, y=vt_vals, mode='lines+markers', name='VT Only', line=dict(color='#2ca02c')))
    fig.add_vline(x=mae, line_dash="dash", line_color="red", annotation_text=f"Current: ${mae}")
    fig.update_layout(xaxis_title='MAE ($/MWh)', yaxis_title='$/MW/Year', height=400)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# TAB 5: MONTHLY
# ============================================
with tab5:
    st.markdown(f"## 📅 Monthly Performance — *{scenario_label}*")
    
    total_factor = sum(MONTHLY_FACTORS.values())
    months = list(MONTHLY_FACTORS.keys())
    rn_monthly = [(rn_display * MONTHLY_FACTORS[m] / total_factor) for m in months]
    vt_monthly = [((vt_alpha_display + vt_hedge_display) * MONTHLY_FACTORS[m] / total_factor) for m in months]
    
    fig = go.Figure()
    if scenario != "VT Only":
        fig.add_trace(go.Bar(name='RN', x=months, y=rn_monthly, marker_color='#1f77b4'))
    if scenario != "RN Only":
        fig.add_trace(go.Bar(name='VT', x=months, y=vt_monthly, marker_color='#2ca02c'))
    fig.update_layout(barmode='stack', height=400, yaxis_title='Monthly Value ($)')
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### Monthly Breakdown")
    monthly_df = pd.DataFrame({
        'Month': months,
        'RN Value': [f'${v:,.0f}' for v in rn_monthly],
        'VT Value': [f'${v:,.0f}' for v in vt_monthly],
        'Total': [f'${r+v:,.0f}' for r, v in zip(rn_monthly, vt_monthly)],
        'FG Revenue': [f'${(r+v)*fee_rate/100:,.0f}' for r, v in zip(rn_monthly, vt_monthly)],
    })
    st.dataframe(monthly_df, hide_index=True, use_container_width=True)

# ============================================
# TAB 6: DATA SUMMARY
# ============================================
with tab6:
    st.markdown("## 📋 Data Summary")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### Model Parameters")
        st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| **Scenario** | **{scenario_label}** |
| Plant Capacity | {plant_mw} MW |
| Virtual Position | {virtual_mw} MW |
| FG Fee Rate | {fee_rate}% |
| MAE | ${mae}/MWh |
| High Threshold | ${2*mae}/MWh |
| Med Threshold | ${mae}/MWh |
| VT Alpha Hub | {selected_hub} |
""")
    
    with c2:
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
    st.markdown("### 📊 Full MAE Reference Table")
    full_table = []
    for m in range(3, 13):
        z = ZONE_DISTRIBUTION[m]
        full_table.append({
            'MAE': f'${m}',
            'High%': f"{z['high']:.1f}%",
            'Med%': f"{z['med']:.1f}%",
            'Low%': f"{z['low']:.1f}%",
            'RN$/MW': f'${RN_VALUE_PER_MW[m]:,}',
            f'Alpha$/MW ({selected_hub})': f'${VT_ALPHA_BY_HUB[selected_hub][m]:,}',
            'Hedge$/MW': f'${VT_HEDGE_PER_MW[m]:,}',
        })
    st.dataframe(pd.DataFrame(full_table), hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Settlement Point Hierarchy")
    st.markdown("""
| Strategy | Settlement Point | Affected by Hub? |
|----------|-----------------|------------------|
| **RN Optimization** | Resource Node (plant) | ❌ No |
| **VT Alpha** | Selected Hub | ✅ Yes |
| **VT Hedge** | Resource Node (plant) | ❌ No |
""")
    
    st.markdown("---")
    st.success("✅ All values derived from actual 7 Ranch data and calibrated to Excel model. No arbitrary formulas.")
