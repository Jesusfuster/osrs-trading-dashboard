# 🎮 OSRS Trading Dashboard

Interactive dashboard for analyzing Old School RuneScape Grand Exchange trading opportunities.

## 🚀 Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run app.py

# 3. Open browser
# → http://localhost:8501
```

## 📊 Features

### 📋 Dashboard
- View top 50 trading candidates
- Interactive filtering (price, spread, ROI, win rate)
- Visual analytics with charts
- Download candidates as CSV

### 🔍 Item Analysis
- Historical price charts (6h granularity)
- Detailed metrics and performance stats
- Trade simulator with profit calculator
- Links to OSRS Wiki and GE Tracker

### ⚙️ Settings
- Configure capital and GE slots
- Select risk profile (conservative/moderate/aggressive)
- View and compare filter thresholds

### 🚀 Pipeline Control
- Run incremental updates (~13 min)
- Run full re-analysis (~90 min)
- View pipeline status and logs

## 🌐 Deployment Options

### Option 1: Streamlit Cloud (FREE, Easy)

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub repo
4. Deploy!

**Limitations:**
- Cannot run long pipelines (>10 min timeout)
- Limited RAM (~1GB)
- Solution: Run pipelines locally, deploy dashboard to visualize

### Option 2: Local with Port Forwarding

```bash
# Run with network access
streamlit run app.py --server.address 0.0.0.0

# Share with friends on same network
# → http://your-local-ip:8501
```

### Option 3: VPS (Full Control)

```bash
# On Ubuntu VPS:
apt update && apt install python3-pip
pip3 install -r requirements.txt

# Run with nohup
nohup streamlit run app.py --server.port 8501 &

# Setup nginx reverse proxy + SSL
# → https://yourdomain.com
```

## 🔐 Authentication

Simple password protection is included in `app.py`.

To set password:

1. Create `.streamlit/secrets.toml`:
```toml
password = "your-secure-password"
```

2. Or edit `app.py` and change default password

**For Streamlit Cloud:**
- Add secrets in dashboard settings
- Never commit secrets.toml to Git

## 📁 Project Structure

```
osrs_moneymaking/
├── app.py                    # Main Streamlit app
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_🔍_Item_Analysis.py
│   ├── 3_⚙️_Settings.py
│   └── 4_🚀_Run_Pipeline.py
├── src/
│   └── streamlit_utils/      # Helper functions
├── data/
│   ├── processed/            # Analysis outputs
│   └── raw/                  # Raw timeseries data
├── scripts/                  # Backend pipeline
└── config.yaml               # User configuration
```

## 🎯 Typical Workflow

```bash
# 1. Initial setup (once)
python scripts/run_bulk_download.py         # ~90 min
python scripts/run_pipeline.py --mode full --reanalyze  # ~90 min

# 2. Start dashboard
streamlit run app.py

# 3. Regular updates (every 3 days)
python scripts/run_pipeline.py --mode full  # ~13 min

# 4. Full re-analysis (weekly)
python scripts/run_pipeline.py --mode full --reanalyze  # ~90 min
```

## 🛠️ Troubleshooting

**"No candidates found"**
- Run the full pipeline first: `python scripts/run_pipeline.py --mode full --reanalyze`

**"ModuleNotFoundError"**
- Install dependencies: `pip install -r requirements.txt`

**Pipeline fails in dashboard**
- Long pipelines timeout in Streamlit
- Run them in terminal instead
- Dashboard is for visualization only

**Charts not showing**
- Check if parquet files exist in `data/processed/`
- Verify data isn't corrupted

## 💡 Tips

- **Start conservative:** Use 'moderate' risk profile
- **Run pipelines in terminal:** Faster and more reliable
- **Don't run long pipelines from UI:** They timeout
- **Check logs:** `data/logs/osrs_trading.log`

## 🚧 Future Enhancements

- [ ] Real-time price monitoring
- [ ] Best buy/sell time recommendations
- [ ] Portfolio optimization
- [ ] Email/Discord alerts
- [ ] Multi-user support
- [ ] Crafting arbitrage analysis

## 📝 License

For personal use. Data from OSRS Wiki API.

---

Made with ❤️ for OSRS traders
