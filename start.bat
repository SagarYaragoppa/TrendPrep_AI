@echo off
echo Starting AI Question Paper Organizer...
echo ---------------------------------------
echo NOTE: Make sure you have set your GEMINI_API_KEY in backend/.env
echo ---------------------------------------
start cmd /k "cd /d %~dp0 && venv\Scripts\python.exe backend\main.py"
echo Application starting... waiting 3 seconds before opening browser!
timeout /t 3 > NUL
start http://127.0.0.1:8000
