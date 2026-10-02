@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Criando ambiente Python pela primeira vez...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
streamlit run app.py
