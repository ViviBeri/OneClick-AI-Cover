@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ==========================================
echo   OneClick-AI-Cover - Automatic Setup
echo ==========================================
echo This setup downloads a managed Python runtime and AI dependencies.
echo You do NOT need to install Python manually.
echo A stable internet connection and several GB of free disk space are required.
echo.
if not exist ".runtime" mkdir ".runtime"
if not exist ".cache" mkdir ".cache"
if not exist "vendor" mkdir "vendor"
if not exist "models\voices" mkdir "models\voices"
if not exist "outputs" mkdir "outputs"
if not exist "logs" mkdir "logs"
set "UV_EXE=%CD%\.runtime\uv.exe"
set "UV_CACHE_DIR=%CD%\.cache\uv"
set "UV_PYTHON_INSTALL_DIR=%CD%\.runtime\python"
set "RVC_COMMIT=81eed5e8f68b6bed1789f682fe78cdd324495afc"
set "RVC_DIR=%CD%\vendor\rvc"
if not exist "%UV_EXE%" (
  echo [1/6] Downloading uv runtime manager...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile '%CD%\.runtime\uv.zip'; Expand-Archive -Force '%CD%\.runtime\uv.zip' '%CD%\.runtime\uv-unpack'; Copy-Item '%CD%\.runtime\uv-unpack\uv.exe' '%UV_EXE%' -Force"
  if errorlevel 1 goto failed
)
echo [2/6] Installing managed Python 3.10...
"%UV_EXE%" python install 3.10
if errorlevel 1 goto failed
echo [3/6] Creating the app environment...
if not exist ".venv\Scripts\python.exe" "%UV_EXE%" venv --python 3.10 .venv
if errorlevel 1 goto failed
"%UV_EXE%" pip install --python ".venv\Scripts\python.exe" -e .
if errorlevel 1 goto failed
if not exist "%RVC_DIR%\infer\cli.py" (
  echo [4/6] Downloading pinned RVC inference backend...
  if exist "%RVC_DIR%" rmdir /s /q "%RVC_DIR%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/archive/%RVC_COMMIT%.zip' -OutFile '%CD%\.runtime\rvc.zip'; Expand-Archive -Force '%CD%\.runtime\rvc.zip' '%CD%\.runtime\rvc-unpack'; $src=Get-ChildItem '%CD%\.runtime\rvc-unpack' -Directory | Select-Object -First 1; Move-Item $src.FullName '%RVC_DIR%'"
  if errorlevel 1 goto failed
)
echo [5/6] Creating the separate RVC environment...
if not exist "%RVC_DIR%\.venv\Scripts\python.exe" "%UV_EXE%" venv --python 3.10 "%RVC_DIR%\.venv"
if errorlevel 1 goto failed
if not exist "%RVC_DIR%\.runtime-ready" (
  if not exist "%RVC_DIR%\requirements.txt" (
    echo ERROR: RVC requirements.txt was not found in the downloaded backend.
    goto failed
  )
  "%UV_EXE%" pip install --python "%RVC_DIR%\.venv\Scripts\python.exe" -r "%RVC_DIR%\requirements.txt"
  if errorlevel 1 goto failed
  echo ready>"%RVC_DIR%\.runtime-ready"
)
echo [6/6] Checking app imports...
".venv\Scripts\python.exe" -c "import gradio, demucs, soundfile; print('UI and separation dependencies are available.')"
if errorlevel 1 goto failed
echo.
echo Setup completed. Double-click run.bat to launch OneClick-AI-Cover.
pause
exit /b 0
:failed
echo SETUP FAILED. Keep this window open and save the error text.
pause
exit /b 1
