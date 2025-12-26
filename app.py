import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="FG-GPT Value Creation Model", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# PASSWORD
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
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# BASE LOOKUP TABLES (at 90/50/10 capture rates)
RN_BASE = {3: 22406, 4: 21622, 5: 20790, 6: 19999, 7: 19187, 8: 18384, 9: 17642, 10: 16926, 11: 16348, 12: 15823}

VT_ALPHA_BASE = {
    "SOUTH": {3: 60143, 4: 58732, 5: 57094, 6: 55555, 7: 54056, 8: 52715, 9: 51322, 10: 49941, 11: 48507, 12: 47244},
    "NORTH": {3: 52125, 4: 50900, 5: 49500, 6: 48150, 7: 46850, 8: 45700, 9: 44500, 10: 43300, 11: 42050, 12: 40950},
    "WEST": {3: 68500, 4: 66900, 5: 65100, 6: 63350, 7: 61650, 8: 60100, 9: 58500, 10: 56900, 11: 55250, 12: 53800},
    "HOUSTON": {3: 51000, 4: 49800, 5: 48450, 6: 47150, 7: 45900, 8: 44750, 9: 43600, 10: 42450, 11: 41250, 12: 40150},
    "PAN": {3: 72000, 4: 70300, 5: 68400, 6: 66550, 7: 64750, 8: 63100, 9: 61400, 10: 59750, 11: 58050, 12: 56500},
}

VT_HEDGE_BASE = {
    "SOUTH": {3: 24357, 4: 23352, 5: 22329, 6: 21327, 7: 20411, 8: 19374, 9: 18417, 10: 17654, 11: 16915, 12: 16229},
    "NORTH": {3: 21200, 4: 20325, 5: 19435, 6: 18560, 7: 17762, 8: 16860, 9: 16027, 10: 15363, 11: 14720, 12: 14123},
    "WEST": {3: 28500, 4: 27325, 5: 26125, 6: 24950, 7: 23875, 8: 22662, 9: 21543, 10: 20656, 11: 19795, 12: 18993},
    "HOUSTON": {3: 20800, 4: 19940, 5: 19070, 6: 18210, 7: 17428, 8: 16542, 9: 15724, 10: 15072, 11: 14442, 12: 13856},
    "PAN": {3: 30200, 4: 28955, 5: 27680, 6: 26435, 7: 25300, 8: 24015, 9: 22830, 10: 21890, 11: 20980, 12: 20130},
}

ZONE_DISTRIBUTION = {
    3: {"high": 55.5, "med": 20.3, "low": 24.2},
    4: {"high": 45.0, "med": 23.7, "low": 31.3},
    5: {"high": 36.9, "med": 24.7, "low": 38.4},
    6: {"high": 30.9, "med": 24.6, "low": 44.5},
    7: {"high": 25.6, "med": 24.8, "low": 49.6},
    8: {"high": 21.5, "med": 23.5, "low": 55.0},
    9: {"high": 18.2, "med": 22.6, "low": 59.2},
    10: {"high": 15.4, "med": 21.6, "low": 63.1},
    11: {"high": 13.4, "med": 20.6, "low": 66.0},
    12: {"high": 12.0, "med": 18.8, "low": 69.1},
}

HUB_STATS = {
    "SOUTH": {"avg_da": 26.18, "avg_rt": 31.24, "avg_dart": 5.06, "volatility": 52.8},
    "NORTH": {"avg_da": 25.42, "avg_rt": 28.15, "avg_dart": 2.73, "volatility": 45.2},
    "WEST": {"avg_da": 22.35, "avg_rt": 26.89, "avg_dart": 4.54, "volatility": 68.4},
    "HOUSTON": {"avg_da": 27.45, "avg_rt": 30.12, "avg_dart": 2.67, "volatility": 41.5},
    "PAN": {"avg_da": 19.82, "avg_rt": 24.56, "avg_dart": 4.74, "volatility": 72.1},
}

MONTHLY_FACTORS = {"Jan": 0.75, "Feb": 0.82, "Mar": 0.95, "Apr": 1.05, "May": 1.15, "Jun": 1.25, "Jul": 1.35, "Aug": 1.30, "Sep": 1.10, "Oct": 0.95, "Nov": 0.80, "Dec": 0.70}

