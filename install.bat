@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo [1/3] Preparing Python virtual environment...
set "PYTHON_CMD=python"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 was not found or is not the default Python.
    echo Install Python 3.12 or make sure the Python launcher command "py -3.12" works.
    exit /b 1
)

if exist "backend\.venv\Scripts\python.exe" (
    for /f "delims=" %%V in ('backend\.venv\Scripts\python.exe -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))"') do set "VENV_PYTHON=%%V"
    if not "!VENV_PYTHON!"=="3.12" (
        echo Existing backend virtual environment uses Python !VENV_PYTHON!. Recreating it with Python 3.12...
        rmdir /s /q "backend\.venv"
    )
)

if not exist "backend\.venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv "backend\.venv"
    if errorlevel 1 exit /b 1
)

call "backend\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo [2/3] Installing backend dependencies...
python -m pip install -r "backend\requirements.txt"
if errorlevel 1 exit /b 1

echo [3/3] Installing frontend dependencies...
where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found. Install Node.js LTS and run this script again.
    exit /b 1
)

pushd "frontend"
npm install
set NPM_EXIT=%ERRORLEVEL%
popd
if not "%NPM_EXIT%"=="0" exit /b %NPM_EXIT%

echo.
echo Install complete. Run start.bat to start the project.
