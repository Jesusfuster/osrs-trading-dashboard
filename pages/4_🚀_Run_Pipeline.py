"""
Run Pipeline - Execute Analysis from UI

Control panel to run data updates and analysis directly from the dashboard.
"""
import streamlit as st
import subprocess
import json
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Run Pipeline", page_icon="🚀", layout="wide")

# Header
st.title("🚀 Pipeline Control")
st.markdown("Execute data updates and analysis from the dashboard")

# Warning
st.warning("""
⚠️ **Important:** Pipeline execution can take a long time:
- **Incremental Update:** ~13 minutes
- **Full Re-analysis:** ~90 minutes

The page will be unresponsive while running. Check terminal/logs for progress.
""")

# Tabs
tab1, tab2, tab3 = st.tabs(["▶️ Run Pipeline", "📊 Status", "📝 Logs"])

with tab1:
    st.subheader("Pipeline Execution")
    
    # Pipeline options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔄 Incremental Update")
        st.info("""
        **Duration:** ~13 minutes
        
        **What it does:**
        1. Updates 6h data for Level 2 items (~465 items)
        2. Re-filters candidates (Level 2 → Level 3)
        3. Updates 1h data for final candidates
        
        **When to use:** Every 3 days (regular updates)
        """)
        
        if st.button("▶️ Run Incremental Update", type="primary", use_container_width=True):
            with st.spinner("Executing incremental pipeline... Check terminal for progress"):
                try:
                    result = subprocess.run(
                        [sys.executable, "scripts/run_pipeline.py", "--mode", "full"],
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=1800  # 30 min timeout
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ Incremental update completed!")
                        st.balloons()
                        
                        # Show last few lines of output
                        if result.stdout:
                            with st.expander("📄 Output (last 20 lines)"):
                                lines = result.stdout.split('\n')
                                st.code('\n'.join(lines[-20:]))
                    else:
                        st.error("❌ Pipeline failed!")
                        if result.stderr:
                            with st.expander("❌ Error details"):
                                st.code(result.stderr)
                
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Pipeline timed out (>30 min)")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with col2:
        st.markdown("### 🔍 Full Re-analysis")
        st.warning("""
        **Duration:** ~90 minutes
        
        **What it does:**
        1. Updates 6h data for ALL items (4,522)
        2. Complete analysis (Level 1 → 2 → 3)
        3. Downloads 1h data for new candidates
        
        **When to use:** Every 1-2 weeks, or when changing risk profile
        """)
        
        confirm_reanalyze = st.checkbox("I understand this takes ~90 minutes")
        
        if st.button(
            "▶️ Run Full Re-analysis",
            type="secondary",
            disabled=not confirm_reanalyze,
            use_container_width=True
        ):
            with st.spinner("Executing full re-analysis... This will take ~90 minutes. Check terminal!"):
                try:
                    result = subprocess.run(
                        [sys.executable, "scripts/run_pipeline.py", "--mode", "full", "--reanalyze"],
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=7200  # 2 hour timeout
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ Full re-analysis completed!")
                        st.balloons()
                        
                        if result.stdout:
                            with st.expander("📄 Output (last 20 lines)"):
                                lines = result.stdout.split('\n')
                                st.code('\n'.join(lines[-20:]))
                    else:
                        st.error("❌ Pipeline failed!")
                        if result.stderr:
                            with st.expander("❌ Error details"):
                                st.code(result.stderr)
                
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Pipeline timed out (>2 hours)")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Alternative: Run in background
    st.divider()
    st.markdown("### 💡 Recommended: Run in Terminal")
    
    st.info("""
    For long-running pipelines, it's better to run them in a terminal:
    
    **Incremental Update (13 min):**
    ```bash
    python scripts/run_pipeline.py --mode full
    ```
    
    **Full Re-analysis (90 min):**
    ```bash
    python scripts/run_pipeline.py --mode full --reanalyze
    ```
    
    Then refresh this dashboard to see updated results!
    """)

with tab2:
    st.subheader("📊 Pipeline Status")
    
    # Check metadata file
    metadata_file = project_root / "data" / "raw" / "timeseries_6h" / "_update_metadata.json"
    
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Parse dates
            start_time = metadata.get('start_time', 'N/A')
            end_time = metadata.get('end_time', 'N/A')
            
            st.success("✅ Last update completed successfully")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric(
                "Started",
                start_time.split('T')[0] if 'T' in str(start_time) else start_time
            )
            col2.metric(
                "Completed",
                end_time.split('T')[0] if 'T' in str(end_time) else end_time
            )
            col3.metric("Items Updated", f"{metadata.get('updated', 0):,}")
            col4.metric("New Records", f"{metadata.get('total_new_records', 0):,}")
            
            # Additional info
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Already Up-to-date", metadata.get('up_to_date', 0))
            col2.metric("No Data", metadata.get('no_data', 0))
            col3.metric("Failed", metadata.get('failed', 0))
            
            # Full metadata
            with st.expander("🔍 View Full Metadata"):
                st.json(metadata)
        
        except Exception as e:
            st.error(f"❌ Error reading metadata: {e}")
    else:
        st.info("ℹ️ No update metadata found. Run the pipeline to generate it.")
    
    # Check candidates file
    st.divider()
    st.subheader("📦 Candidates Status")
    
    processed_dir = project_root / "data" / "processed"
    
    candidates_found = False
    for risk_profile in ['moderate', 'conservative', 'aggressive']:
        file_path = processed_dir / f'final_candidates_{risk_profile}.parquet'
        if file_path.exists():
            candidates_found = True
            
            import pandas as pd
            df = pd.read_parquet(file_path)
            
            st.success(f"✅ Found candidates file: **{risk_profile}**")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Candidates", len(df))
            col2.metric("Avg Win Rate", f"{df['win_rate'].mean():.1f}%")
            col3.metric("Avg ROI", f"{df['avg_roi'].mean():.2f}%")
            
            # File info
            import os
            file_size = os.path.getsize(file_path)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            st.caption(f"Size: {file_size / 1024:.1f} KB | Last modified: {file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
            
            break
    
    if not candidates_found:
        st.warning("⚠️ No candidates file found. Run the full analysis first!")

with tab3:
    st.subheader("📝 Recent Logs")
    
    log_file = project_root / "data" / "logs" / "osrs_trading.log"
    
    if log_file.exists():
        # Show last N lines
        n_lines = st.slider("Number of lines to show", 10, 200, 50)
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            recent_lines = lines[-n_lines:]
            log_text = ''.join(recent_lines)
            
            st.text_area(
                "Log Output",
                value=log_text,
                height=400,
                disabled=True
            )
            
            # Download button
            st.download_button(
                "📥 Download Full Log",
                data=''.join(lines),
                file_name="osrs_trading.log",
                mime="text/plain"
            )
        
        except Exception as e:
            st.error(f"❌ Error reading log file: {e}")
    else:
        st.info("ℹ️ No log file found yet. Logs will appear after running the pipeline.")

# Footer
st.divider()
st.markdown("""
### 💡 Tips

**When to run Incremental Update:**
- Every 3 days to keep data fresh
- After market fluctuations
- To update prices of existing candidates

**When to run Full Re-analysis:**
- Every 1-2 weeks
- After changing risk profile in Settings
- When you want to discover new candidates
- After major game updates

**Troubleshooting:**
- If pipeline fails, check the Logs tab
- Make sure you have internet connection (API calls)
- Verify `config.yaml` is valid
""")
