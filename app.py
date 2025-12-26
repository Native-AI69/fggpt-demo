import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# PAGE CONFIG - MUST BE FIRST
st.set_page_config(page_title="FG-GPT Value Creation Model", page_icon="⚡", layout="wide")

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
# LOOKUP TABLES - FROM EXCEL MODEL
# ============================================

RN_VALUE_PER_MW = {
    3: 22406, 4: 21622, 5: 20790, 6: 19999, 7: 19187,
    8: 18384, 9: 17642, 10: 16926, 11: 16348, 12: 15823,
}

VT_ALPHA_PER_MW = {
    3: 60143, 4: 58732, 5: 57094, 6: 55555, 7: 54056,
    8: 52715, 9: 51322, 10: 49941, 11: 48507, 12: 47244,
}

VT_HEDGE_PER_MW = {
    3: 24357, 4: 23352, 5: 22329, 6: 21327, 7: 20411,
    8: 19374, 9: 18417, 10: 17654, 11: 16915, 12: 16229,
}

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

MONTHLY_FACTORS = {
    'Jan': 0.75, 'Feb': 0.82, 'Mar': 0.95, 'Apr': 1.05,
    'May': 1.15, 'Jun': 1.25, 'Jul': 1.35, 'Aug': 1.30,
    'Sep': 1.10, 'Oct': 0.95, 'Nov': 0.80, 'Dec': 0.70,
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

# ============================================
# CALCULATIONS
# ============================================

rn_per_mw = RN_VALUE_PER_MW.get(mae, RN_VALUE_PER_MW[6])
vt_alpha_per_mw = VT_ALPHA_PER_MW.get(mae, VT_ALPHA_PER_MW[6])
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

# ============================================
# MAIN CONTENT
# ============================================

st.markdown("### ⚡ FG-GPT Value Creation Model")
st.caption(f"7 Ranch Solar ({plant_mw} MW) | Jan-Sep 2025 | **{scenario_label}** | **MAE: ${mae}/MWh**")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "📈 RN", "💹 VT", "🎚️ Sensitivity"])

with tab1:
    st.markdown(f"## 📊 Executive Summary — *{scenario_label}*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("$/MW/Year", f"${value_per_mw:,.0f}")
    c2.metric("FG Revenue", f"${fg_revenue:,.0f}")
    c3.metric("Client Uplift", f"${client_uplift:,.0f}")
    c4.metric("MW for $10M", f"{mw_for_10m:,.0f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Value by Strategy")
        labels = []
        values = []
        colors = []
        if rn_display > 0:
            labels.append('RN')
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
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Scenario Comparison")
        comp_data = {
            'Scenario': ['RN Only', 'VT Only', 'Combined'],
            'Total': [f'${rn_annual:,.0f}', f'${vt_alpha_annual+vt_hedge_annual:,.0f}', f'${rn_annual+vt_alpha_annual+vt_hedge_annual:,.0f}'],
            '$/MW/Yr': [f'${rn_annual/plant_mw:,.0f}', f'${(vt_alpha_annual+vt_hedge_annual)/plant_mw:,.0f}', f'${(rn_annual+vt_alpha_annual+vt_hedge_annual)/plant_mw:,.0f}'],
        }
        st.dataframe(pd.DataFrame(comp_data), hide_index=True)

with tab2:
    st.markdown("## 📈 Resource Node")
    c1, c2 = st.columns(2)
    c1.metric("RN Annual", f"${rn_annual:,.0f}")
    c2.metric("RN $/MW/Year", f"${rn_per_mw:,.0f}")
    
    zones = ZONE_DISTRIBUTION.get(mae, ZONE_DISTRIBUTION[6])
    st.markdown(f"### Zones at MAE=${mae}")
    st.markdown(f"- High (>${2*mae}): {zones['high']}% → 90% capture")
    st.markdown(f"- Med (${mae}-${2*mae}): {zones['med']}% → 50% capture")
    st.markdown(f"- Low (≤${mae}): {zones['low']}% → 10% capture")

with tab3:
    st.markdown("## 💹 Virtual Trading")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### VT Alpha")
        st.metric("Annual", f"${vt_alpha_annual:,.0f}")
        st.metric("$/MW Position", f"${vt_alpha_per_mw:,.0f}")
    with c2:
        st.markdown("### VT Hedge")
        st.metric("Annual", f"${vt_hedge_annual:,.0f}")
        st.metric("$/MW Plant", f"${vt_hedge_per_mw:,.0f}")

with tab4:
    st.markdown("## 🎚️ MAE Sensitivity")
    
    table_data = []
    for m in range(3, 13):
        rn = RN_VALUE_PER_MW[m]
        alpha = VT_ALPHA_PER_MW[m]
        hedge = VT_HEDGE_PER_MW[m]
        table_data.append({
            'MAE': f'${m}',
            'RN $/MW': f'${rn:,}',
            'Alpha $/MW': f'${alpha:,}',
            'Hedge $/MW': f'${hedge:,}',
        })
    st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)
    st.info(f"📍 Current: MAE=${mae} → {value_per_mw:,.0f}/MW/Year")

st.sidebar.markdown("---")
st.sidebar.caption("v7.0 | © 2025 FG-GPT")
