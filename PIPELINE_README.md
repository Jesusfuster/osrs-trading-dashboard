# 🚀 OSRS Trading Pipeline - Usage Guide

## 📦 Pipeline Architecture

```
SETUP (Once):
  └─ scripts/run_bulk_download.py        # Download all 6h data (~1-2h)

REGULAR (Every 3 days):
  └─ scripts/run_pipeline.py --mode full
      ├─ 1. update_6h_data.py           # Update 6h data (~5-10 min)
      ├─ 2. analyze_and_filter.py       # Find candidates (~5-10 min)
      └─ 3. download_1h_candidates.py   # Get 1h data for top 50 (~2-5 min)

DAILY (Every day):
  └─ scripts/run_pipeline.py --mode daily
      ├─ 1. analyze_timing.py           # (TODO) Find best buy/sell times
      └─ 2. generate_recommendations.py # (TODO) Generate portfolio
```

---

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Your Preferences
Edit `config.yaml`:
```yaml
# Change these to match your situation:
risk_profile: "moderate"  # conservative, moderate, aggressive
capital: 10000000         # Your available GP
ge_slots: 8               # Your GE slots
```

### 3. Initial Data Download
**Only run this ONCE:**
```bash
python scripts/run_bulk_download.py
```
⏱️ Takes ~1-2 hours
📁 Downloads to `data/raw/timeseries_6h/`

---

## 🔄 Regular Usage

### Every 3 Days: Full Pipeline

```bash
python scripts/run_pipeline.py --mode full
```

**What it does:**
1. ✅ Updates 6h data for all items (incremental + smart check*)
2. ✅ Analyzes all items and filters to top candidates (max 50)
3. ✅ Downloads 1h data for those candidates only
4. 🚧 Analyzes best buy/sell times (TODO)
5. 🚧 Generates daily recommendations (TODO)

⏱️ Total time: ~15-20 minutes (or instant if no new data!)

**\*Smart Check Optimization:**
The pipeline first checks ONE liquid item (Cannonball) to see if there's new data. If not, it skips the entire update! This means:
- ✅ If no new GE data → Completes in ~1 second
- ✅ If new data available → Downloads only new records (~5-10 min)

**Force update:**
```bash
# Skip the smart check and update anyway
python scripts/update_6h_data.py --force
```

**Output files:**
```
data/processed/
├── all_items_quick_analysis.parquet  # All items stats
├── level1_filtered.parquet           # After basic filtering
├── level2_filtered.parquet           # After quality filtering
└── final_candidates_moderate.parquet # Top 50 candidates ✅
```

---

### Every Day: Quick Update

```bash
python scripts/run_pipeline.py --mode daily
```

**What it does:**
1. 🚧 Re-analyzes timing with latest 1h data (TODO)
2. 🚧 Generates fresh recommendations (TODO)

⏱️ Total time: ~2-3 minutes

---

## 📊 Understanding the Output

### Final Candidates File

`data/processed/final_candidates_moderate.parquet` contains:

| Column | Description |
|--------|-------------|
| `name` | Item name |
| `avg_high_price` | Average sell price |
| `avg_low_price` | Average buy price |
| `avg_spread_pct` | Spread percentage |
| `win_rate` | % of profitable trades in backtest |
| `avg_roi` | Average ROI per trade |
| `sharpe_ratio` | Risk-adjusted returns |
| `final_score` | Composite quality score |

**View as CSV:**
```bash
# The pipeline also generates a CSV for easy viewing:
cat data/processed/final_candidates_moderate.csv
```

---

## 🎛️ Customization

### Change Risk Profile

Edit `config.yaml`:
```yaml
risk_profile: "aggressive"  # More opportunities, higher risk
# or
risk_profile: "conservative"  # Safer, fewer opportunities
```

Then re-run:
```bash
python scripts/run_pipeline.py --mode full
```

### Adjust Filters Manually

In `config.yaml`, under `risk_profiles`, you can tweak individual filters:

```yaml
moderate:
  level2:
    min_spread_pct: 5  # Increase for higher profit margins
    min_trading_frequency: 0.7  # Increase for more liquid items
```

---

## 🐛 Troubleshooting

### No candidates found

**Problem:** `analyze_and_filter.py` returns 0 candidates

**Solutions:**
1. Use a less restrictive risk profile (`aggressive`)
2. Reduce `min_win_rate` in `level3` filters
3. Check if bulk download completed successfully

### Download is too slow

**Problem:** Downloads taking >2 hours

**Solution:** This is normal for initial bulk download. Subsequent updates are much faster (~5-10 min).

### File not found errors

**Problem:** Scripts can't find data files

**Solution:** 
```bash
# Make sure you're running from project root:
cd /path/to/osrs_moneymaking
python scripts/run_pipeline.py --mode full
```

---

## 📅 Automation (Cron)

### Every 3 days at 6 AM:
```bash
0 6 */3 * * cd /path/to/osrs_moneymaking && /path/to/.venv/bin/python scripts/run_pipeline.py --mode full >> logs/pipeline.log 2>&1
```

### Every day at 7 AM:
```bash
0 7 * * * cd /path/to/osrs_moneymaking && /path/to/.venv/bin/python scripts/run_pipeline.py --mode daily >> logs/pipeline_daily.log 2>&1
```

---

## 🚧 TODO / Future Enhancements

- [ ] `scripts/analyze_timing.py` - Find best buy/sell times per item
- [ ] `scripts/generate_recommendations.py` - Portfolio optimization
- [ ] WiseOldMan integration for skill-based filtering
- [ ] Streamlit dashboard for visualization
- [ ] Crafting arbitrage analysis
- [ ] Real-time price monitoring

---

## 📁 Project Structure

```
osrs_moneymaking/
├── data/
│   ├── raw/
│   │   ├── mapping.parquet
│   │   ├── timeseries_6h/          # All items (6h granularity)
│   │   └── timeseries_1h/          # Candidates only (1h granularity)
│   ├── processed/
│   │   └── final_candidates_*.parquet
│   └── logs/
│
├── scripts/
│   ├── run_bulk_download.py        # ✅ Initial setup
│   ├── run_pipeline.py             # ✅ Master orchestrator
│   ├── update_6h_data.py           # ✅ Incremental updates
│   ├── analyze_and_filter.py       # ✅ Find candidates
│   ├── download_1h_candidates.py   # ✅ Get granular data
│   ├── analyze_timing.py           # 🚧 TODO
│   └── generate_recommendations.py # 🚧 TODO
│
├── src/
│   ├── data_collection/
│   ├── analysis/
│   └── recommendation/
│
├── config.yaml                     # ⚙️ Edit this!
└── README.md                       # You are here
```

---

## 💡 Quick Start Checklist

- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Edit `config.yaml` with your capital and risk profile
- [ ] Run initial bulk download (`python scripts/run_bulk_download.py`)
- [ ] Run full pipeline (`python scripts/run_pipeline.py --mode full`)
- [ ] Check `data/processed/final_candidates_moderate.csv`
- [ ] Set up cron for automation (optional)

---

**Questions? Issues? Check logs in `data/logs/osrs_trading.log`**
