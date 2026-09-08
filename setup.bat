@echo off
echo === code_word setup ===

REM Create Python virtual environment
python -m venv .venv
call .venv\Scripts\activate

REM Install Python dependencies
pip install -r requirements.txt

REM Install and build React frontend
cd frontend
npm install
npm run build
cd ..

echo.
echo === Setup complete ===
echo Run the app with:  python run.py
echo Dev mode frontend: cd frontend ^&^& npm run dev
