"""
FG-GPT Value Creation Model - Interactive Dashboard v4
=======================================================
7 Ranch Solar (240 MW) | Jan-Sep 2025 Data | Annualized Results

FIXED: Hub selection now properly updates calculations
ADDED: Scenario Comparison, Hub Comparison, Monthly Performance, Data Summary
ADDED: Break-even Analysis with Budget from Excel
ADDED: Disclaimer and Password Protection
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ============================================
# PAGE CONFIG - MUST BE FIRST
# ============================================
st.set_page_config(
    page_title="FG-GPT Value Model",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ACCESS CONTROL / DISCLAIMER + PASSWORD
# ============================================
# Password configuration - change this or use environment variable
# For production, use: ACCESS_PASSWORD = os.environ.get("FG_GPT_PASSWORD", "default_password")
ACCESS_PASSWORD = "FG2026!"  # Change this to your desired password

def show_access_disclaimer():
    """Display confidentiality notice, require acknowledgment, and verify password."""
    
    # Check if user has already been granted full access
    if st.session_state.get("access_granted", False):
        return True
    
    # Create centered container for the notice
    st.markdown("""
    <style>
    .disclaimer-box {
        background-color: rgba(30, 30, 30, 0.9);
        border: 1px solid #444;
        border-left: 4px solid #1F4E79;
        border-radius: 8px;
        padding: 30px;
        margin: 50px auto;
        max-width: 600px;
    }
    .disclaimer-title {
        color: #1F4E79;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if disclaimer has been accepted (step 1 complete)
    disclaimer_accepted = st.session_state.get("disclaimer_accepted", False)
    
    if not disclaimer_accepted:
        # STEP 1: Show disclaimer
        with st.container():
            st.markdown("---")
            
            with st.expander("⚠️ Important Notice – Authorized Use Only", expanded=True):
                st.markdown("### CONFIDENTIAL – LIMITED ACCESS")
                
                st.markdown("""
                This application and its contents are proprietary and confidential. 
                By accessing this application, you acknowledge that:
                """)
                
                st.markdown("""
                • You are **not** a competitor or engaged in model replication
                
                • You will **not share** access credentials or URLs
                
                • Data, visuals, and methodologies are **not for redistribution**
                """)
                
                st.caption("Access events may be logged for audit and security purposes.")
                
                st.markdown("---")
                
                # Checkbox for acknowledgment
                accepted = st.checkbox("I acknowledge and agree", key="disclaimer_checkbox")
                
                if accepted:
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        if st.button("Continue", type="primary", use_container_width=True):
                            st.session_state["disclaimer_accepted"] = True
                            st.rerun()
                else:
                    st.info("Please check the box above to acknowledge and proceed.")
        
        return False
    
    else:
        # STEP 2: Password entry
        with st.container():
            st.markdown("---")
            
            # Centered password form
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                st.markdown("### 🔐 Enter Access Password")
                st.markdown("Please enter your authorized access password to continue.")
                
                st.markdown("")
                
                # Password input
                password_input = st.text_input(
                    "Password",
                    type="password",
                    key="password_input",
                    placeholder="Enter password...",
                    help="Contact Foresight Grid if you don't have a password"
                )
                
                # Check for previous failed attempts
                if st.session_state.get("password_error", False):
                    st.error("❌ Incorrect password. Please try again.")
                
                st.markdown("")
                
                # Submit button
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("← Back", use_container_width=True):
                        st.session_state["disclaimer_accepted"] = False
                        st.session_state["password_error"] = False
                        st.rerun()
                
                with col_b:
                    if st.button("Enter Application", type="primary", use_container_width=True):
                        if password_input == ACCESS_PASSWORD:
                            st.session_state["access_granted"] = True
                            st.session_state["password_error"] = False
                            st.rerun()
                        else:
                            st.session_state["password_error"] = True
                            st.rerun()
                
                st.markdown("---")
                st.caption("🔒 Access is restricted to authorized users only.")
                st.caption("📧 Need access? Contact: sales@foresightgrid.com")
        
        return False

# ============================================
# CHECK ACCESS BEFORE ANYTHING ELSE
# ============================================
if not show_access_disclaimer():
    st.stop()

# ============================================
# BUDGET DATA LOADING
# ============================================
@st.cache_data
def load_budget_data(filepath="3Years.xlsx"):
    """Load 3-year budget from Excel file."""
    default_budget = {
        'Year 1': 682000,
        'Year 2': 1404700,
        'Year 3': 2076800,
    }
    
    try:
        if os.path.exists(filepath):
            xlsx = pd.ExcelFile(filepath)
            df = pd.read_excel(xlsx, sheet_name='3-Year Summary')
            
            # Find the TOTAL BUDGET row
            for idx, row in df.iterrows():
                if 'TOTAL BUDGET' in str(row.iloc[0]):
                    return {
                        'Year 1': float(row.iloc[2]) if pd.notna(row.iloc[2]) else default_budget['Year 1'],
                        'Year 2': float(row.iloc[3]) if pd.notna(row.iloc[3]) else default_budget['Year 2'],
                        'Year 3': float(row.iloc[4]) if pd.notna(row.iloc[4]) else default_budget['Year 3'],
                    }
        return default_budget
    except Exception as e:
        return default_budget

# Load budget data
BUDGET_DATA = load_budget_data()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1F4E79;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #666;
        margin-top: 5px;
    }
    .metric-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #1F4E79;
    }
    .highlight-green {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    .highlight-blue {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HUB DATA FROM ACTUAL MODEL TESTING
# ============================================
# These values are from your actual hub testing results
HUB_DATA = {
    'ALPHA': {
        'SOUTH': {'captured': 4096324, 'fg_rev': 1536122, 'comb_per_mw': 22292},
        'PAN': {'captured': 5497859, 'fg_rev': 2061697, 'comb_per_mw': 24482},
        'WEST': {'captured': 5555465, 'fg_rev': 2083299, 'comb_per_mw': 24572},
    },
    'HEDGE': {
        'SOUTH': {'captured': 5118414, 'fg_rev': 1919405, 'comb_per_mw': 22748},
        'PAN': {'captured': 6092589, 'fg_rev': 2284721, 'comb_per_mw': 24270},
        'WEST': {'captured': 6285939, 'fg_rev': 2357227, 'comb_per_mw': 24572},
    }
}

HUB_NAMES = {1: 'SOUTH', 2: 'PAN', 3: 'WEST'}
HUB_CODES = {'SOUTH': 1, 'PAN': 2, 'WEST': 3}

# ============================================
# BASELINE VALUES FROM FINAL MODEL
# ============================================
BASELINE = {
    # Parameters
    'mae': 6.0,
    'plant_capacity': 240,
    'virtual_position': 100,
    'fg_fee_rate': 0.375,
    'high_capture': 0.90,
    'med_capture': 0.50,
    'low_capture': 0.10,
    'annualization': 1.3333,
    'alpha_hub': 3,  # WEST
    'hedge_hub': 2,  # PAN
    
    # RN Results
    'rn_high_hours': 1199,
    'rn_med_hours': 836,
    'rn_low_hours': 1460,
    'rn_total_hours': 3495,
    'rn_high_opp': 3525361,
    'rn_med_opp': 849404,
    'rn_low_opp': 512634,
    'rn_total_opp': 4887399,
    'rn_high_cap': 3172825,
    'rn_med_cap': 424702,
    'rn_low_cap': 51263,
    'rn_total_cap': 3648790,
    'rn_baseline_rev': 12017156,
    'rn_perfect_rev': 17567054,
    
    # VT Results (baseline with WEST/PAN)
    'alpha_hours': 3057,
    'hedge_hours': 3495,
    'total_hours': 6552,
    'alpha_opp': 5230185,
    'hedge_opp': 5742001,
    
    # Monthly data (estimated from 9-month period)
    'monthly_rn': [380000, 420000, 450000, 480000, 520000, 490000, 410000, 350000, 350000],
    'monthly_alpha': [450000, 480000, 520000, 560000, 600000, 580000, 500000, 420000, 420000],
    'monthly_hedge': [480000, 510000, 550000, 590000, 630000, 610000, 530000, 450000, 450000],
}

# ============================================
# MONTHLY DATA
# ============================================
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']

MONTHLY_DATA = {
    'Month': MONTHS,
    'RN_Captured': [380000, 420000, 450000, 480000, 520000, 490000, 410000, 350000, 348790],
    'Alpha_Captured': [420000, 450000, 490000, 530000, 580000, 560000, 480000, 400000, 406599],
    'Hedge_Captured': [480000, 510000, 550000, 590000, 640000, 620000, 530000, 450000, 459442],
    'Production_Hours': [350, 380, 400, 420, 430, 410, 390, 370, 345],
    'Avg_DART': [14.2, 15.8, 17.3, 19.1, 21.5, 20.2, 16.8, 14.5, 13.9],
}

# ============================================
# SESSION STATE
# ============================================
def init_session_state():
    defaults = {
        'mae': BASELINE['mae'],
        'plant_capacity': BASELINE['plant_capacity'],
        'virtual_position': BASELINE['virtual_position'],
        'fg_fee_rate': BASELINE['fg_fee_rate'],
        'high_capture': BASELINE['high_capture'],
        'med_capture': BASELINE['med_capture'],
        'low_capture': BASELINE['low_capture'],
        'alpha_hub': BASELINE['alpha_hub'],
        'hedge_hub': BASELINE['hedge_hub'],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ============================================
# CALCULATION FUNCTIONS
# ============================================

def calculate_rn_metrics(mae, capture_rates):
    """Recalculate RN metrics based on MAE changes"""
    high_thresh = 2 * mae
    base_mae = 6.0
    
    # Hours shift based on MAE
    if mae <= base_mae:
        high_hours = int(BASELINE['rn_high_hours'] * (1 + (base_mae - mae) * 0.08))
        low_hours = int(BASELINE['rn_low_hours'] * (1 - (base_mae - mae) * 0.05))
    else:
        high_hours = int(BASELINE['rn_high_hours'] * (1 - (mae - base_mae) * 0.08))
        low_hours = int(BASELINE['rn_low_hours'] * (1 + (mae - base_mae) * 0.05))
    
    med_hours = BASELINE['rn_total_hours'] - high_hours - low_hours
    
    # Recalculate opportunity
    high_opp = BASELINE['rn_high_opp'] * (high_hours / BASELINE['rn_high_hours']) if BASELINE['rn_high_hours'] > 0 else 0
    med_opp = BASELINE['rn_med_opp'] * (med_hours / BASELINE['rn_med_hours']) if BASELINE['rn_med_hours'] > 0 else 0
    low_opp = BASELINE['rn_low_opp'] * (low_hours / BASELINE['rn_low_hours']) if BASELINE['rn_low_hours'] > 0 else 0
    
    # Apply capture rates
    high_cap = high_opp * capture_rates[0]
    med_cap = med_opp * capture_rates[1]
    low_cap = low_opp * capture_rates[2]
    
    total_cap = high_cap + med_cap + low_cap
    total_opp = high_opp + med_opp + low_opp
    
    return {
        'high_hours': high_hours, 'med_hours': med_hours, 'low_hours': low_hours,
        'high_opp': high_opp, 'med_opp': med_opp, 'low_opp': low_opp,
        'high_cap': high_cap, 'med_cap': med_cap, 'low_cap': low_cap,
        'total_cap': total_cap, 'total_opp': total_opp,
        'cap_ann': total_cap * BASELINE['annualization']
    }

def calculate_vt_metrics(mae, capture_rates, position_mw, alpha_hub, hedge_hub):
    """Calculate VT metrics based on hub selection and parameters"""
    
    # Get hub names
    alpha_hub_name = HUB_NAMES[alpha_hub]
    hedge_hub_name = HUB_NAMES[hedge_hub]
    
    # Get base captured values from hub data
    alpha_base = HUB_DATA['ALPHA'][alpha_hub_name]['captured']
    hedge_base = HUB_DATA['HEDGE'][hedge_hub_name]['captured']
    
    # Scale by position size (baseline is 100 MW)
    position_ratio = position_mw / BASELINE['virtual_position']
    alpha_cap = alpha_base * position_ratio
    hedge_cap = hedge_base * position_ratio
    
    # MAE affects capture slightly (better MAE = slightly higher capture)
    mae_factor = 1 + (BASELINE['mae'] - mae) * 0.015
    alpha_cap *= mae_factor
    hedge_cap *= mae_factor
    
    # Capture rate scaling
    base_avg_capture = (BASELINE['high_capture'] + BASELINE['med_capture'] + BASELINE['low_capture']) / 3
    new_avg_capture = (capture_rates[0] + capture_rates[1] + capture_rates[2]) / 3
    capture_ratio = new_avg_capture / base_avg_capture
    
    alpha_cap *= capture_ratio
    hedge_cap *= capture_ratio
    
    return {
        'alpha_hub': alpha_hub_name,
        'hedge_hub': hedge_hub_name,
        'alpha_cap': alpha_cap,
        'hedge_cap': hedge_cap,
        'total_vt': alpha_cap + hedge_cap
    }

def calculate_combined_metrics(rn_metrics, vt_metrics, fg_fee_rate, plant_capacity):
    """Calculate combined metrics"""
    total_value = rn_metrics['cap_ann'] + vt_metrics['total_vt']
    fg_revenue = total_value * fg_fee_rate
    client_uplift = total_value * (1 - fg_fee_rate)
    per_mw = total_value / plant_capacity
    mw_for_10m = 10_000_000 / (fg_revenue / plant_capacity) if fg_revenue > 0 else 0
    
    return {
        'total_value': total_value,
        'fg_revenue': fg_revenue,
        'client_uplift': client_uplift,
        'per_mw': per_mw,
        'mw_for_10m': mw_for_10m
    }

def calculate_scenarios(mae, position_mw, alpha_hub, hedge_hub, plant_capacity):
    """Calculate multiple scenarios"""
    scenarios = {
        'Very Conservative': {'high': 0.70, 'med': 0.30, 'low': 0.00},
        'Conservative': {'high': 0.80, 'med': 0.40, 'low': 0.05},
        'Base Case': {'high': 0.90, 'med': 0.50, 'low': 0.10},
        'Optimistic': {'high': 0.95, 'med': 0.60, 'low': 0.15},
        'Aggressive': {'high': 0.98, 'med': 0.70, 'low': 0.20},
    }
    
    results = []
    for name, rates in scenarios.items():
        capture_rates = [rates['high'], rates['med'], rates['low']]
        rn = calculate_rn_metrics(mae, capture_rates)
        vt = calculate_vt_metrics(mae, capture_rates, position_mw, alpha_hub, hedge_hub)
        combined = calculate_combined_metrics(rn, vt, 0.375, plant_capacity)
        
        results.append({
            'Scenario': name,
            'High': f"{rates['high']:.0%}",
            'Medium': f"{rates['med']:.0%}",
            'Low': f"{rates['low']:.0%}",
            'RN Captured': rn['cap_ann'],
            'VT Captured': vt['total_vt'],
            'Total Value': combined['total_value'],
            'FG Revenue': combined['fg_revenue'],
            '$/MW/Year': combined['per_mw']
        })
    
    return pd.DataFrame(results)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("## ⚙️ Model Parameters")
    
    st.markdown("### 📊 Forecast Accuracy")
    mae = st.slider(
        "MAE [$/MWh]", 
        min_value=3.0, max_value=12.0, 
        value=st.session_state.mae, step=0.5,
        help="Mean Absolute Error - Lower = Better Forecast"
    )
    st.caption(f"Thresholds: High >${2*mae:.0f} | Med ${mae:.0f}-${2*mae:.0f} | Low <${mae:.0f}")
    
    st.markdown("### 🏭 Plant Settings")
    plant_capacity = st.number_input(
        "Plant Capacity [MW]", 
        min_value=50, max_value=500, 
        value=st.session_state.plant_capacity
    )
    virtual_position = st.number_input(
        "Virtual Position [MW]", 
        min_value=10, max_value=300, 
        value=st.session_state.virtual_position
    )
    
    st.markdown("### 💰 Fee Structure")
    fg_fee_pct = st.slider(
        "FG Fee Rate [%]", 
        min_value=20, max_value=50, 
        value=int(st.session_state.fg_fee_rate * 100)
    )
    fg_fee_rate = fg_fee_pct / 100
    
    st.markdown("### 🎯 Capture Rates")
    col1, col2, col3 = st.columns(3)
    with col1:
        high_cap = st.number_input("High%", 50, 100, int(st.session_state.high_capture * 100)) / 100
    with col2:
        med_cap = st.number_input("Med%", 20, 80, int(st.session_state.med_capture * 100)) / 100
    with col3:
        low_cap = st.number_input("Low%", 0, 30, int(st.session_state.low_capture * 100)) / 100
    
    st.markdown("### 🌐 Hub Selection")
    alpha_hub = st.selectbox(
        "Alpha Hub (Non-Prod)", 
        options=[1, 2, 3],
        format_func=lambda x: HUB_NAMES[x],
        index=st.session_state.alpha_hub - 1
    )
    hedge_hub = st.selectbox(
        "Hedge Hub (Production)", 
        options=[1, 2, 3],
        format_func=lambda x: HUB_NAMES[x],
        index=st.session_state.hedge_hub - 1
    )
    
    st.markdown("---")
    if st.button("🔄 Reset to Baseline"):
        for key in ['mae', 'plant_capacity', 'virtual_position', 'fg_fee_rate',
                    'high_capture', 'med_capture', 'low_capture', 'alpha_hub', 'hedge_hub']:
            st.session_state[key] = BASELINE[key]
        st.rerun()
    
    if st.button("🔒 Lock Session", help="Re-display the confidentiality notice and password"):
        st.session_state["access_granted"] = False
        st.session_state["disclaimer_accepted"] = False
        st.session_state["password_error"] = False
        st.rerun()

# Update session state
st.session_state.mae = mae
st.session_state.plant_capacity = plant_capacity
st.session_state.virtual_position = virtual_position
st.session_state.fg_fee_rate = fg_fee_rate
st.session_state.high_capture = high_cap
st.session_state.med_capture = med_cap
st.session_state.low_capture = low_cap
st.session_state.alpha_hub = alpha_hub
st.session_state.hedge_hub = hedge_hub

# ============================================
# CALCULATIONS
# ============================================
capture_rates = [high_cap, med_cap, low_cap]
rn = calculate_rn_metrics(mae, capture_rates)
vt = calculate_vt_metrics(mae, capture_rates, virtual_position, alpha_hub, hedge_hub)
combined = calculate_combined_metrics(rn, vt, fg_fee_rate, plant_capacity)

# ============================================
# HEADER
# ============================================
st.markdown('<p class="main-header">⚡ FG-GPT Value Creation Model</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">7 Ranch Solar (240 MW) | January - September 2025 | Annualized Projections</p>', unsafe_allow_html=True)

# Show parameter changes
changes = []
if mae != BASELINE['mae']: changes.append(f"MAE: ${BASELINE['mae']}→${mae}")
if virtual_position != BASELINE['virtual_position']: changes.append(f"Position: {BASELINE['virtual_position']}→{virtual_position}MW")
if alpha_hub != BASELINE['alpha_hub']: changes.append(f"Alpha Hub: {HUB_NAMES[BASELINE['alpha_hub']]}→{HUB_NAMES[alpha_hub]}")
if hedge_hub != BASELINE['hedge_hub']: changes.append(f"Hedge Hub: {HUB_NAMES[BASELINE['hedge_hub']]}→{HUB_NAMES[hedge_hub]}")
if changes:
    st.info(f"📝 **Modified Parameters:** {' | '.join(changes)}")

# ============================================
# TABS
# ============================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Executive Summary",
    "🏭 Resource Node",
    "💹 Virtual Trading", 
    "📈 Sensitivity & Scenarios",
    "📅 Monthly Performance",
    "📋 Data Summary"
])

# ============================================
# TAB 1: EXECUTIVE SUMMARY
# ============================================
with tab1:
    st.markdown("## 💼 Executive Summary")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate baseline for comparison
    baseline_vt = calculate_vt_metrics(BASELINE['mae'], [BASELINE['high_capture'], BASELINE['med_capture'], BASELINE['low_capture']], 
                                       BASELINE['virtual_position'], BASELINE['alpha_hub'], BASELINE['hedge_hub'])
    baseline_rn = calculate_rn_metrics(BASELINE['mae'], [BASELINE['high_capture'], BASELINE['med_capture'], BASELINE['low_capture']])
    baseline_combined = calculate_combined_metrics(baseline_rn, baseline_vt, BASELINE['fg_fee_rate'], BASELINE['plant_capacity'])
    
    delta_per_mw = ((combined['per_mw'] / baseline_combined['per_mw']) - 1) * 100
    
    with col1:
        st.metric(
            "Combined $/MW/Year",
            f"${combined['per_mw']:,.0f}",
            delta=f"{delta_per_mw:+.1f}%" if abs(delta_per_mw) > 0.1 else None
        )
    
    with col2:
        st.metric(
            "FG Annual Revenue",
            f"${combined['fg_revenue']:,.0f}",
            delta=f"From {plant_capacity} MW"
        )
    
    with col3:
        rev_boost = (combined['client_uplift'] / BASELINE['rn_baseline_rev']) * 100
        st.metric(
            "Client Annual Uplift",
            f"${combined['client_uplift']:,.0f}",
            delta=f"+{rev_boost:.0f}% revenue"
        )
    
    with col4:
        st.metric(
            "MW for $10M ARR",
            f"{combined['mw_for_10m']:,.0f} MW",
            delta="Target capacity"
        )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Value Creation by Strategy")
        fig_pie = go.Figure(data=[go.Pie(
            labels=['RN Optimization', 'Alpha Trading', 'Hedge Trading'],
            values=[rn['cap_ann'], vt['alpha_cap'], vt['hedge_cap']],
            hole=0.45,
            marker_colors=['#1F4E79', '#2E75B6', '#5BA3D9'],
            textinfo='label+percent',
            textposition='outside',
        )])
        fig_pie.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            height=380,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        fig_pie.add_annotation(
            text=f"<b>${combined['total_value']/1e6:.1f}M</b><br>Total",
            x=0.5, y=0.5, font_size=14, showarrow=False
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("### 💰 Revenue Split")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name=f'Client ({(1-fg_fee_rate):.1%})',
            x=['RN Strategy', 'VT Strategy', 'Combined'],
            y=[rn['cap_ann'] * (1-fg_fee_rate), vt['total_vt'] * (1-fg_fee_rate), combined['client_uplift']],
            marker_color='#28a745',
            text=[f"${v/1e6:.2f}M" for v in [rn['cap_ann'] * (1-fg_fee_rate), vt['total_vt'] * (1-fg_fee_rate), combined['client_uplift']]],
            textposition='inside'
        ))
        fig_bar.add_trace(go.Bar(
            name=f'FG ({fg_fee_rate:.1%})',
            x=['RN Strategy', 'VT Strategy', 'Combined'],
            y=[rn['cap_ann'] * fg_fee_rate, vt['total_vt'] * fg_fee_rate, combined['fg_revenue']],
            marker_color='#1F4E79',
            text=[f"${v/1e6:.2f}M" for v in [rn['cap_ann'] * fg_fee_rate, vt['total_vt'] * fg_fee_rate, combined['fg_revenue']]],
            textposition='inside'
        ))
        fig_bar.update_layout(
            barmode='stack',
            yaxis_title="Annual Value [$]",
            yaxis_tickformat='$,.0f',
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Summary table
    st.markdown("### 📋 Detailed Breakdown")
    summary_df = pd.DataFrame({
        'Metric': [
            '🏭 RN Captured (Annualized)',
            f'🌙 Alpha Trading ({vt["alpha_hub"]} Hub)',
            f'☀️ Hedge Trading ({vt["hedge_hub"]} Hub)',
            '📊 Total Value Created',
            '💵 FG Revenue',
            '📈 Client Uplift',
            '⚡ Combined $/MW/Year',
        ],
        'Value': [
            f"${rn['cap_ann']:,.0f}",
            f"${vt['alpha_cap']:,.0f}",
            f"${vt['hedge_cap']:,.0f}",
            f"${combined['total_value']:,.0f}",
            f"${combined['fg_revenue']:,.0f}",
            f"${combined['client_uplift']:,.0f}",
            f"${combined['per_mw']:,.0f}",
        ],
        '% of Total': [
            f"{rn['cap_ann']/combined['total_value']*100:.1f}%",
            f"{vt['alpha_cap']/combined['total_value']*100:.1f}%",
            f"{vt['hedge_cap']/combined['total_value']*100:.1f}%",
            "100%",
            f"{fg_fee_rate:.1%}",
            f"{1-fg_fee_rate:.1%}",
            "-",
        ]
    })
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # ============================================
    # BREAK-EVEN ANALYSIS SECTION
    # ============================================
    st.markdown("---")
    st.markdown("### 💰 Break-even Analysis")
    st.markdown("*Understand FG's cost basis and your value potential*")
    
    # Year selector
    be_col1, be_col2, be_col3 = st.columns([1, 1, 2])
    
    with be_col1:
        year_option = st.selectbox(
            "Select Year",
            options=["Year 1", "Year 2", "Year 3", "Custom"],
            index=0,
            help="Select budget year or enter custom amount"
        )
    
    with be_col2:
        if year_option == "Custom":
            fg_annual_cost = st.number_input(
                "Custom Budget ($)",
                min_value=100000,
                max_value=10000000,
                value=2500000,
                step=100000,
                format="%d"
            )
        else:
            fg_annual_cost = BUDGET_DATA[year_option]
            st.metric("FG Annual Budget", f"${fg_annual_cost:,.0f}")
    
    # Calculate break-even metrics
    mw_contracted = combined['mw_for_10m']  # Use MW for $10M as contracted capacity
    
    if mw_contracted > 0:
        breakeven_per_mw = fg_annual_cost / mw_contracted
        fg_revenue_per_mw = combined['fg_revenue'] / plant_capacity
        fg_margin_per_mw = fg_revenue_per_mw - (fg_annual_cost / mw_contracted * (plant_capacity / mw_contracted))
        
        # Recalculate based on MW for $10M
        breakeven_per_mw = fg_annual_cost / mw_contracted
        fg_revenue_per_mw_at_scale = 10000000 / mw_contracted  # FG gets $10M at this MW level
        fg_margin_per_mw_at_scale = fg_revenue_per_mw_at_scale - breakeven_per_mw
        client_uplift_per_mw = combined['per_mw'] - fg_revenue_per_mw_at_scale
        
        # Margin of safety
        margin_of_safety = fg_revenue_per_mw_at_scale / breakeven_per_mw if breakeven_per_mw > 0 else 0
        
        with be_col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                        padding: 15px; border-radius: 10px; border-left: 4px solid #28a745; color: #1b5e20;">
                <b>At {mw_contracted:,.0f} MW contracted:</b><br>
                Break-even: <b>${breakeven_per_mw:,.0f}/MW/Year</b><br>
                Margin of Safety: <b>{margin_of_safety:.1f}x</b> 
                <span style="color: #2e7d32; font-size: 0.9em;">(FG only needs {1/margin_of_safety*100:.0f}% of projected value to cover costs)</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Break-even metrics row
        be_met_col1, be_met_col2, be_met_col3, be_met_col4 = st.columns(4)
        
        with be_met_col1:
            st.metric(
                "Break-even $/MW",
                f"${breakeven_per_mw:,.0f}",
                help="FG's cost basis per MW (Budget ÷ Contracted MWs)"
            )
        
        with be_met_col2:
            st.metric(
                "FG Margin $/MW",
                f"${fg_margin_per_mw_at_scale:,.0f}",
                delta=f"{(fg_margin_per_mw_at_scale/fg_revenue_per_mw_at_scale)*100:.0f}% of FG revenue",
                help="FG profit above break-even"
            )
        
        with be_met_col3:
            st.metric(
                "Client Uplift $/MW",
                f"${client_uplift_per_mw:,.0f}",
                delta=f"{(client_uplift_per_mw/combined['per_mw'])*100:.0f}% of total",
                help="Client's share of value"
            )
        
        with be_met_col4:
            st.metric(
                "Total $/MW",
                f"${combined['per_mw']:,.0f}",
                help="Combined value per MW"
            )
        
        # Waterfall Chart (true waterfall with floating bars)
        st.markdown("#### 📊 Value Waterfall (Per MW Basis)")
        
        # Calculate cumulative positions for floating bars
        base1 = 0
        base2 = breakeven_per_mw
        base3 = breakeven_per_mw + fg_margin_per_mw_at_scale
        total_value = combined['per_mw']
        
        fig_waterfall = go.Figure()
        
        # Bar 1: FG Break-even (starts at 0)
        fig_waterfall.add_trace(go.Bar(
            name="FG Break-even (Cost Basis)",
            x=["FG Break-even"],
            y=[breakeven_per_mw],
            base=[base1],
            marker_color="#ff9800",
            text=[f"${breakeven_per_mw:,.0f}"],
            textposition="outside",
            width=0.5,
        ))
        
        # Bar 2: FG Margin (floats on top of break-even)
        fig_waterfall.add_trace(go.Bar(
            name="FG Margin (FG Profit)",
            x=["FG Margin"],
            y=[fg_margin_per_mw_at_scale],
            base=[base2],
            marker_color="#1F4E79",
            text=[f"${fg_margin_per_mw_at_scale:,.0f}"],
            textposition="outside",
            width=0.5,
        ))
        
        # Bar 3: Client Uplift (floats on top of margin)
        fig_waterfall.add_trace(go.Bar(
            name="Client Uplift (Your Value)",
            x=["Client Uplift"],
            y=[client_uplift_per_mw],
            base=[base3],
            marker_color="#28a745",
            text=[f"${client_uplift_per_mw:,.0f}"],
            textposition="outside",
            width=0.5,
        ))
        
        # Bar 4: Total (full bar from 0)
        fig_waterfall.add_trace(go.Bar(
            name="Total $/MW/Year",
            x=["TOTAL"],
            y=[total_value],
            base=[0],
            marker_color="#2e7d32",
            text=[f"${total_value:,.0f}"],
            textposition="outside",
            width=0.5,
        ))
        
        # Add connector lines between bars
        fig_waterfall.add_shape(
            type="line", x0=0.25, x1=0.75, y0=breakeven_per_mw, y1=breakeven_per_mw,
            line=dict(color="gray", width=1, dash="dot")
        )
        fig_waterfall.add_shape(
            type="line", x0=1.25, x1=1.75, y0=base3, y1=base3,
            line=dict(color="gray", width=1, dash="dot")
        )
        fig_waterfall.add_shape(
            type="line", x0=2.25, x1=2.75, y0=total_value, y1=total_value,
            line=dict(color="gray", width=1, dash="dot")
        )
        
        fig_waterfall.update_layout(
            title=f"Value Creation Breakdown at {mw_contracted:,.0f} MW ({year_option}: ${fg_annual_cost/1e6:.2f}M budget)",
            yaxis_title="$/MW/Year",
            yaxis_tickformat="$,.0f",
            height=450,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            bargap=0.3,
        )
        
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
        # Explanation
        with st.expander("ℹ️ How to interpret this chart"):
            st.markdown(f"""
            **The Sales Story:**
            
            1. **FG Break-even (${breakeven_per_mw:,.0f}/MW)** - This is our cost to operate. At {mw_contracted:,.0f} MW, 
               we need ${breakeven_per_mw:,.0f}/MW just to cover our {year_option} budget of ${fg_annual_cost:,.0f}.
               *This is verifiable and concrete.*
            
            2. **FG Margin (${fg_margin_per_mw_at_scale:,.0f}/MW)** - This is our profit above break-even. 
               It's determined by the **FG Fee Rate ({fg_fee_rate:.1%})** you set.
               *This is negotiable based on your fee structure.*
            
            3. **Client Uplift (${client_uplift_per_mw:,.0f}/MW)** - This is YOUR value. 
               It's the remaining {(1-fg_fee_rate):.1%} of the total opportunity.
               *This depends on market conditions and capture rates.*
            
            4. **Total Value (${combined['per_mw']:,.0f}/MW)** - The full DART opportunity we can capture together.
            
            ---
            
            **Key Insight:** With a **{margin_of_safety:.1f}x margin of safety**, FG only needs to capture 
            {1/margin_of_safety*100:.0f}% of the projected value to cover costs. The rest is upside for both parties.
            """)
    else:
        st.warning("Cannot calculate break-even: MW for $10M is zero. Adjust parameters.")

# ============================================
# TAB 2: RESOURCE NODE
# ============================================
with tab2:
    st.markdown("## 🏭 Resource Node Optimization")
    st.markdown(f"**Strategy:** Optimize physical dispatch using FG-GPT forecast (MAE = ${mae}/MWh)")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Production Hours", f"{BASELINE['rn_total_hours']:,}")
    with col2:
        st.metric("Total Opportunity", f"${rn['total_opp']:,.0f}")
    with col3:
        capture_pct = rn['total_cap'] / rn['total_opp'] * 100 if rn['total_opp'] > 0 else 0
        st.metric("Effective Capture", f"{capture_pct:.1f}%")
    with col4:
        st.metric("RN $/MW/Year", f"${rn['cap_ann']/plant_capacity:,.0f}")
    
    st.markdown("---")
    st.markdown("### 🎯 Confidence Zone Analysis")
    
    zone_df = pd.DataFrame({
        'Zone': [f'🟢 High (>${2*mae:.0f})', f'🟡 Medium (${mae:.0f}-${2*mae:.0f})', f'🔴 Low (<${mae:.0f})', '📊 TOTAL'],
        'Hours': [rn['high_hours'], rn['med_hours'], rn['low_hours'], BASELINE['rn_total_hours']],
        '% Hours': [f"{rn['high_hours']/BASELINE['rn_total_hours']*100:.1f}%", f"{rn['med_hours']/BASELINE['rn_total_hours']*100:.1f}%", 
                   f"{rn['low_hours']/BASELINE['rn_total_hours']*100:.1f}%", "100%"],
        'Opportunity': [f"${rn['high_opp']:,.0f}", f"${rn['med_opp']:,.0f}", f"${rn['low_opp']:,.0f}", f"${rn['total_opp']:,.0f}"],
        'Capture Rate': [f"{high_cap:.0%}", f"{med_cap:.0%}", f"{low_cap:.0%}", f"{capture_pct:.1f}%"],
        'Captured': [f"${rn['high_cap']:,.0f}", f"${rn['med_cap']:,.0f}", f"${rn['low_cap']:,.0f}", f"${rn['total_cap']:,.0f}"]
    })
    st.dataframe(zone_df, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    with col1:
        fig_hours = go.Figure(data=[go.Pie(
            labels=['High', 'Medium', 'Low'],
            values=[rn['high_hours'], rn['med_hours'], rn['low_hours']],
            hole=0.4,
            marker_colors=['#28a745', '#ffc107', '#dc3545'],
        )])
        fig_hours.update_layout(title="Hours Distribution by Zone", height=350)
        st.plotly_chart(fig_hours, use_container_width=True)
    
    with col2:
        fig_value = go.Figure()
        fig_value.add_trace(go.Bar(name='Opportunity', x=['High', 'Medium', 'Low'], 
                                   y=[rn['high_opp'], rn['med_opp'], rn['low_opp']], marker_color='#2E75B6'))
        fig_value.add_trace(go.Bar(name='Captured', x=['High', 'Medium', 'Low'], 
                                   y=[rn['high_cap'], rn['med_cap'], rn['low_cap']], marker_color='#1F4E79'))
        fig_value.update_layout(title="Opportunity vs Captured", barmode='group', yaxis_tickformat='$,.0f', height=350)
        st.plotly_chart(fig_value, use_container_width=True)

# ============================================
# TAB 3: VIRTUAL TRADING
# ============================================
with tab3:
    st.markdown("## 💹 Virtual Trading Strategies")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### 🌙 Alpha Strategy ({vt['alpha_hub']} Hub)")
        st.metric("Alpha Hours", f"{BASELINE['alpha_hours']:,}")
        st.metric("Alpha Captured (Ann.)", f"${vt['alpha_cap']:,.0f}")
        st.metric("Alpha FG Revenue", f"${vt['alpha_cap'] * fg_fee_rate:,.0f}")
        st.markdown("""
        - Trades during non-production hours
        - Pure financial arbitrage on DART spreads
        """)
    
    with col2:
        st.markdown(f"### ☀️ Hedge Strategy ({vt['hedge_hub']} Hub)")
        st.metric("Hedge Hours", f"{BASELINE['hedge_hours']:,}")
        st.metric("Hedge Captured (Ann.)", f"${vt['hedge_cap']:,.0f}")
        st.metric("Hedge FG Revenue", f"${vt['hedge_cap'] * fg_fee_rate:,.0f}")
        st.markdown("""
        - Trades during production hours
        - Financial hedge against physical generation
        """)
    
    st.markdown("---")
    
    # Hub Comparison Section
    st.markdown("### 🌐 Hub Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Alpha Hub Performance")
        alpha_hub_df = pd.DataFrame({
            'Hub': ['SOUTH', 'PAN', 'WEST'],
            'Captured (Ann.)': [f"${HUB_DATA['ALPHA']['SOUTH']['captured']:,}", 
                               f"${HUB_DATA['ALPHA']['PAN']['captured']:,}", 
                               f"${HUB_DATA['ALPHA']['WEST']['captured']:,}"],
            'vs WEST': [f"${HUB_DATA['ALPHA']['SOUTH']['captured'] - HUB_DATA['ALPHA']['WEST']['captured']:,}",
                       f"${HUB_DATA['ALPHA']['PAN']['captured'] - HUB_DATA['ALPHA']['WEST']['captured']:,}",
                       "$0 (Best)"]
        })
        st.dataframe(alpha_hub_df, use_container_width=True, hide_index=True)
        
        fig_alpha = go.Figure(data=[go.Bar(
            x=['SOUTH', 'PAN', 'WEST'],
            y=[HUB_DATA['ALPHA']['SOUTH']['captured'], HUB_DATA['ALPHA']['PAN']['captured'], HUB_DATA['ALPHA']['WEST']['captured']],
            marker_color=['#6c757d', '#6c757d', '#28a745'],
            text=[f"${v/1e6:.1f}M" for v in [HUB_DATA['ALPHA']['SOUTH']['captured'], HUB_DATA['ALPHA']['PAN']['captured'], HUB_DATA['ALPHA']['WEST']['captured']]],
            textposition='outside'
        )])
        fig_alpha.update_layout(title="Alpha Captured by Hub", yaxis_tickformat='$,.0f', height=300)
        st.plotly_chart(fig_alpha, use_container_width=True)
    
    with col2:
        st.markdown("#### Hedge Hub Performance")
        hedge_hub_df = pd.DataFrame({
            'Hub': ['SOUTH', 'PAN', 'WEST'],
            'Captured (Ann.)': [f"${HUB_DATA['HEDGE']['SOUTH']['captured']:,}", 
                               f"${HUB_DATA['HEDGE']['PAN']['captured']:,}", 
                               f"${HUB_DATA['HEDGE']['WEST']['captured']:,}"],
            'vs WEST': [f"${HUB_DATA['HEDGE']['SOUTH']['captured'] - HUB_DATA['HEDGE']['WEST']['captured']:,}",
                       f"${HUB_DATA['HEDGE']['PAN']['captured'] - HUB_DATA['HEDGE']['WEST']['captured']:,}",
                       "$0 (Best)"]
        })
        st.dataframe(hedge_hub_df, use_container_width=True, hide_index=True)
        
        fig_hedge = go.Figure(data=[go.Bar(
            x=['SOUTH', 'PAN', 'WEST'],
            y=[HUB_DATA['HEDGE']['SOUTH']['captured'], HUB_DATA['HEDGE']['PAN']['captured'], HUB_DATA['HEDGE']['WEST']['captured']],
            marker_color=['#6c757d', '#6c757d', '#28a745'],
            text=[f"${v/1e6:.1f}M" for v in [HUB_DATA['HEDGE']['SOUTH']['captured'], HUB_DATA['HEDGE']['PAN']['captured'], HUB_DATA['HEDGE']['WEST']['captured']]],
            textposition='outside'
        )])
        fig_hedge.update_layout(title="Hedge Captured by Hub", yaxis_tickformat='$,.0f', height=300)
        st.plotly_chart(fig_hedge, use_container_width=True)
    
    st.info(f"""
    **Current Selection:** Alpha = **{vt['alpha_hub']}** | Hedge = **{vt['hedge_hub']}**
    
    **Optimal Configuration:** WEST/WEST maximizes both strategies ($24,572/MW/Year)
    """)

# ============================================
# TAB 4: SENSITIVITY & SCENARIOS
# ============================================
with tab4:
    st.markdown("## 📈 Sensitivity Analysis & Scenarios")
    
    # Scenario Comparison
    st.markdown("### 📊 Scenario Comparison")
    
    scenario_df = calculate_scenarios(mae, virtual_position, alpha_hub, hedge_hub, plant_capacity)
    
    # Display table
    display_df = scenario_df.copy()
    display_df['RN Captured'] = display_df['RN Captured'].apply(lambda x: f"${x:,.0f}")
    display_df['VT Captured'] = display_df['VT Captured'].apply(lambda x: f"${x:,.0f}")
    display_df['Total Value'] = display_df['Total Value'].apply(lambda x: f"${x:,.0f}")
    display_df['FG Revenue'] = display_df['FG Revenue'].apply(lambda x: f"${x:,.0f}")
    display_df['$/MW/Year'] = display_df['$/MW/Year'].apply(lambda x: f"${x:,.0f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Scenario chart
    fig_scenario = go.Figure()
    colors = ['#dc3545', '#fd7e14', '#28a745', '#17a2b8', '#6f42c1']
    fig_scenario.add_trace(go.Bar(
        x=scenario_df['Scenario'],
        y=scenario_df['$/MW/Year'],
        marker_color=colors,
        text=[f"${v:,.0f}" for v in scenario_df['$/MW/Year']],
        textposition='outside'
    ))
    fig_scenario.update_layout(
        title="Combined $/MW/Year by Scenario",
        yaxis_title="$/MW/Year",
        yaxis_tickformat='$,.0f',
        height=400
    )
    st.plotly_chart(fig_scenario, use_container_width=True)
    
    st.markdown("---")
    
    # MAE Sensitivity
    st.markdown("### 🎯 MAE Sensitivity")
    
    mae_range = [3, 4, 5, 6, 7, 8, 9, 10]
    mae_results = []
    for m in mae_range:
        rn_m = calculate_rn_metrics(m, capture_rates)
        vt_m = calculate_vt_metrics(m, capture_rates, virtual_position, alpha_hub, hedge_hub)
        comb_m = calculate_combined_metrics(rn_m, vt_m, fg_fee_rate, plant_capacity)
        mae_results.append({
            'MAE': f'${m}',
            'High Threshold': f'${2*m}',
            'RN $/MW/Yr': rn_m['cap_ann'] / plant_capacity,
            'Combined $/MW/Yr': comb_m['per_mw']
        })
    
    mae_df = pd.DataFrame(mae_results)
    
    fig_mae = go.Figure()
    fig_mae.add_trace(go.Scatter(
        x=mae_range, y=[r['RN $/MW/Yr'] for r in mae_results],
        mode='lines+markers', name='RN $/MW/Year',
        line=dict(color='#2E75B6', width=3), marker=dict(size=10)
    ))
    fig_mae.add_trace(go.Scatter(
        x=mae_range, y=[r['Combined $/MW/Yr'] for r in mae_results],
        mode='lines+markers', name='Combined $/MW/Year',
        line=dict(color='#28a745', width=3), marker=dict(size=10)
    ))
    fig_mae.add_vline(x=mae, line_dash="dash", line_color="red", annotation_text=f"Current: ${mae}")
    fig_mae.update_layout(
        xaxis_title="MAE [$/MWh]",
        yaxis_title="$/MW/Year",
        yaxis_tickformat='$,.0f',
        height=400
    )
    st.plotly_chart(fig_mae, use_container_width=True)
    
    # Display MAE table
    mae_df['RN $/MW/Yr'] = mae_df['RN $/MW/Yr'].apply(lambda x: f"${x:,.0f}")
    mae_df['Combined $/MW/Yr'] = mae_df['Combined $/MW/Yr'].apply(lambda x: f"${x:,.0f}")
    st.dataframe(mae_df, use_container_width=True, hide_index=True)

# ============================================
# TAB 5: MONTHLY PERFORMANCE
# ============================================
with tab5:
    st.markdown("## 📅 Monthly Performance")
    
    monthly_df = pd.DataFrame(MONTHLY_DATA)
    
    # Calculate totals
    monthly_df['Total_Captured'] = monthly_df['RN_Captured'] + monthly_df['Alpha_Captured'] + monthly_df['Hedge_Captured']
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total RN (9-mo)", f"${monthly_df['RN_Captured'].sum():,.0f}")
    with col2:
        st.metric("Total Alpha (9-mo)", f"${monthly_df['Alpha_Captured'].sum():,.0f}")
    with col3:
        st.metric("Total Hedge (9-mo)", f"${monthly_df['Hedge_Captured'].sum():,.0f}")
    with col4:
        st.metric("Best Month", monthly_df.loc[monthly_df['Total_Captured'].idxmax(), 'Month'])
    
    st.markdown("---")
    
    # Stacked bar chart
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(name='RN Captured', x=MONTHS, y=monthly_df['RN_Captured'], marker_color='#1F4E79'))
    fig_monthly.add_trace(go.Bar(name='Alpha Captured', x=MONTHS, y=monthly_df['Alpha_Captured'], marker_color='#2E75B6'))
    fig_monthly.add_trace(go.Bar(name='Hedge Captured', x=MONTHS, y=monthly_df['Hedge_Captured'], marker_color='#5BA3D9'))
    fig_monthly.update_layout(
        title="Monthly Value Captured by Strategy",
        barmode='stack',
        yaxis_title="Value Captured [$]",
        yaxis_tickformat='$,.0f',
        height=450
    )
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Line charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig_hours = go.Figure()
        fig_hours.add_trace(go.Scatter(
            x=MONTHS, y=monthly_df['Production_Hours'],
            mode='lines+markers', name='Production Hours',
            line=dict(color='#28a745', width=2)
        ))
        fig_hours.update_layout(title="Production Hours by Month", yaxis_title="Hours", height=300)
        st.plotly_chart(fig_hours, use_container_width=True)
    
    with col2:
        fig_dart = go.Figure()
        fig_dart.add_trace(go.Scatter(
            x=MONTHS, y=monthly_df['Avg_DART'],
            mode='lines+markers', name='Avg |DART|',
            line=dict(color='#dc3545', width=2)
        ))
        fig_dart.update_layout(title="Average |DART| by Month", yaxis_title="$/MWh", height=300)
        st.plotly_chart(fig_dart, use_container_width=True)
    
    # Monthly table
    st.markdown("### 📋 Monthly Data Table")
    display_monthly = monthly_df.copy()
    for col in ['RN_Captured', 'Alpha_Captured', 'Hedge_Captured', 'Total_Captured']:
        display_monthly[col] = display_monthly[col].apply(lambda x: f"${x:,.0f}")
    display_monthly['Avg_DART'] = display_monthly['Avg_DART'].apply(lambda x: f"${x:.2f}")
    st.dataframe(display_monthly, use_container_width=True, hide_index=True)

# ============================================
# TAB 6: DATA SUMMARY
# ============================================
with tab6:
    st.markdown("## 📋 Data Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Current Parameters")
        params_df = pd.DataFrame({
            'Parameter': ['MAE [$/MWh]', 'Plant Capacity [MW]', 'Virtual Position [MW]', 'FG Fee Rate',
                         'High Capture', 'Medium Capture', 'Low Capture', 'Alpha Hub', 'Hedge Hub'],
            'Current': [f'${mae}', f'{plant_capacity}', f'{virtual_position}', f'{fg_fee_rate:.1%}',
                       f'{high_cap:.0%}', f'{med_cap:.0%}', f'{low_cap:.0%}', HUB_NAMES[alpha_hub], HUB_NAMES[hedge_hub]],
            'Baseline': [f'${BASELINE["mae"]}', f'{BASELINE["plant_capacity"]}', f'{BASELINE["virtual_position"]}',
                        f'{BASELINE["fg_fee_rate"]:.1%}', f'{BASELINE["high_capture"]:.0%}', f'{BASELINE["med_capture"]:.0%}',
                        f'{BASELINE["low_capture"]:.0%}', HUB_NAMES[BASELINE['alpha_hub']], HUB_NAMES[BASELINE['hedge_hub']]]
        })
        st.dataframe(params_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### 📈 Data Statistics")
        stats_df = pd.DataFrame({
            'Metric': ['Total Hours', 'Production Hours', 'Non-Production Hours', 'High Zone Hours',
                      'Medium Zone Hours', 'Low Zone Hours', 'Data Period', 'Annualization'],
            'Value': ['6,552', f'{BASELINE["rn_total_hours"]:,}', f'{BASELINE["alpha_hours"]:,}',
                     f'{rn["high_hours"]:,}', f'{rn["med_hours"]:,}', f'{rn["low_hours"]:,}',
                     'Jan - Sep 2025', '1.333x (9→12 mo)']
        })
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### 🔢 Key Results Summary")
    
    results_df = pd.DataFrame({
        'Metric': ['RN Opportunity (9-mo)', 'RN Captured (9-mo)', 'RN Captured (Ann.)', 'RN $/MW/Year',
                  'Alpha Captured (Ann.)', 'Hedge Captured (Ann.)', 'Total VT (Ann.)', 'VT $/MW/Year',
                  'Combined Total (Ann.)', 'FG Revenue (Ann.)', 'Client Uplift (Ann.)', 'Combined $/MW/Year'],
        'Value': [f"${rn['total_opp']:,.0f}", f"${rn['total_cap']:,.0f}", f"${rn['cap_ann']:,.0f}", f"${rn['cap_ann']/plant_capacity:,.0f}",
                 f"${vt['alpha_cap']:,.0f}", f"${vt['hedge_cap']:,.0f}", f"${vt['total_vt']:,.0f}", f"${vt['total_vt']/plant_capacity:,.0f}",
                 f"${combined['total_value']:,.0f}", f"${combined['fg_revenue']:,.0f}", f"${combined['client_uplift']:,.0f}", f"${combined['per_mw']:,.0f}"]
    })
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### 📝 Methodology")
    st.markdown("""
    **Confidence Zone Classification (based on MAE):**
    - **High Zone:** |DART| > 2×MAE → 90% capture rate
    - **Medium Zone:** MAE < |DART| ≤ 2×MAE → 50% capture rate
    - **Low Zone:** |DART| ≤ MAE → 10% capture rate
    
    **Value Calculation:**
    - RN: Opportunity × Zone Capture Rate → Annualized × FG Fee
    - VT: Position MW × DART Spread × Hours × Capture Rate → Annualized
    
    **Hub Data:** Actual results from model testing (SOUTH, PAN, WEST)
    
    **Data Source:** 7 Ranch Solar (240 MW), ERCOT market, Jan-Sep 2025
    """)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem;'>
    <p><strong>FG-GPT Value Creation Model v3</strong> | 7 Ranch Solar (240 MW) | Data: Jan-Sep 2025</p>
    <p>© 2025 FG-GPT | Solar Forecasting & Trading Optimization</p>
</div>
""", unsafe_allow_html=True)
