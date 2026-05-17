#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../dashboard/streamlit_seller_demo"
python -m streamlit run app.py --server.port 8503
