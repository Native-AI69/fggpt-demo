# FG-GPT Value Creation Model

Interactive investor pitch demo for FG-GPT's pre-seed funding round.

## Overview

FG-GPT provides AI-powered forecasting for solar plants in ERCOT, generating revenue through two strategies:

1. **Resource Node (RN) Optimization** - Physical dispatch optimization at the plant's node
2. **Virtual Trading (VT)** - Financial trading at ERCOT hubs
   - Alpha Strategy: Trades in non-production hours
   - Hedging Strategy: Trades in production hours

## Key Results (240 MW Plant + 100 MW Virtual)

| Metric | Value |
|--------|-------|
| FG Total Revenue | ~$5.5M/year |
| Client Uplift | ~$9.1M/year |
| Total Value Created | ~$14.6M/year |
| $/MW/Year | ~$22,748 |
| MW for $10M ARR | ~440 MW |

## Installation

```bash
# Clone or download the project
cd fggpt_model

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure

```
fggpt_model/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── config/
│   └── settings.py           # Default values, thresholds
├── model/
│   ├── __init__.py
│   ├── data_loader.py        # Load and prepare CSV data
│   ├── resource_node.py      # RN strategy calculations
│   ├── virtual_trading.py    # VT strategy (Alpha + Hedging)
│   └── combined.py           # Combined strategy
├── data/
│   ├── MNTZ_HB_SOUTH_extracted_2025.csv
│   ├── MNTZ_HB_PAN_extracted_2025.csv
│   ├── MNTZ_HB_WEST_extracted_2025.csv
│   ├── MNTZ_HB_HOUSTON_extracted_2025.csv
│   ├── MNTZ_HB_NORTH_extracted_2025.csv
│   ├── MNTZ_HB_HUBAVG_extracted_2025.csv
│   ├── MNTZ_HB_BUSAVG_extracted_2025.csv
│   └── MNTZ_7RNCHSLR_ALL_extracted_2025.csv
└── outputs/                  # Generated exports
```

## Features

### Interactive Controls
- **Strategy Toggle**: Switch between RN Only, VT Only, or Both
- **Plant Parameters**: Adjust capacity and virtual position size
- **Model Parameters**: Modify MAE, fee rates, capture rates
- **Hub Selection**: Compare SOUTH, PAN, WEST for Alpha strategy

### Visualizations
- Revenue breakdown pie chart
- Scenario comparison (RN Only vs VT Only vs Both)
- Hub comparison bar chart
- Monthly performance with stacked bars and line chart

### Key Metrics
- FG Total Revenue (Annual)
- Client Uplift (Annual)
- Total Value Created (Annual)
- $/MW/Year
- MW needed for $10M ARR

## Data

The model uses 9 months of ERCOT market data (Jan-Sep 2025):
- **Plant**: 7 Ranch Solar (240 MW)
- **Hubs**: SOUTH, PAN, WEST, HOUSTON, NORTH, HUBAVG, BUSAVG
- **Metrics**: Day-Ahead prices, Real-Time prices, DART spreads

## Model Logic

### Confidence Zones
Based on forecast accuracy (MAE = 6 $/MWh):
- **High**: |DART| > 12 $/MWh (2×MAE) → 90% capture rate
- **Medium**: 6 < |DART| ≤ 12 $/MWh → 50% capture rate
- **Low**: |DART| ≤ 6 $/MWh → 10% capture rate

### Value Calculation
```
Opportunity = Hours × Avg|DART| × MW
Captured = Opportunity × Capture_Rate
FG_Revenue = Captured × FG_Fee_Rate (37.5%)
Client_Uplift = Captured × (1 - FG_Fee_Rate)
```

## Deployment Options

| Use Case | Solution | Cost |
|----------|----------|------|
| Local demo | `streamlit run app.py` | $0 |
| Team access | Each person installs Python | $0 |
| Investor demo | Run on your laptop | $0 |
| Cloud hosting | Streamlit Cloud / AWS | $0-100/mo |

## Support

For questions about the model or investor presentation, contact FG-GPT.

---

*FG-GPT Value Creation Model | Pre-Seed Funding Round | Confidential*

