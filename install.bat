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
set "SETUP_STAGE=Preparing folders"
if not exist "%UV_EXE%" (
  set "SETUP_STAGE=Downloading the uv runtime manager"
  echo [1/6] Downloading uv runtime manager...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile '%CD%\.runtime\uv.zip'; Expand-Archive -Force '%CD%\.runtime\uv.zip' '%CD%\.runtime\uv-unpack'; Copy-Item '%CD%\.runtime\uv-unpack\uv.exe' '%UV_EXE%' -Force"
  if errorlevel 1 goto failed
)
set "SETUP_STAGE=Installing managed Python 3.10 and 3.12"
echo [2/6] Installing managed Python 3.10 for the main app and Python 3.12 for RVC...
"%UV_EXE%" python install 3.10
if errorlevel 1 goto failed
"%UV_EXE%" python install 3.12
if errorlevel 1 goto failed
set "SETUP_STAGE=Creating the main app environment and installing dependencies"
echo [3/6] Creating the app environment...
if not exist ".venv\Scripts\python.exe" "%UV_EXE%" venv --python 3.10 .venv
if errorlevel 1 goto failed
"%UV_EXE%" pip install --python ".venv\Scripts\python.exe" -e .
if errorlevel 1 goto failed
if not exist "%RVC_DIR%\webui.py" (
  set "SETUP_STAGE=Downloading the pinned RVC backend"
  echo [4/6] Downloading pinned RVC inference backend...
  if exist "%RVC_DIR%" rmdir /s /q "%RVC_DIR%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/archive/%RVC_COMMIT%.zip' -OutFile '%CD%\.runtime\rvc.zip'; Expand-Archive -Force '%CD%\.runtime\rvc.zip' '%CD%\.runtime\rvc-unpack'; $src=Get-ChildItem '%CD%\.runtime\rvc-unpack' -Directory | Select-Object -First 1; Move-Item $src.FullName '%RVC_DIR%'"
  if errorlevel 1 goto failed
)
if not exist "%RVC_DIR%\webui.py" (
  echo ERROR: RVC training UI entry point webui.py was not found.
  echo The pinned backend may have changed or downloaded incorrectly.
  goto failed
)
if not exist "%RVC_DIR%\infer\cli.py" (
  echo ERROR: RVC inference CLI infer\cli.py was not found.
  echo The pinned backend cannot run singing-cover conversion.
  goto failed
)
set "SETUP_STAGE=Installing RVC Python 3.12 dependencies"
echo [5/6] Creating the separate RVC Python 3.12 environment...
if not exist "%RVC_DIR%\.venv\Scripts\python.exe" "%UV_EXE%" venv --python 3.12 "%RVC_DIR%\.venv"
if errorlevel 1 goto failed
if not exist "%RVC_DIR%\.runtime-ready-py312" (
  if not exist "%RVC_DIR%\requirments_cpu_py312.txt" (
    echo ERROR: RVC CPU requirements file was not found in the downloaded backend.
    goto failed
  )
  "%UV_EXE%" pip install --python "%RVC_DIR%\.venv\Scripts\python.exe" -r "%RVC_DIR%\requirments_cpu_py312.txt"
  if errorlevel 1 goto failed
  echo ready>"%RVC_DIR%\.runtime-ready-py312"
)
set "SETUP_STAGE=Checking app dependencies"
echo [6/6] Checking app imports...
".venv\Scripts\python.exe" -c "import gradio, demucs, soundfile; print('UI and separation dependencies are available.')"
if errorlevel 1 goto failed
echo.
echo Setup completed. Double-click run.bat to launch OneClick-AI-Cover.
pause
exit /b 0
:failed
echo.
echo SETUP FAILED during: %SETUP_STAGE%
echo Keep this window open and save the last error lines above.
echo Check internet access, free disk space, and security software download restrictions.
echo Troubleshooting guide: https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/docs/troubleshooting.md
echo Fix the reported issue, then run install.bat again.
pause
exit /b 1
