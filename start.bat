@echo off
rem Start the OnlyNerds backend (http://127.0.0.1:8000) and frontend (http://localhost:3000) in two windows.
rem Needs uv, Node.js/npm and MongoDB running on localhost:27017.
setlocal
cd /d "%~dp0"

where uv >nul 2>nul || (echo uv not found. Install it: https://docs.astral.sh/uv/ & pause & exit /b 1)
where npm >nul 2>nul || (echo npm not found. Install Node.js: https://nodejs.org/ & pause & exit /b 1)

if not exist "backend\.env" (
    echo backend\.env is missing. Copy backend\.env.example to backend\.env and fill in your keys.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo Installing frontend packages...
    pushd frontend
    call npm install || (popd & pause & exit /b 1)
    popd
)

start "OnlyNerds backend" /d "%~dp0backend" cmd /k uv run uvicorn main:app --reload
start "OnlyNerds frontend" /d "%~dp0frontend" cmd /k npm run dev

echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:3000
timeout /t 6 /nobreak >nul
start "" http://localhost:3000
