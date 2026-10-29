@echo off
setlocal

cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo Backend virtual environment is missing. Running install.bat first...
    call "%~dp0install.bat"
    if errorlevel 1 goto fail
)

"backend\.venv\Scripts\python.exe" -c "import uvicorn" >nul 2>nul
if errorlevel 1 (
    echo Backend dependencies are missing. Running install.bat first...
    call "%~dp0install.bat"
    if errorlevel 1 goto fail
)

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Skipping PostgreSQL and Neo4j auto-start.
) else (
    docker compose version >nul 2>nul
    if errorlevel 1 (
        echo Docker Compose was not found. Skipping PostgreSQL and Neo4j auto-start.
    ) else (
        echo Starting PostgreSQL and Neo4j with Docker Compose...
        docker compose up -d
        if errorlevel 1 goto fail
    )
)

echo.
echo Starting PassiveAgent...
echo API:      http://localhost:18080
echo Frontend: http://localhost:5173
echo.

pushd "backend"
call ".venv\Scripts\activate.bat"
python main.py
set APP_EXIT=%ERRORLEVEL%
popd

if not "%APP_EXIT%"=="0" goto fail
exit /b 0

:fail
echo.
echo PassiveAgent failed to start. Check the error message above.
pause
exit /b 1