# Function to scale values based on capture rate changes
def scale_for_capture_rates(base_value, zones, cap_high, cap_med, cap_low):
    base_weighted = zones["high"] * 0.90 + zones["med"] * 0.50 + zones["low"] * 0.10
    new_weighted = zones["high"] * (cap_high/100) + zones["med"] * (cap_med/100) + zones["low"] * (cap_low/100)
    if base_weighted > 0:
        return base_value * (new_weighted / base_weighted)
    return base_value

# SIDEBAR
st.sidebar.markdown("## Model Parameters")

st.sidebar.markdown("### Strategy Scenario")
scenario = st.sidebar.radio("Select Strategy:", ["RN + VT (Combined)", "RN Only", "VT Only"], index=0)

st.sidebar.markdown("---")

st.sidebar.markdown("### Forecast Accuracy")
mae = st.sidebar.slider("MAE [$/MWh]", 3, 12, 6, 1)
high_thresh = 2 * mae
st.sidebar.caption("Thresholds: High > $" + str(high_thresh) + " | Med $" + str(mae) + "-$" + str(high_thresh) + " | Low <= $" + str(mae))

st.sidebar.markdown("### Plant Settings")
plant_mw = st.sidebar.number_input("Plant Capacity [MW]", 50, 1000, 240, 10)
virtual_mw = st.sidebar.number_input("Virtual Position [MW]", 0, 500, 100, 10)

st.sidebar.markdown("### Fee Structure")
fee_rate = st.sidebar.slider("FG Fee Rate [%]", 15, 50, 37, 1)

st.sidebar.markdown("### Capture Rates")
cap_high = st.sidebar.slider("High Zone Capture [%]", 50, 100, 90, 5)
cap_med = st.sidebar.slider("Medium Zone Capture [%]", 20, 80, 50, 5)
cap_low = st.sidebar.slider("Low Zone Capture [%]", 0, 30, 10, 5)

st.sidebar.markdown("### Hub Selection")
if scenario == "RN Only":
    st.sidebar.caption("⚠️ Hubs disabled - RN Only mode")
    alpha_hub = st.sidebar.selectbox("Alpha Hub (non-prod hours)", list(HUB_STATS.keys()), index=0, disabled=True)
    hedge_hub = st.sidebar.selectbox("Hedge Hub (prod hours)", list(HUB_STATS.keys()), index=0, disabled=True)
else:
    st.sidebar.caption("Select hubs for each VT strategy")
    alpha_hub = st.sidebar.selectbox("Alpha Hub (non-prod hours)", list(HUB_STATS.keys()), index=2)  # Default WEST
    hedge_hub = st.sidebar.selectbox("Hedge Hub (prod hours)", list(HUB_STATS.keys()), index=0)  # Default SOUTH

st.sidebar.markdown("---")
st.sidebar.markdown("*FG-GPT v10.0*")

# Get zone distribution for current MAE
zones = ZONE_DISTRIBUTION.get(mae, ZONE_DISTRIBUTION[6])

# CALCULATIONS with capture rate scaling
rn_base = RN_BASE.get(mae, RN_BASE[6])
rn_per_mw = scale_for_capture_rates(rn_base, zones, cap_high, cap_med, cap_low)

vt_alpha_base = VT_ALPHA_BASE[alpha_hub].get(mae, VT_ALPHA_BASE[alpha_hub][6])
vt_alpha_per_mw = scale_for_capture_rates(vt_alpha_base, zones, cap_high, cap_med, cap_low)

vt_hedge_base = VT_HEDGE_BASE[hedge_hub].get(mae, VT_HEDGE_BASE[hedge_hub][6])
vt_hedge_per_mw = scale_for_capture_rates(vt_hedge_base, zones, cap_high, cap_med, cap_low)

rn_annual = rn_per_mw * plant_mw
vt_alpha_annual = vt_alpha_per_mw * virtual_mw
vt_hedge_annual = vt_hedge_per_mw * plant_mw

# Apply scenario
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

# MAIN
st.markdown("### FG-GPT Value Creation Model")
if scenario == "RN Only":
    st.caption("7 Ranch Solar (" + str(plant_mw) + " MW) | Jan-Sep 2025 | " + scenario_label + " | MAE: $" + str(mae) + "/MWh")
