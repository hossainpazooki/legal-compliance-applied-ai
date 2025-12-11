"""
Streamlit Cloud Entry Point - Reg-RWA Navigator.

This is the main entry point for Streamlit Cloud deployment.
It imports and runs the KE Dashboard with all features.

Run locally:
    streamlit run streamlit_app.py
"""

import sys
from pathlib import Path

# Ensure backend is importable from repo root
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main dashboard
# We import after path setup to ensure backend modules resolve
from frontend.ke_dashboard import *  # noqa: F401, F403

# The ke_dashboard.py already contains all Streamlit code
# which runs on import. This file just ensures proper path setup
# for Streamlit Cloud deployment.
