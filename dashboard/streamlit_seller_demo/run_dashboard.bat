@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
streamlit run app.py --server.port 8503
pause