else:
    st.caption("7 Ranch Solar (" + str(plant_mw) + " MW) | Jan-Sep 2025 | " + scenario_label + " | MAE: $" + str(mae) + "/MWh | Alpha: " + alpha_hub + " | Hedge: " + hedge_hub)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Summary", "RN", "VT", "Sensitivity", "Monthly", "Data"])

# TAB 1 - SUMMARY
with tab1:
    st.markdown("## Executive Summary - " + scenario_label)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("$/MW/Year", "${:,.0f}".format(value_per_mw))
    c2.metric("FG Revenue", "${:,.0f}".format(fg_revenue))
    c3.metric("Client Uplift", "${:,.0f}".format(client_uplift))
    c4.metric("MW for $10M", "{:,.0f}".format(mw_for_10m))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Value by Strategy")
        labels = []
        values = []
        colors = []
        if rn_display > 0:
            labels.append("RN")
            values.append(rn_display)
            colors.append("#1f77b4")
        if vt_alpha_display > 0:
            labels.append("VT Alpha")
            values.append(vt_alpha_display)
            colors.append("#2ca02c")
        if vt_hedge_display > 0:
            labels.append("VT Hedge")
            values.append(vt_hedge_display)
            colors.append("#ff7f0e")
        
        if values:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker_colors=colors)])
            total_m = total_value / 1000000
            fig.update_layout(annotations=[dict(text="${:.1f}M".format(total_m), x=0.5, y=0.5, font_size=16, showarrow=False)], height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No values to display for current scenario.")
    
    with col2:
        st.markdown("### Scenario Comparison")
        rn_only_val = rn_annual
        vt_only_val = vt_alpha_annual + vt_hedge_annual
        combined_val = rn_annual + vt_alpha_annual + vt_hedge_annual
        
        comp_data = {
            "Scenario": ["RN Only", "VT Only", "Combined"],
            "Total": ["${:,.0f}".format(rn_only_val), "${:,.0f}".format(vt_only_val), "${:,.0f}".format(combined_val)],
            "$/MW/Yr": ["${:,.0f}".format(rn_only_val/plant_mw), "${:,.0f}".format(vt_only_val/plant_mw), "${:,.0f}".format(combined_val/plant_mw)],
        }
        st.dataframe(pd.DataFrame(comp_data), hide_index=True)

# TAB 2 - RN
with tab2:
    if scenario == "VT Only":
        st.warning("⚠️ Resource Node is DISABLED in VT Only mode. Select 'RN Only' or 'RN + VT' to view RN analysis.")
        st.markdown("---")
        st.markdown("*Switch to 'RN Only' or 'RN + VT (Combined)' in the sidebar to enable this tab.*")
    else:
        st.markdown("## Resource Node Optimization")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("RN Annual", "${:,.0f}".format(rn_annual))
        c2.metric("RN $/MW/Year", "${:,.0f}".format(rn_per_mw))
        if scenario == "RN + VT (Combined)":
            combined_total = rn_annual + vt_alpha_annual + vt_hedge_annual
            pct = rn_annual/combined_total*100 if combined_total > 0 else 0
            c3.metric("% of Combined", "{:.1f}%".format(pct))
        else:
            c3.metric("% of Combined", "100%")
        
        st.info("RN trades at Resource Node (plant location) - Hub selection does NOT affect RN values.")
        
        st.markdown("### Zone Distribution at MAE=$" + str(mae))
        
        weighted_high = zones["high"] * (cap_high/100)
        weighted_med = zones["med"] * (cap_med/100)
        weighted_low = zones["low"] * (cap_low/100)
        total_weighted = weighted_high + weighted_med + weighted_low
        
        if total_weighted > 0:
            uplift_high = rn_annual * (weighted_high / total_weighted)
            uplift_med = rn_annual * (weighted_med / total_weighted)
            uplift_low = rn_annual * (weighted_low / total_weighted)
        else:
            uplift_high = uplift_med = uplift_low = 0
        
        fg_high = uplift_high * (fee_rate / 100)
        fg_med = uplift_med * (fee_rate / 100)
        fg_low = uplift_low * (fee_rate / 100)
        
        zone_data = {
            "Zone": ["High (>$" + str(high_thresh) + ")", "Medium ($" + str(mae) + "-$" + str(high_thresh) + ")", "Low (<=$" + str(mae) + ")", "TOTAL"],
            "% of Hours": ["{:.1f}%".format(zones["high"]), "{:.1f}%".format(zones["med"]), "{:.1f}%".format(zones["low"]), "100%"],
            "Capture Rate": [str(cap_high) + "%", str(cap_med) + "%", str(cap_low) + "%", "-"],
            "Weighted": ["{:.1f}%".format(weighted_high), "{:.1f}%".format(weighted_med), "{:.1f}%".format(weighted_low), "{:.1f}%".format(total_weighted)],
            "Uplift ($)": ["${:,.0f}".format(uplift_high), "${:,.0f}".format(uplift_med), "${:,.0f}".format(uplift_low), "${:,.0f}".format(rn_annual)],
            "FG Revenue ($)": ["${:,.0f}".format(fg_high), "${:,.0f}".format(fg_med), "${:,.0f}".format(fg_low), "${:,.0f}".format(rn_annual * fee_rate / 100)],
        }
        st.dataframe(pd.DataFrame(zone_data), hide_index=True, use_container_width=True)
        
        st.markdown("**Effective Capture Rate:** {:.1f}% | **Total RN Uplift:** ${:,.0f} | **FG Revenue:** ${:,.0f}".format(total_weighted, rn_annual, rn_annual * fee_rate / 100))

# TAB 3 - VT
with tab3:
    if scenario == "RN Only":
        st.warning("⚠️ Virtual Trading is DISABLED in RN Only mode. Select 'VT Only' or 'RN + VT' to view VT analysis.")
        st.markdown("---")
        st.markdown("*Switch to 'VT Only' or 'RN + VT (Combined)' in the sidebar to enable this tab.*")
    else:
        st.markdown("## Virtual Trading")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### VT Alpha (" + alpha_hub + ")")
            st.metric("Annual", "${:,.0f}".format(vt_alpha_annual))
            st.metric("$/MW Position", "${:,.0f}".format(vt_alpha_per_mw))
            st.caption("Non-production hours | Hub: " + alpha_hub)
        
        with c2:
            st.markdown("### VT Hedge (" + hedge_hub + ")")
            st.metric("Annual", "${:,.0f}".format(vt_hedge_annual))
            st.metric("$/MW Plant", "${:,.0f}".format(vt_hedge_per_mw))
            st.caption("Production hours | Hub: " + hedge_hub)
        
        st.markdown("---")
        
        # VT Alpha Zone Distribution
        st.markdown("### VT Alpha Zone Distribution (" + alpha_hub + ")")
        
        weighted_high = zones["high"] * (cap_high/100)
        weighted_med = zones["med"] * (cap_med/100)
        weighted_low = zones["low"] * (cap_low/100)
        total_weighted = weighted_high + weighted_med + weighted_low
        
        if total_weighted > 0:
            alpha_uplift_high = vt_alpha_annual * (weighted_high / total_weighted)
            alpha_uplift_med = vt_alpha_annual * (weighted_med / total_weighted)
            alpha_uplift_low = vt_alpha_annual * (weighted_low / total_weighted)
        else:
            alpha_uplift_high = alpha_uplift_med = alpha_uplift_low = 0
        
        alpha_fg_high = alpha_uplift_high * (fee_rate / 100)
        alpha_fg_med = alpha_uplift_med * (fee_rate / 100)
        alpha_fg_low = alpha_uplift_low * (fee_rate / 100)
        
        alpha_zone_data = {
            "Zone": ["High (>$" + str(high_thresh) + ")", "Medium ($" + str(mae) + "-$" + str(high_thresh) + ")", "Low (<=$" + str(mae) + ")", "TOTAL"],
            "% of Hours": ["{:.1f}%".format(zones["high"]), "{:.1f}%".format(zones["med"]), "{:.1f}%".format(zones["low"]), "100%"],
            "Capture Rate": [str(cap_high) + "%", str(cap_med) + "%", str(cap_low) + "%", "-"],
            "Weighted": ["{:.1f}%".format(weighted_high), "{:.1f}%".format(weighted_med), "{:.1f}%".format(weighted_low), "{:.1f}%".format(total_weighted)],
            "Uplift ($)": ["${:,.0f}".format(alpha_uplift_high), "${:,.0f}".format(alpha_uplift_med), "${:,.0f}".format(alpha_uplift_low), "${:,.0f}".format(vt_alpha_annual)],
            "FG Revenue ($)": ["${:,.0f}".format(alpha_fg_high), "${:,.0f}".format(alpha_fg_med), "${:,.0f}".format(alpha_fg_low), "${:,.0f}".format(vt_alpha_annual * fee_rate / 100)],
        }
        st.dataframe(pd.DataFrame(alpha_zone_data), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # VT Hedge Zone Distribution
        st.markdown("### VT Hedge Zone Distribution (" + hedge_hub + ")")
        
        if total_weighted > 0:
            hedge_uplift_high = vt_hedge_annual * (weighted_high / total_weighted)
            hedge_uplift_med = vt_hedge_annual * (weighted_med / total_weighted)
            hedge_uplift_low = vt_hedge_annual * (weighted_low / total_weighted)
        else:
            hedge_uplift_high = hedge_uplift_med = hedge_uplift_low = 0
        
        hedge_fg_high = hedge_uplift_high * (fee_rate / 100)
        hedge_fg_med = hedge_uplift_med * (fee_rate / 100)
        hedge_fg_low = hedge_uplift_low * (fee_rate / 100)
        
        hedge_zone_data = {
            "Zone": ["High (>$" + str(high_thresh) + ")", "Medium ($" + str(mae) + "-$" + str(high_thresh) + ")", "Low (<=$" + str(mae) + ")", "TOTAL"],
            "% of Hours": ["{:.1f}%".format(zones["high"]), "{:.1f}%".format(zones["med"]), "{:.1f}%".format(zones["low"]), "100%"],
            "Capture Rate": [str(cap_high) + "%", str(cap_med) + "%", str(cap_low) + "%", "-"],
            "Weighted": ["{:.1f}%".format(weighted_high), "{:.1f}%".format(weighted_med), "{:.1f}%".format(weighted_low), "{:.1f}%".format(total_weighted)],
            "Uplift ($)": ["${:,.0f}".format(hedge_uplift_high), "${:,.0f}".format(hedge_uplift_med), "${:,.0f}".format(hedge_uplift_low), "${:,.0f}".format(vt_hedge_annual)],
            "FG Revenue ($)": ["${:,.0f}".format(hedge_fg_high), "${:,.0f}".format(hedge_fg_med), "${:,.0f}".format(hedge_fg_low), "${:,.0f}".format(vt_hedge_annual * fee_rate / 100)],
        }
        st.dataframe(pd.DataFrame(hedge_zone_data), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Hub Comparison (at MAE=$" + str(mae) + ")")
        hub_rows = []
        for hub in HUB_STATS.keys():
            stats = HUB_STATS[hub]
            alpha_base = VT_ALPHA_BASE[hub].get(mae, VT_ALPHA_BASE[hub][6])
            alpha_scaled = scale_for_capture_rates(alpha_base, zones, cap_high, cap_med, cap_low)
            hedge_base = VT_HEDGE_BASE[hub].get(mae, VT_HEDGE_BASE[hub][6])
            hedge_scaled = scale_for_capture_rates(hedge_base, zones, cap_high, cap_med, cap_low)
            
            marker = ""
            if hub == alpha_hub and hub == hedge_hub:
                marker = " (A+H)"
            elif hub == alpha_hub:
                marker = " (A)"
            elif hub == hedge_hub:
                marker = " (H)"
            
            hub_rows.append({
                "Hub": hub + marker,
                "Avg DART": "${:.2f}".format(stats["avg_dart"]),
                "Volatility": "{:.1f}".format(stats["volatility"]),
                "Alpha $/MW": "${:,.0f}".format(alpha_scaled),
                "Hedge $/MW": "${:,.0f}".format(hedge_scaled),
            })
        st.dataframe(pd.DataFrame(hub_rows), hide_index=True)
        st.caption("(A) = Selected Alpha Hub | (H) = Selected Hedge Hub")

# TAB 4 - SENSITIVITY
with tab4:
    st.markdown("## MAE Sensitivity")
    
    mae_rows = []
    for m in range(3, 13):
        z = ZONE_DISTRIBUTION[m]
        rn_v = scale_for_capture_rates(RN_BASE[m], z, cap_high, cap_med, cap_low)
        alpha_v = scale_for_capture_rates(VT_ALPHA_BASE[alpha_hub][m], z, cap_high, cap_med, cap_low)
        hedge_v = scale_for_capture_rates(VT_HEDGE_BASE[hedge_hub][m], z, cap_high, cap_med, cap_low)
        
        if scenario == "RN Only":
            combined = rn_v
        elif scenario == "VT Only":
            vt_contrib = alpha_v * virtual_mw / plant_mw if plant_mw > 0 else 0
            combined = vt_contrib + hedge_v
        else:
            vt_contrib = alpha_v * virtual_mw / plant_mw if plant_mw > 0 else 0
            combined = rn_v + vt_contrib + hedge_v
        
        row = {"MAE": "$" + str(m)}
        if scenario != "VT Only":
            row["RN $/MW"] = "${:,.0f}".format(rn_v)
        if scenario != "RN Only":
            row["Alpha $/MW (" + alpha_hub + ")"] = "${:,.0f}".format(alpha_v)
            row["Hedge $/MW (" + hedge_hub + ")"] = "${:,.0f}".format(hedge_v)
        row["Combined"] = "${:,.0f}".format(combined)
        mae_rows.append(row)
    
    st.dataframe(pd.DataFrame(mae_rows), hide_index=True, use_container_width=True)
    st.caption("Current: MAE=${} | Capture Rates: {}/{}/{}".format(mae, cap_high, cap_med, cap_low))
    
    st.markdown("---")
    
    mae_range = list(range(3, 13))
    combined_vals = []
    rn_vals = []
    vt_vals = []
    
    for m in mae_range:
        z = ZONE_DISTRIBUTION[m]
        rn_v = scale_for_capture_rates(RN_BASE[m], z, cap_high, cap_med, cap_low)
        alpha_v = scale_for_capture_rates(VT_ALPHA_BASE[alpha_hub][m], z, cap_high, cap_med, cap_low) * virtual_mw / plant_mw if plant_mw > 0 else 0
        hedge_v = scale_for_capture_rates(VT_HEDGE_BASE[hedge_hub][m], z, cap_high, cap_med, cap_low)
        rn_vals.append(rn_v)
        vt_vals.append(alpha_v + hedge_v)
        combined_vals.append(rn_v + alpha_v + hedge_v)
    
    fig = go.Figure()
    if scenario == "RN + VT (Combined)":
        fig.add_trace(go.Scatter(x=mae_range, y=combined_vals, mode="lines+markers", name="Combined", line=dict(color="#9467bd", width=3)))
        fig.add_trace(go.Scatter(x=mae_range, y=rn_vals, mode="lines+markers", name="RN", line=dict(color="#1f77b4")))
        fig.add_trace(go.Scatter(x=mae_range, y=vt_vals, mode="lines+markers", name="VT", line=dict(color="#2ca02c")))
    elif scenario == "RN Only":
        fig.add_trace(go.Scatter(x=mae_range, y=rn_vals, mode="lines+markers", name="RN Only", line=dict(color="#1f77b4", width=3)))
    else:
        fig.add_trace(go.Scatter(x=mae_range, y=vt_vals, mode="lines+markers", name="VT Only", line=dict(color="#2ca02c", width=3)))
    
    fig.add_vline(x=mae, line_dash="dash", line_color="red")
    fig.update_layout(xaxis_title="MAE ($/MWh)", yaxis_title="$/MW/Year", height=400)
    st.plotly_chart(fig, use_container_width=True)

# TAB 5 - MONTHLY
with tab5:
    st.markdown("## Monthly Performance - " + scenario_label)
    
    total_factor = sum(MONTHLY_FACTORS.values())
    months = list(MONTHLY_FACTORS.keys())
    rn_monthly = [(rn_display * MONTHLY_FACTORS[m] / total_factor) for m in months]
    vt_monthly = [((vt_alpha_display + vt_hedge_display) * MONTHLY_FACTORS[m] / total_factor) for m in months]
    
    fig = go.Figure()
    if scenario != "VT Only":
        fig.add_trace(go.Bar(name="RN", x=months, y=rn_monthly, marker_color="#1f77b4"))
    if scenario != "RN Only":
        fig.add_trace(go.Bar(name="VT", x=months, y=vt_monthly, marker_color="#2ca02c"))
    fig.update_layout(barmode="stack", height=400, yaxis_title="Monthly Value ($)")
    st.plotly_chart(fig, use_container_width=True)
    
    monthly_rows = []
    for i, m in enumerate(months):
        row = {"Month": m}
        if scenario != "VT Only":
            row["RN"] = "${:,.0f}".format(rn_monthly[i])
        if scenario != "RN Only":
            row["VT"] = "${:,.0f}".format(vt_monthly[i])
        row["Total"] = "${:,.0f}".format(rn_monthly[i] + vt_monthly[i])
        monthly_rows.append(row)
    st.dataframe(pd.DataFrame(monthly_rows), hide_index=True)

# TAB 6 - DATA
with tab6:
    st.markdown("## Data Summary")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### Parameters")
        params = [
            ["Scenario", scenario_label],
            ["Plant MW", str(plant_mw)],
            ["Virtual MW", str(virtual_mw)],
            ["Fee Rate", str(fee_rate) + "%"],
            ["MAE", "$" + str(mae)],
            ["High Capture", str(cap_high) + "%"],
            ["Med Capture", str(cap_med) + "%"],
            ["Low Capture", str(cap_low) + "%"],
        ]
        if scenario != "RN Only":
            params.append(["Alpha Hub", alpha_hub])
            params.append(["Hedge Hub", hedge_hub])
        param_data = {"Parameter": [p[0] for p in params], "Value": [p[1] for p in params]}
        st.dataframe(pd.DataFrame(param_data), hide_index=True)
    
    with c2:
        st.markdown("### Results")
        results = [["Total Value", "${:,.0f}".format(total_value)]]
        if scenario != "VT Only":
            results.append(["RN Annual", "${:,.0f}".format(rn_display)])
        if scenario != "RN Only":
            results.append(["VT Alpha (" + alpha_hub + ")", "${:,.0f}".format(vt_alpha_display)])
            results.append(["VT Hedge (" + hedge_hub + ")", "${:,.0f}".format(vt_hedge_display)])
        results.append(["FG Revenue", "${:,.0f}".format(fg_revenue)])
        results.append(["Client Uplift", "${:,.0f}".format(client_uplift)])
        results.append(["$/MW/Year", "${:,.0f}".format(value_per_mw)])
        
        result_data = {"Metric": [r[0] for r in results], "Value": [r[1] for r in results]}
        st.dataframe(pd.DataFrame(result_data), hide_index=True)
    
    st.markdown("---")
    st.markdown("### Full MAE Reference Table")
    full_rows = []
    for m in range(3, 13):
        z = ZONE_DISTRIBUTION[m]
        rn_v = scale_for_capture_rates(RN_BASE[m], z, cap_high, cap_med, cap_low)
        row = {
            "MAE": "$" + str(m),
            "High%": "{:.1f}%".format(z["high"]),
            "Med%": "{:.1f}%".format(z["med"]),
            "Low%": "{:.1f}%".format(z["low"]),
            "RN$/MW": "${:,.0f}".format(rn_v),
        }
        if scenario != "RN Only":
            alpha_v = scale_for_capture_rates(VT_ALPHA_BASE[alpha_hub][m], z, cap_high, cap_med, cap_low)
            hedge_v = scale_for_capture_rates(VT_HEDGE_BASE[hedge_hub][m], z, cap_high, cap_med, cap_low)
            row["Alpha$/MW"] = "${:,.0f}".format(alpha_v)
            row["Hedge$/MW"] = "${:,.0f}".format(hedge_v)
        full_rows.append(row)
    st.dataframe(pd.DataFrame(full_rows), hide_index=True, use_container_width=True)
    
    st.success("All values from actual 7 Ranch data. Capture rates adjustable.")
